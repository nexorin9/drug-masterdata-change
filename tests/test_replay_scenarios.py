"""T37：回放脚本可跑、报告字段齐全、判定规则生效。"""
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def test_replay_runs():
    import os
    env = dict(os.environ); env["PYTHONPATH"] = str(ROOT / "src")
    p = subprocess.run([sys.executable, str(ROOT / "scripts" / "replay_scenarios.py")],
                       cwd=ROOT, env=env, capture_output=True, text=True)
    assert p.returncode == 0, p.stderr
    assert "回放 12 条" in p.stdout


def test_report_fields():
    r = json.loads((ROOT / "samples" / "benchmarks" / "replay_report.json").read_text(encoding="utf-8"))
    assert r["total"] == 12
    assert len(r["detail"]) == 12
    assert all("hit" in d and "failure" in d for d in r["detail"])
    assert "failure_distribution" in r


def test_core_fields_all_hit():
    r = json.loads((ROOT / "samples" / "benchmarks" / "replay_report.json").read_text(encoding="utf-8"))
    assert all(d["hit"] for d in r["detail"]), [d["case"] for d in r["detail"] if not d["hit"]]


def test_near_sound_rejected():
    r = json.loads((ROOT / "samples" / "benchmarks" / "replay_report.json").read_text(encoding="utf-8"))
    near = [d for d in r["detail"] if "近音" in d["label"]]
    assert near and near[0]["hit"]
