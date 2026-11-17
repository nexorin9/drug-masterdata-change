"""T15：六类归因齐全、阈值扫描可读、默认阈值理由、固化用例回归。"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
B = ROOT / "samples" / "benchmarks"
SIX = {"wrong_drug", "wrong_field", "direction_flip", "value_missing", "evidence_wrong", "extra_element"}


def test_attribution_categories():
    r = json.loads((B / "extraction_errors.json").read_text(encoding="utf-8"))
    assert set(r["by_category"].keys()) == SIX
    for c in SIX:
        assert r["by_category"][c]["count"] >= 1
        assert 0 <= r["by_category"][c]["ratio"] <= 1
        assert r["by_category"][c]["examples"]


def test_threshold_sweep():
    r = json.loads((B / "threshold_sweep.json").read_text(encoding="utf-8"))
    assert len(r["sweep"]) >= 3
    assert "chosen" in r and "rationale" in r


def test_architecture_threshold_section():
    arch = (ROOT / "docs" / "architecture.md")
    text = arch.read_text(encoding="utf-8") if arch.exists() else ""
    assert "阈值与取舍" in text or "阈值" in text  # T13 会写全，这里只断言存在


def test_completeness_baseline():
    r = json.loads((B / "extraction_completeness.json").read_text(encoding="utf-8"))
    assert r["sample_size"] >= 8
    assert len(r["detail"]) >= 8
    assert all(k in r["detail"][0] for k in ("drug_code", "field_name", "cur_value", "proposed_value", "evidence"))
