"""录音控件与实时转写区（T31 + 界面规范补建）：按住说话语义、按语音段逐行追加。"""
from __future__ import annotations

from typing import Optional

try:
    from PySide6.QtCore import Signal, QObject, QTimer
    from PySide6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QListWidget,
        QListWidgetItem, QProgressBar,
    )
    from PySide6.QtCore import Qt

    from .icons import svg
    from .theme import ON_PRIMARY
    from .widgets import IconButton

    class RecorderController(QObject):
        """按住说话的信号序列：press 一次、release 一次；可中途 cancel。"""

        pressed = Signal()
        released = Signal(int)  # duration_ms
        cancelled = Signal()
        chunkReady = Signal(bytes)

        def __init__(self, parent=None):
            super().__init__(parent)
            self._recording = False
            self._started = 0

        def press(self):
            if self._recording:
                return
            import time
            self._recording = True
            self._started = time.time()
            self.pressed.emit()

        def release(self):
            if not self._recording:
                return
            import time
            dur = int((time.time() - self._started) * 1000)
            self._recording = False
            self.released.emit(dur)

        def cancel(self):
            if self._recording:
                self._recording = False
                self.cancelled.emit()

    class TranscriptView(QListWidget):
        """实时转写区：按段逐行追加，行内显示说话人、毫秒区间、文本。"""

        def __init__(self, parent=None):
            super().__init__(parent)
            self.setAlternatingRowColors(True)
            # 长句换行显示，不出横向滚动条
            self.setWordWrap(True)
            self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        def append_line(self, text: str, start_ms: int, end_ms: int,
                        speaker: Optional[str] = None, punct_source: str = "model"):
            spk = speaker or "未分离"
            punc = "" if punct_source == "model" else "（标点推测）"
            line = f"[{start_ms}-{end_ms}ms] {spk}: {text}{punc}"
            item = QListWidgetItem(line)
            item.setToolTip(line)  # 长句在列表里会被省略，悬停看全文
            item.setData(Qt.UserRole, {"start": start_ms, "end": end_ms, "speaker": speaker})
            self.addItem(item)
            self.scrollToBottom()

        def highlight_at(self, start_ms: int, end_ms: int):
            for i in range(self.count()):
                item = self.item(i)
                d = item.data(Qt.UserRole) or {}
                if d.get("start") == start_ms and d.get("end") == end_ms:
                    self.setCurrentItem(item)
                    return

        def show_empty_state(self):
            self.clear()
            self.addItem("按住上方按钮说话，转写内容会按句出现在这里。")

    class RecorderWidget(QWidget):
        """录音控件 + 时长显示 + 状态指示。"""

        def __init__(self, parent=None):
            super().__init__(parent)
            self.controller = RecorderController(self)
            layout = QHBoxLayout(self)
            # 麦克风图标走内联 SVG（禁止 emoji 充当图标）
            self.btn = IconButton("按住 说话 (Ctrl+Shift+R)", svg("mic", ON_PRIMARY))
            self.lbl_duration = QLabel("就绪")
            self.lbl_duration.setProperty("role", "status")
            self.progress = QProgressBar()
            self.progress.setVisible(False)
            layout.addWidget(self.btn)
            layout.addWidget(self.lbl_duration)
            layout.addWidget(self.progress)
            self.btn.pressed.connect(self.controller.press)
            self.btn.released.connect(self.controller.release)
            self.controller.released.connect(self._on_released)

        def _on_released(self, dur):
            self.lbl_duration.setText(f"录音 {dur / 1000:.1f}s")

except ImportError:
    RecorderController = object  # type: ignore
    TranscriptView = object  # type: ignore
    RecorderWidget = object  # type: ignore
