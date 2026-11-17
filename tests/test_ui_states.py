"""T35：三态在三处存在、两档响应式、视觉差距文档、离屏渲染两档PNG。"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# 色板金标准放在测试数据层（.json 不是源码），源码里不散写裸色值
GOLDEN = json.loads((ROOT / "tests" / "data" / "palette_golden.json").read_text(encoding="utf-8"))


def test_three_states_containers(qapp):
    from dmchange.ui.main_window import StateContainer
    from PySide6.QtWidgets import QLabel, QWidget
    c = StateContainer(QLabel("内容"), "空态提示")
    c.show_loading(); assert c.currentIndex() == StateContainer.LOADING
    c.show_empty(); assert c.currentIndex() == StateContainer.EMPTY
    c.show_error("timeout", "超时", "重试"); assert c.currentIndex() == StateContainer.ERROR
    c.show_content(); assert c.currentIndex() == StateContainer.CONTENT


def test_main_window_has_three_state_areas(qapp):
    from dmchange.ui.main_window import MainWindow
    w = MainWindow()
    assert hasattr(w, "transcript_container") and hasattr(w, "table_container")
    assert hasattr(w, "detail")


def test_responsive_two_tiers(qapp):
    from dmchange.ui.main_window import MainWindow
    from PySide6.QtCore import Qt
    w = MainWindow()
    w.set_responsive(1280)
    assert w.splitter.orientation() == Qt.Horizontal
    w.set_responsive(768)
    assert w.splitter.orientation() == Qt.Vertical


def test_gap_doc_exists():
    p = ROOT / "docs" / "concepts" / "visual-target-gap.md"
    assert p.exists()
    text = p.read_text(encoding="utf-8")
    for color in (GOLDEN["primary"], GOLDEN["surface"], GOLDEN["danger"], GOLDEN["success"]):
        assert color in text


def test_offscreen_two_tiers(qapp):
    from dmchange.ui.main_window import MainWindow
    from dmchange.ui.theme import apply_theme
    apply_theme(qapp, dark=False)
    for width in (1280, 768):
        w = MainWindow()
        w.set_responsive(width)
        w.resize(width, 760)
        w.show()
        # 渲染产物用独立文件名：不与 scripts/capture_screenshots.py 产出的
        # 证据截图（灌了真实条目数据）抢同一个路径，否则每次跑测试都会把证据图覆盖成空窗口
        out = ROOT / "docs" / "screenshots" / f"main_window_responsive_{width}.png"
        out.parent.mkdir(parents=True, exist_ok=True)
        pix = w.grab()
        assert pix.save(str(out))
        w.hide()
