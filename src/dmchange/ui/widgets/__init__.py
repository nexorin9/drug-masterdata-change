"""基础组件：只含样式与无业务逻辑的绘制，禁止反向依赖 ledger/extract。

样式一律走 theme 令牌：组件里不出现裸色值、裸字号。
"""

try:
    from PySide6.QtWidgets import QPushButton, QLabel, QWidget
    from PySide6.QtCore import Qt, QSize
    from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor

    from ..theme import RADIUS, SPACE, status_tag, status_tag_qss

    class StatusTag(QLabel):
        """状态标签：圆角底色 + 语义色 + 文字（颜色不单独承载含义，含文字）。"""

        def __init__(self, status: str = "", parent=None):
            super().__init__(parent)
            self.setAlignment(Qt.AlignCenter)
            self.setContentsMargins(SPACE["space-2"], 2, SPACE["space-2"], 2)
            self._status = ""
            self.set_status(status)

        def set_status(self, status: str) -> None:
            tag = status_tag(status)
            self._status = status
            self.setText(tag.label)
            font = self.font()
            font.setPointSize(9)
            font.setBold(tag.bold)
            self.setFont(font)
            self.setStyleSheet(status_tag_qss(status))

    class IconButton(QPushButton):
        """带 SVG 图标的按钮；禁止 emoji 作图标。"""

        ICON_SIZE = QSize(18, 18)

        def __init__(self, text: str = "", svg_path: str = "", parent=None):
            super().__init__(text, parent)
            if svg_path:
                self.setIcon(load_svg_icon(svg_path))
                self.setIconSize(self.ICON_SIZE)

    def load_svg_icon(svg_or_path: str) -> QIcon:
        """加载 SVG 图标：既接受文件路径，也接受内联 SVG 文本。"""
        from PySide6.QtSvg import QSvgRenderer
        from PySide6.QtCore import QByteArray
        text = svg_or_path.strip()
        if text.startswith("<"):
            data = text.encode("utf-8")
        else:
            data = Path(svg_or_path).read_bytes()
        renderer = QSvgRenderer(QByteArray(data))
        pix = QPixmap(20, 20)
        pix.fill(QColor(0, 0, 0, 0))
        painter = QPainter(pix)
        renderer.render(painter)
        painter.end()
        return QIcon(pix)

    from pathlib import Path
except ImportError:
    # 无 PySide6 环境下提供占位类，便于非 GUI 测试 import 模块
    StatusTag = object  # type: ignore
    IconButton = object  # type: ignore

    def load_svg_icon(svg_or_path: str):  # type: ignore
        return None
