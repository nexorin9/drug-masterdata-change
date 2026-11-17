# CLI 参考（运维与排障通道）

CLI 是给信息科做自检与无人值守跑批用的，日常操作走桌面窗口。

## dmchange selftest

端到端自检：样例 → 识别 → 抽取 → 守门 → 落库 → 打印可核对条目行。

```bash
python -m dmchange selftest --case samples/scenarios/case_001.json
```

| 参数 | 默认 | 说明 |
|---|---|---|
| `--case` | `samples/scenarios/case_001.json` | 场景 JSON 路径 |

退出码：0 成功；非 0 失败。

## dmchange doctor

环境与凭据自检清单：依赖包、环境变量、模型包状态。缺包给出获取指引。

```bash
python -m dmchange doctor
```

## dmchange sync-dictionary

从主数据平台同步药品目录快照。需要 `$MDM_BASE_URL` / `$MDM_TOKEN`。

```bash
python -m dmchange sync-dictionary
```

## dmchange export

导出药事会材料 CSV（含药品码、字段、依据原话、起止毫秒）。

```bash
python -m dmchange export --out out.csv
```

| 参数 | 默认 | 说明 |
|---|---|---|
| `--out` | `out.csv` | 输出路径 |

## 环境变量

见项目根 `.env.example`：MDM_BASE_URL / MDM_TOKEN / MODEL_BASE_URL / MODEL_API_KEY / MODEL_NAME / MODEL_TIMEOUT / ASR_MODE / ASR_BASE_URL / ASR_API_KEY。
