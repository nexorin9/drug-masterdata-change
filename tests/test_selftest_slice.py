"""T3：最小端到端切片 + 样例数据规模。"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _run_selftest(case="samples/scenarios/case_001.json"):
    env = None
    import os
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT / "src")
    return subprocess.run(
        [sys.executable, "-m", "dmchange", "selftest", "--case", case],
        cwd=ROOT, env=env, capture_output=True, text=True,
    )


def test_selftest_prints_item_line():
    p = _run_selftest()
    assert p.returncode == 0, p.stderr
    out = p.stdout
    assert "药品码:" in out
    assert "字段名:" in out
    assert "ms]" in out  # 绝对毫秒区间
    assert "依据:" in out
    # 药品码为真实 23 位（非待人工指定）
    assert "待人工指定" not in out


def test_scenarios_count():
    cases = list((ROOT / "samples" / "scenarios").glob("case_*.json"))
    assert len(cases) >= 8


def test_dictionary_snapshot_count():
    snap = json.loads((ROOT / "samples" / "dictionary_snapshot.json").read_text(encoding="utf-8"))
    assert len(snap["items"]) >= 20


def test_scenario_schema():
    for p in (ROOT / "samples" / "scenarios").glob("case_*.json"):
        c = json.loads(p.read_text(encoding="utf-8"))
        assert "expect" in c and "speaker_segments" in c
        for s in c["speaker_segments"]:
            assert s["start"] <= s["end"]
