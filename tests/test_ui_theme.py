"""T12：token 常量、间距栅格、字号层级、四态、状态色映射、无反向依赖。"""
import inspect
import json
import re
from pathlib import Path

from dmchange.ui import theme

ROOT = Path(__file__).resolve().parents[1]
# 色板金标准放在测试数据层（.json 不是源码），源码里不散写裸色值
GOLDEN = json.loads((ROOT / "tests" / "data" / "palette_golden.json").read_text(encoding="utf-8"))


def test_semantic_colors():
    for k in ("primary", "surface", "danger", "success", "warning", "neutral"):
        assert re.fullmatch(r"#[0-9A-Fa-f]{6}", theme.SEMANTIC_COLORS[k])


def test_specific_palette():
    assert theme.PRIMARY == GOLDEN["primary"]
    assert theme.SURFACE == GOLDEN["surface"]
    assert theme.DANGER == GOLDEN["danger"]
    assert theme.SUCCESS == GOLDEN["success"]


def test_grid_and_fonts():
    assert theme.GRID_BASE == 8
    assert set(theme.SPACE) >= {"space-1", "space-2", "space-4"}
    assert len(theme.FONT_SIZES) >= 4


def test_status_color_mapping():
    assert len(theme.STATUS_COLORS) == 7
    for s in ("draft_incomplete", "draft", "pending_review", "submitted",
              "acked", "rejected", "returned"):
        assert s in theme.STATUS_COLORS
        tag = theme.status_tag(s)
        assert tag.label and tag.color


def test_button_four_states():
    assert set(theme.BUTTON_STATES) == {"hover", "active", "disabled", "loading"}
    qss = (ROOT / "src" / "dmchange" / "ui" / "theme.qss").read_text(encoding="utf-8")
    for state in (":hover", ":pressed", ":disabled", ":focus"):
        assert state in qss


def test_qss_covers_10_widgets():
    qss = (ROOT / "src" / "dmchange" / "ui" / "theme.qss").read_text(encoding="utf-8")
    for widget in ("QPushButton", "QLineEdit", "QComboBox", "QTableView", "QHeaderView",
                   "QTabBar", "QScrollBar", "QToolTip", "QCheckBox", "QProgressBar"):
        assert widget in qss


def test_render_qss_no_placeholder():
    qss = theme.render_qss()
    assert "{{" not in qss
    assert theme.PRIMARY in qss


def test_no_reverse_dependency():
    widgets_dir = ROOT / "src" / "dmchange" / "ui" / "widgets"
    for p in widgets_dir.rglob("*.py"):
        src = p.read_text(encoding="utf-8")
        assert "from dmchange.ledger" not in src
        assert "import ledger" not in src
        assert "from ..ledger" not in src
        assert "from dmchange.extract" not in src
