"""T16：演练脚本存在、关键步骤可解析、正负向三类断言。"""
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_rehearsal_script_exists():
    assert (ROOT / "scripts" / "e2e_rehearsal.sh").exists()
    assert (ROOT / "scripts" / "_e2e_rehearsal.py").exists()


def test_rehearsal_runs():
    p = subprocess.run(["bash", str(ROOT / "scripts" / "e2e_rehearsal.sh")],
                       cwd=ROOT, capture_output=True, text=True)
    assert p.returncode == 0, p.stderr
    assert "正向" in p.stdout and "负向一" in p.stdout and "负向二" in p.stdout


def test_request_body_evidence():
    body = ROOT.parent / "logs" / "e2e_request_body.json"
    assert body.exists()
    d = json.loads(body.read_text(encoding="utf-8"))
    for f in ("change_id", "drug_code", "field_name", "cur_value", "proposed_value",
              "evidence", "evidence_source", "submitted_by", "reviewed_by", "status"):
        assert f in d, f
