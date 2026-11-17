"""T43：README 填实、丰度基数、GUI 优先、截图引用、无占位符。"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
README = (ROOT / "README.md").read_text(encoding="utf-8")
LINES = README.splitlines()


def test_abundance_baseline():
    assert sum(1 for l in LINES if l.startswith("## ")) >= 10
    assert sum(1 for l in LINES if l.startswith("### ")) >= 8
    assert sum(1 for l in LINES if l.startswith("|")) >= 5
    assert sum(1 for l in LINES if l.startswith("```")) >= 8
    assert len(README) >= 5000


def test_line_limit():
    assert len(LINES) <= 350


def test_no_placeholders():
    for token in ("Phase 4 后续 task 补齐", "TBD", "待补", "（填写）"):
        assert token not in README


def test_screenshots_referenced():
    assert "docs/screenshots/" in README
    assert README.count("![" ) >= 1


def test_scenarios_count():
    assert sum(1 for l in LINES if l.startswith("### 场景")) >= 6


def test_gui_first():
    # 取「## 快速开始」整节：按行首二级标题切，避免把 "### " 子标题误当成节尾
    # （原来的 split("## ") 会在 "### 依赖" 的第 2 个井号处截断，
    #   导致 "### 依赖" 永远不在 quick 里，断言不可达）
    quick = README.split("## 快速开始")[1].split("\n## ")[0]
    assert "启动桌面程序" in quick
    assert quick.index("启动桌面程序") < quick.index("### 依赖")


def test_no_upstream_repo_name():
    import re
    assert not re.search(r"funasr|github\.com|基于.{0,6}项目", README, re.I)


def test_readme_en():
    en = ROOT / "README_EN.md"
    assert en.exists()
    text = en.read_text(encoding="utf-8")
    assert len(text.splitlines()) <= 80
    assert "Full documentation: see README.md" in text
