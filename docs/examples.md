# 输出样例

## 条目表片段（桌面窗口）

| 药品码 | 字段 | 现值 | 应为值 | 依据 | 状态 |
|---|---|---|---|---|---|
| XC0014N01400140014E0014 | 规格 | 0.5mg | 1mg | 8000–15000ms spk0 | 草稿 |
| XC0001N00100010001E0001 | 规格 | 0.25g | 0.5g | 8000–15000ms spk0 | 待复核 |

## 导出 CSV 片段

```
序号,药品码,字段名,现值,应为值,依据原话,说话人编号,起始毫秒,结束毫秒,经办人,复核人,状态,回执号
1,XC0014N01400140014E0014,spec_pack_code,0.5mg,1mg,恩替卡韦片的规格不是0.5毫克是1毫克,spk0,8000,15000,张三,李四,submitted,R-2026-001
```

CSV 为 UTF-8 with BOM，Excel 可直接打开。

## 终端 selftest 输出

```
=== selftest 可核对条目行 ===
药品码: XC0014N01400140014E0014
字段名: spec_pack_code
现值: 0.5mg  →  应为值: 1mg
状态: draft  守门: ok 守门通过
依据: [8000-15000ms] spk1: 恩替卡韦片的规格不是0.5毫克，是1毫克。
```

## 出站请求体（spec.md §2.3）

```json
{
  "change_id": "<sha256>",
  "drug_code": "XC0014N01400140014E0014",
  "field_name": "spec_pack_code",
  "cur_value": "0.5mg",
  "proposed_value": "1mg",
  "evidence": [{"speaker": "spk0", "start_ms": 8000, "end_ms": 15000, "text": "<原话>"}],
  "evidence_source": "voice",
  "submitted_by": "张三",
  "reviewed_by": "李四",
  "status": "submitted"
}
```
