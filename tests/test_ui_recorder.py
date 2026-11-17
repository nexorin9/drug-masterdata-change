"""T31：按下/释放信号序列、转写区追加模型、毫秒区间渲染、离屏渲染PNG。"""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_press_release_signals(qapp):
    from dmchange.ui.transcript import RecorderController
    c = RecorderController()
    events = []
    c.pressed.connect(lambda: events.append("press"))
    c.released.connect(lambda d: events.append("release"))
    c.press(); c.press()  # 重复 press 不重复触发
    c.release()
    assert events == ["press", "release"]


def test_transcript_append(qapp):
    from dmchange.ui.transcript import TranscriptView
    v = TranscriptView()
    assert v.count() == 0
    v.append_line("不是0.25是0.5", 8000, 15000, "spk0")
    assert v.count() == 1
    assert "8000-15000" in v.item(0).text()


def test_highlight_by_ms(qapp):
    from dmchange.ui.transcript import TranscriptView
    v = TranscriptView()
    v.append_line("句子", 1000, 2000, "spk0")
    v.highlight_at(1000, 2000)
    assert v.currentItem() is not None


def test_offscreen_render_png(qapp):
    from dmchange.ui.transcript import TranscriptView
    from PySide6.QtGui import QPixmap
    v = TranscriptView()
    v.resize(600, 300)
    for i in range(3):
        v.append_line(f"第{i}句转写内容", i * 1000, (i+1) * 1000, f"spk{i%2}")
    out = ROOT / "docs" / "screenshots" / "transcript.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    pix = QPixmap(v.size())
    v.render(pix)
    assert pix.save(str(out))
    assert out.exists() and out.stat().st_size > 1000
