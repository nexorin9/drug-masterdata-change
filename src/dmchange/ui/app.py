"""托盘常驻、状态条、toast 反馈（T34）：关闭主窗口隐藏到托盘，退出只走托盘菜单。"""
from __future__ import annotations

try:
    from PySide6.QtWidgets import (
        QApplication, QSystemTrayIcon, QMenu, QMainWindow, QLabel, QStatusBar,
    )
    from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QAction
    from PySide6.QtCore import QTimer, Qt

    from .theme import ON_PRIMARY, PRIMARY, duration_ms, toast_qss

    TRAY_MENU_ITEMS = ("显示主窗口", "开始录音", "导出药事会材料", "退出")
    TOAST_DURATION_MS = 3000
    ERROR_TOAST_PERSISTENT = True

    def make_tray_icon() -> QIcon:
        """程序化生成药事岗圆形图标（不依赖 PNG 缩放，不用 emoji）。"""
        pix = QPixmap(64, 64)
        pix.fill(QColor(0, 0, 0, 0))
        p = QPainter(pix)
        p.setRenderHint(QPainter.Antialiasing)
        p.setBrush(QColor(PRIMARY))
        p.setPen(Qt.NoPen)
        p.drawEllipse(4, 4, 56, 56)
        p.setBrush(QColor(ON_PRIMARY))
        p.drawRect(28, 18, 8, 28)
        p.drawRect(18, 28, 28, 8)
        p.end()
        return QIcon(pix)

    class StatusBar(QStatusBar):
        """右下角状态条：就绪/录音中/识别中/抽取中/等待复核/已提交/出站失败重试中。"""

        STATES = ("就绪", "录音中", "识别中", "抽取中", "等待复核", "已提交", "出站失败重试中")
        # 需要人工介入的状态：颜色之外同时用文字承载含义（WCAG 1.4.1）
        ALERT_STATES = ("出站失败重试中",)

        def __init__(self, parent=None):
            super().__init__(parent)
            self._label = QLabel("就绪")
            self._label.setProperty("role", "status")
            self.addPermanentWidget(self._label)

        def set_state(self, state: str):
            if state in self.STATES:
                self._label.setText(state)
                self._label.setProperty("alert", state in self.ALERT_STATES)
                self._label.style().unpolish(self._label)
                self._label.style().polish(self._label)

    class ToastManager:
        """轻量提示：普通 3s 消失，错误常驻直到用户处理；同一时刻最多一个。"""

        def __init__(self, parent=None):
            self.parent = parent
            self._current = None
            self._timer = QTimer()

        def show(self, message: str, *, error: bool = False):
            label = QLabel(message)
            label.setStyleSheet(toast_qss(error=error))
            label.setWindowFlags(Qt.ToolTip | Qt.FramelessWindowHint)
            label.adjustSize()
            self._current = label
            label.show()
            self._fade_in(label)
            if not error:
                self._timer.timeout.connect(label.hide)
                self._timer.start(TOAST_DURATION_MS)

        @staticmethod
        def _fade_in(label):
            """淡入。动效降级开启时 duration_ms() 返回 0，直接显示不做动画。"""
            ms = duration_ms("dur-2")
            if ms <= 0:
                return
            from PySide6.QtWidgets import QGraphicsOpacityEffect
            from PySide6.QtCore import QPropertyAnimation
            effect = QGraphicsOpacityEffect(label)
            label.setGraphicsEffect(effect)
            effect.setOpacity(0.0)
            anim = QPropertyAnimation(effect, b"opacity", label)
            anim.setDuration(ms)
            anim.setStartValue(0.0)
            anim.setEndValue(1.0)
            anim.start()
            label._fade_anim = anim  # 保住引用，避免动画被回收后不生效

    class TrayApp(QApplication):
        """托盘应用：主窗口关闭隐藏到托盘。"""

        def __init__(self, argv):
            super().__init__(argv)
            self.tray = QSystemTrayIcon(make_tray_icon(), self)
            self.tray.setToolTip("药品主数据变更听写系统")
            menu = QMenu()
            self._actions = {}
            for name in TRAY_MENU_ITEMS:
                act = QAction(name, menu)
                menu.addAction(act)
                self._actions[name] = act
            self.tray.setContextMenu(menu)
            self.tray.show()
            self._quitting = False

        def quit_from_tray(self):
            self._quitting = True
            self.quit()

    class HiddenOnCloseWindow(QMainWindow):
        """关闭按钮 → 隐藏到托盘；只有 TrayApp.quit_from_tray 才真正退出。"""

        def __init__(self, app: TrayApp, parent=None):
            super().__init__(parent)
            self._app = app

        def closeEvent(self, event):
            if not self._app._quitting:
                event.ignore()
                self.hide()
                self._app.tray.showMessage("已最小化到托盘", "药品主数据变更听写系统")
            else:
                event.accept()

except ImportError:
    TrayApp = object  # type: ignore
    ToastManager = object  # type: ignore
    StatusBar = object  # type: ignore
    TRAY_MENU_ITEMS = ()  # type: ignore
