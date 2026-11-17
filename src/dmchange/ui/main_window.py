"""主窗口骨架与三态/两档响应式（T31/T35 + 界面规范补建）。

三态：加载 / 空 / 错误，在转写区、条目表、详情页三处各实现一遍。
两档响应式：1200 宽以上左右分栏（条目表为主角），1200 以下上下排布（表拿整幅宽度）。
样式走 theme 令牌（QLabel role / QProgressBar / QPushButton role），不写内联色值。
"""
from __future__ import annotations

try:
    from PySide6.QtWidgets import (
        QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QStackedWidget,
        QProgressBar, QPushButton, QSplitter,
    )
    from PySide6.QtCore import Qt

    from .tables import ItemTableView
    from .transcript import RecorderWidget, TranscriptView
    from .widgets.detail import DetailPanel
    from .app import StatusBar
    from .theme import repolish

    # 断点：低于此宽度上下排布。
    # 决策依据：条目表 8 列、药品码 23 位，横向排布在 1200 以下必然出横向滚动条、
    # 把「回执时间/经办人」挤出视野；转写区只有一两行，上下排布能让表拿到整幅宽度。
    NARROW_BREAKPOINT = 1200

    class StateContainer(QStackedWidget):
        """三态容器：index 0=内容 1=加载 2=空 3=错误。

        空态与错态都给文案 + 下一步动作，不给一张空白页。
        """

        CONTENT, LOADING, EMPTY, ERROR = 0, 1, 2, 3

        def __init__(self, content: QWidget, empty_text: str,
                     empty_action: str = "", parent=None):
            super().__init__(parent)
            self.addWidget(content)

            loading = QWidget()
            loading.setProperty("role", "card")
            ll = QVBoxLayout(loading)
            ll.setContentsMargins(24, 24, 24, 24)
            ll.setSpacing(8)
            l_title = QLabel("正在加载…")
            l_title.setProperty("role", "empty-title")
            repolish(l_title)
            ll.addWidget(l_title)
            bar = QProgressBar()
            bar.setRange(0, 0)  # 不确定进度：跑批时不让界面看着像死了
            ll.addWidget(bar)
            l_hint = QLabel("正在读取本地台账与目录快照")
            l_hint.setProperty("role", "empty-hint")
            repolish(l_hint)
            ll.addWidget(l_hint)
            ll.addStretch(1)
            self.addWidget(loading)

            empty = QWidget()
            empty.setProperty("role", "card")
            el = QVBoxLayout(empty)
            el.setContentsMargins(24, 24, 24, 24)
            el.setSpacing(8)
            e_title = QLabel("暂无内容")
            e_title.setProperty("role", "empty-title")
            repolish(e_title)
            el.addWidget(e_title)
            e_hint = QLabel(empty_text)
            e_hint.setProperty("role", "empty-hint")
            repolish(e_hint)
            el.addWidget(e_hint)
            if empty_action:
                e_btn = QPushButton(empty_action)
                e_btn.setProperty("role", "secondary")
                repolish(e_btn)
                # 动作按钮按内容宽度，不拉成整行横幅
                e_row = QHBoxLayout()
                e_row.setContentsMargins(0, 0, 0, 0)
                e_row.addWidget(e_btn)
                e_row.addStretch(1)
                el.addLayout(e_row)
                self.empty_action_button = e_btn
            el.addStretch(1)
            self.addWidget(empty)

            err = QWidget()
            err.setProperty("role", "card")
            erl = QVBoxLayout(err)
            erl.setContentsMargins(24, 24, 24, 24)
            erl.setSpacing(8)
            self.err_code = QLabel("出错了")
            self.err_code.setProperty("role", "error-code")
            repolish(self.err_code)
            erl.addWidget(self.err_code)
            self.err_label = QLabel("出错了")
            self.err_label.setProperty("role", "error-msg")
            repolish(self.err_label)
            erl.addWidget(self.err_label)
            self.err_hint = QLabel("")
            self.err_hint.setProperty("role", "empty-hint")
            repolish(self.err_hint)
            erl.addWidget(self.err_hint)
            retry = QPushButton("重试")
            r_row = QHBoxLayout()
            r_row.setContentsMargins(0, 0, 0, 0)
            r_row.addWidget(retry)
            r_row.addStretch(1)
            erl.addLayout(r_row)
            erl.addStretch(1)
            self.addWidget(err)
            self.retry_button = retry

        def show_content(self): self.setCurrentIndex(self.CONTENT)
        def show_loading(self): self.setCurrentIndex(self.LOADING)
        def show_empty(self): self.setCurrentIndex(self.EMPTY)
        def show_error(self, code: str, msg: str, suggestion: str = ""):
            self.err_code.setText(code)
            self.err_label.setText(msg)
            self.err_hint.setText(suggestion)
            self.setCurrentIndex(self.ERROR)

    class MainWindow(QMainWindow):
        """左：录音+转写；右：条目表+详情。768 宽时上下排布。"""

        def __init__(self, reviewers: list[str] | None = None, parent=None):
            super().__init__(parent)
            self.setWindowTitle("药品主数据变更听写系统")
            self.resize(1280, 800)
            self.recorder = RecorderWidget()
            self.transcript = TranscriptView()
            self.items_table = ItemTableView()
            self.detail = DetailPanel(reviewers)
            self.status_bar = StatusBar()

            transcript_container = StateContainer(
                self.transcript, "按住上方按钮说话，转写内容会按句出现在这里。",
                empty_action="开始录音")
            table_container = StateContainer(
                self.items_table, "还没有条目，先同步药品目录。", empty_action="同步药品目录")
            self.transcript_container = transcript_container
            self.table_container = table_container

            left = QWidget(); lv = QVBoxLayout(left)
            lv.setContentsMargins(12, 12, 12, 12)
            lv.setSpacing(8)
            l_cap = QLabel("录音与转写")
            l_cap.setProperty("role", "section-title")
            repolish(l_cap)
            lv.addWidget(l_cap)
            # 录音按钮按内容宽度：条目表才是这一屏的主角
            btn_row = QHBoxLayout()
            btn_row.setContentsMargins(0, 0, 0, 0)
            btn_row.addWidget(self.recorder.btn)
            btn_row.addStretch(1)
            lv.addLayout(btn_row)
            lv.addWidget(transcript_container, stretch=1)

            right = QWidget(); rv = QVBoxLayout(right)
            rv.setContentsMargins(12, 12, 12, 12)
            rv.setSpacing(8)
            r_cap = QLabel("条目工作台")
            r_cap.setProperty("role", "section-title")
            repolish(r_cap)
            rv.addWidget(r_cap)
            rv.addWidget(table_container, stretch=3)
            rv.addWidget(self.detail, stretch=2)

            self.splitter = QSplitter(Qt.Horizontal)
            self.splitter.addWidget(left)
            self.splitter.addWidget(right)
            self.splitter.setStretchFactor(0, 1)
            self.splitter.setStretchFactor(1, 2)
            self.splitter.setSizes([420, 860])
            self.setCentralWidget(self.splitter)
            self.setStatusBar(self.status_bar)
            self.items_table.rowSelected.connect(self.detail.set_item)

        def resizeEvent(self, event):
            super().resizeEvent(event)
            self.set_responsive(self.width())

        def set_responsive(self, width: int):
            """1200 宽以上左右分栏（条目表为主角）；更窄时上下排布。"""
            want = Qt.Vertical if width < NARROW_BREAKPOINT else Qt.Horizontal
            if self.splitter.orientation() != want:
                self.splitter.setOrientation(want)
                if want == Qt.Horizontal:
                    self.splitter.setSizes([max(320, width // 3), width - max(320, width // 3)])
                else:
                    self.splitter.setSizes([width // 3, width - width // 3])

        def show_three_states(self):
            """供测试/演示触发三态渲染。"""
            self.transcript_container.show_empty()
            self.table_container.show_loading()
            self.detail.setEnabled(True)
            self.table_container.show_error("timeout", "模型调用超时", "请检查 MODEL_TIMEOUT 或重试")

except ImportError:
    MainWindow = object  # type: ignore
    StateContainer = object  # type: ignore
