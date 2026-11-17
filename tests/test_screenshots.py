"""T42：≥3 张真实运行截图存在、README 逐张引用、无概念图冒充。"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHOTS = ROOT / "docs" / "screenshots"
README = (ROOT / "README.md").read_text(encoding="utf-8")


def test_at_least_three_shots():
    pngs = list(SHOTS.glob("*.png"))
    assert len(pngs) >= 3
    assert all(p.stat().st_size > 1000 for p in pngs)


def test_three_kinds():
    names = {p.name for p in SHOTS.glob("*.png")}
    assert any("terminal" in n for n in names)
    assert any("main_window" in n or "detail" in n or "table" in n for n in names)
    assert any("export" in n for n in names)


def test_referenced_in_readme():
    for name in ("terminal_selftest.png", "main_window_filled.png", "export_report.png"):
        assert name in README


def test_no_concept_copy():
    concept = ROOT / "docs" / "concepts"
    assert not list(concept.glob("*.png")) and not list(concept.glob("*.jpg"))
