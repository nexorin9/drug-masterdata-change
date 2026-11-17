# 架构与数据流（内部实现说明）

> 本文是给信息科与后续维护者的实现说明。产品使用说明见 `README.md`。

## 全链路数据流

```
麦克风/导入音频 → 音频统一化(16k单声道PCM) → VAD分段 → 段驱动增量解码
  → Utterance[]句级归一 → ModelGateway要素抽取 → 目录表守门与歧义拒绝
  → 台账与状态机 → MDM出站 → 回执回读 → 药事会材料/审计链导出
```

## 状态机

```
draft_incomplete → draft → pending_review → submitted → acked | rejected
                                │
                                └→ returned → draft
```

- 两个确认点：药事岗确认（`draft → pending_review`）、药事会第二人复核（`pending_review → submitted`，强校验复核人≠经办人）。
- 模型输出不推进任何状态。
- 非法迁移抛 `IllegalTransition` 并记 `illegal_transition` 审计。

## 幂等键

`change_id = sha256(drug_code | field_name | cur_value | proposed_value | evidence_sha256)`，不含时间戳与重试次数。证据按 speaker/start/end/text 排序后拼接再哈希，证据顺序不影响结果。`items.change_id` 唯一约束兜底。

## 审计链

只增不改：`audit_log(actor, action, drug_code, field_name, cur_value, proposed_value, evidence_json, detail_json, at)`。无 update/delete 代码路径。动作集合：item_created / manual_fill / confirmed / reviewed / submitted / acked / rejected / returned / duplicated_submit / illegal_transition / asset_rule_updated。

## 出站时序

复核通过 → 同一事务写 items(submitted) + outbox(pending) → 出站 POST（Idempotency-Key=change_id）→ 失败退避重试（2^n，封顶 300s，6 次转 dead）→ 收到回执才推进 acked/rejected。失败期间状态恒为 submitted，绝不误标 acked。

## 阈值与取舍

默认「证据强度 weak 时不自动确认」「低于阈值要求人工指定药品码」。

阈值扫描（`samples/benchmarks/threshold_sweep.json`）表明：降阈值会提高误放行，升阈值会增加人工负担。默认阈值定为 3，理由：**主数据不接受脏数据，误放行的代价高于误拦**——宁可多一次人工核对，不可让错误值写回主数据平台。这条取舍与目录表硬匹配、歧义拒绝共同构成"模型不可信 assumptive"防线。

## 失败降级

- 模型不可达/超时/Schema 失败 → `draft_incomplete`，只留转写+出处+空要素，不出站。
- 目录同步失败 → 用上次快照 + 顶部「目录已过期」提示。
- 出站失败 → outbox 排队，状态停 submitted。
- 说话人聚类不足 → 标「未分离」，不产出两个角色。

## 凭据与脱敏

九个环境变量，零硬编码。日志与导出对 Bearer token / api key 掩码，音频本地路径不进导出物。
