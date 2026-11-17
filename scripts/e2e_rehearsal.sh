#!/usr/bin/env bash
# 出站真实路径端到端联调演练：建条目 → 确认 → 换人复核 → 出站 → 回执 → 导出
# 演练用协议替身（仅测试层），字段规范严格对齐 spec.md §2.3；真实院内端点未实连。
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOGDIR="$(cd "$ROOT/.." && pwd)/logs"
mkdir -p "$LOGDIR"
export PYTHONPATH="$ROOT/src"
export MDM_BASE_URL="${MDM_BASE_URL:-https://mdm.rehearsal.internal}"
export MDM_TOKEN="${MDM_TOKEN:-rehearsal-token}"
export MODEL_BASE_URL="${MODEL_BASE_URL:-https://llm.rehearsal.internal}"
export MODEL_API_KEY="${MODEL_API_KEY:-rehearsal-key}"
export MODEL_NAME="${MODEL_NAME:-rehearsal-model}"

echo "=== E2E 联调演练开始 ==="
python3 "$ROOT/scripts/_e2e_rehearsal.py" --logdir "$LOGDIR"
echo "=== E2E 联调演练完成 ==="
