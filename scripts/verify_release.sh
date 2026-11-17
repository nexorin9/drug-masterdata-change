#!/usr/bin/env bash
# T44：一条命令跑通 安装检查 → selftest 端到端 → 目录守门 → 导出 CSV → 断言产物
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export PYTHONPATH="$ROOT/src"
export QT_QPA_PLATFORM=offscreen
cd "$ROOT"
echo "[1/5] Python 与依赖"
python3 --version
python3 -c "import pytest,pydantic,httpx; print('  核心依赖 OK')"

echo "[2/5] 端到端自检（含目录守门）"
python3 -m dmchange selftest --case samples/scenarios/case_001.json

echo "[3/5] 目录守门回归（歧义拒绝）"
python3 -c "
from dmchange.domain.models import ChangeItem
from dmchange.dictionary.store import DrugEntry
from dmchange.extract.guard import guard_item
import json
snap=json.load(open('samples/dictionary_snapshot.json'))['items']
entries=[DrugEntry(i['drug_code'],i['generic_name'],i['dosage_form'],i['spec'],i['manufacturer']) for i in snap]
it=ChangeItem(field_name='spec_pack_code')
gr=guard_item(it,entries=entries,generic_ref='阿莫西林胶囊')
assert not gr.passed and len(it.candidate_codes)>=2
print('  歧义拒绝 OK，候选',len(it.candidate_codes),'条')
"

echo "[4/5] 导出 CSV"
python3 -m dmchange export --out .verify_out.csv
test -s .verify_out.csv && echo "  导出产物 OK"

echo "[5/5] 断言关键产物存在"
for f in README.md requirements.txt pyproject.toml .env.example qrcode.jpg docs/screenshots/main_window_filled.png samples/dictionary_snapshot.json; do
  test -e "$f" || { echo "  缺失 $f"; exit 1; }
  echo "  OK $f"
done
rm -f .verify_out.csv
echo "=== 发布校验全部通过 ==="
