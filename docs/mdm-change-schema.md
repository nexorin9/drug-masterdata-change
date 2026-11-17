# 主数据变更单字段规范（spec.md §2.3 对齐）

`POST {mdm_base_url}/api/v1/master-data/changes`，Header：`Authorization: Bearer $MDM_TOKEN`、`Idempotency-Key: {change_id}`。

| 字段 | 类型 | 必填 | 取值域 / 说明 | 代码位置 |
|---|---|---|---|---|
| change_id | string(64) | 是 | sha256 幂等键，与 Idempotency-Key 同值 | `domain`→`ledger/identity.py:compute_change_id` |
| drug_code | string(23) | 是 | 西药 23 位 6 部分，目录表硬匹配 | `domain/codes.py:validate_drug_code` |
| field_name | enum | 是 | name_code / category_code / dosage_form_code / spec_pack_code / enterprise_code | `domain/models.py:FieldName` |
| cur_value | string | 是 | 目录现值原文 | `domain/models.py:ChangeItem.cur_value` |
| proposed_value | string | 是 | 应为值原文 | `domain/models.py:ChangeItem.proposed_value` |
| evidence | array | 是(≥1) | 每条含 speaker / start_ms / end_ms / text | `extract/evidence.py` |
| evidence_source | string | 是 | 固定 `voice` | `domain/models.py:ChangeItem` |
| submitted_by | string | 是 | 经办人，非空 | `ledger/repository.py:create` |
| reviewed_by | string | 是 | 复核人，≠ submitted_by | `ledger/state_machine.py:assert_reviewer_not_submitter` |
| status | enum | 是 | 出站时固定 `submitted` | `ledger/repository.py:submit` |

evidence 子字段：

| 字段 | 类型 | 说明 | 代码位置 |
|---|---|---|---|
| speaker | string/null | 录音内匿名编号，辅助列 | `domain/models.py:Evidence` |
| start_ms | int | 绝对毫秒起点 | 同上 |
| end_ms | int | 绝对毫秒终点 | 同上 |
| text | string | 原话原文（非空） | 同上 |

口径不静默换算：请求体只传原文，`*_normalized` 归一值只留本地台账，不进出站 body。
