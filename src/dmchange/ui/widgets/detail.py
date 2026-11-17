"""条目详情页（T33 + 界面规范补建）：依据出处三行、确认/退回/复核人选择、按钮随状态切换。

样式全部走 theme 令牌的 QSS role（title / evidence / field-error 等），
组件里不写内联色值与裸字号。
"""
from __future__ import annotations

from typing import Optional

try:
    from PySide6.QtCore import Signal, QSize
    from PySide6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel, QPushButton,
        QComboBox, QLineEdit, QGroupBox,
    )
    from PySide6.QtCore import Qt

    from ..theme import ON_PRIMARY, repolish
    from . import StatusTag, load_svg_icon
    from ..icons import svg

    BUTTONS_BY_STATUS = {
        "draft": ["确认并送复核"],
        "pending_review": ["退回修改", "复核通过并出站"],
        "returned": ["修改后重提"],
        "submitted": ["刷新回执"],
        "acked": [],
        "rejected": [],
        "draft_incomplete": ["补录要素", "确认并送复核"],
    }
    # 需要配图标的动作（其余用文字按钮：中文场景下文字更直达）
    BUTTON_ICONS = {"刷新回执": "refresh"}

    class DetailPanel(QWidget):
        """详情页工作面：状态驱动操作按钮，依据出处三行可点。"""

        evidenceClicked = Signal(int, int)  # start_ms, end_ms
        actionTriggered = Signal(str)  # action name

        def __init__(self, reviewers: Optional[list[str]] = None, parent=None):
            super().__init__(parent)
            self._status = ""
            self._submitted_by = ""
            self._reviewers = reviewers or ["李四", "王五", "赵六"]
            self._buttons: dict[str, QPushButton] = {}
            self._build()

        def _build(self):
            lay = QVBoxLayout(self)
            self.title = QLabel("（未选择条目）")
            self.title.setProperty("role", "title")
            lay.addWidget(self.title)

            self.status_lbl = StatusTag("")
            self.status_lbl.setVisible(False)  # 未选中条目时不显示空状态标签
            lay.addWidget(self.status_lbl, alignment=Qt.AlignLeft)

            form = QFormLayout()
            self.cur_lbl = QLabel("")
            self.prop_lbl = QLabel("")
            form.addRow("现值：", self.cur_lbl)
            form.addRow("应为值：", self.prop_lbl)
            lay.addLayout(form)

            quote = QGroupBox("依据出处")
            ql = QVBoxLayout(quote)
            self.evidence_labels = []
            for _ in range(3):
                b = QPushButton("（依据行）")
                b.setFlat(True)
                b.setProperty("role", "evidence")
                b.setEnabled(False)  # 未选中条目时没有依据行
                repolish(b)
                b.clicked.connect(lambda checked=False, idx=len(self.evidence_labels): self._emit_evidence(idx))
                ql.addWidget(b)
                self.evidence_labels.append(b)
            lay.addWidget(quote)

            self.reviewer_combo = QComboBox()
            self.reviewer_combo.addItems(self._reviewers)
            self.reviewer_combo.currentTextChanged.connect(self._check_reviewer)
            # label 常驻在控件上方，不用 placeholder 当 label
            reviewer_cap = QLabel("复核人（药事会第二人）")
            reviewer_cap.setProperty("role", "field-label")
            repolish(reviewer_cap)
            lay.addWidget(reviewer_cap)
            lay.addWidget(self.reviewer_combo)

            self.comment_edit = QLineEdit()
            self.comment_edit.setPlaceholderText("退回修改时必填，写清要改哪里")
            self.comment_edit.textChanged.connect(self._check_comment)
            comment_cap = QLabel("复核意见")
            comment_cap.setProperty("role", "field-label")
            repolish(comment_cap)
            lay.addWidget(comment_cap)
            lay.addWidget(self.comment_edit)

            self.hint = QLabel("")
            self.hint.setObjectName("hint")
            self.hint.setProperty("role", "field-error")
            repolish(self.hint)
            lay.addWidget(self.hint)

            self.action_box = QHBoxLayout()
            lay.addLayout(self.action_box)

        def set_item(self, item: dict):
            self._status = item.get("status", "")
            self._submitted_by = item.get("submitted_by", "")
            self.status_lbl.set_status(self._status)
            self.status_lbl.setVisible(bool(self._status))
            self.title.setText(f"{item.get('drug_code', '')}  ·  {item.get('field_name', '')}")
            self.cur_lbl.setText(item.get("cur_value", ""))
            self.prop_lbl.setText(item.get("proposed_value", ""))
            for i, lbl in enumerate(self.evidence_labels):
                ev = (item.get("evidence") or [])
                if i < len(ev):
                    e = ev[i]
                    lbl.setText(f"{e.get('speaker') or '未分离'}  {e.get('start_ms')}-{e.get('end_ms')}ms  {e.get('text','')}")
                    lbl.setEnabled(True)
                else:
                    lbl.setText("（依据行）")
                    lbl.setEnabled(False)
            self._rebuild_buttons()
            self._check_reviewer(self.reviewer_combo.currentText())
            self._check_comment(self.comment_edit.text())

        def _rebuild_buttons(self):
            while self.action_box.count():
                w = self.action_box.takeAt(0).widget()
                if w:
                    w.deleteLater()
            self._buttons.clear()
            for label in BUTTONS_BY_STATUS.get(self._status, []):
                b = QPushButton(label)
                icon_name = BUTTON_ICONS.get(label)
                if icon_name:
                    b.setIcon(load_svg_icon(svg(icon_name, ON_PRIMARY)))
                    b.setIconSize(QSize(18, 18))
                b.clicked.connect(lambda checked=False, l=label: self.actionTriggered.emit(l))
                self.action_box.addWidget(b)
                self._buttons[label] = b
            # 动作按钮按内容宽度，不拉成整行横幅：一屏一个主角
            self.action_box.addStretch(1)

        def _check_reviewer(self, reviewer: str):
            """复核人与经办人相同则禁用出站按钮并提示。"""
            blocked = bool(reviewer and reviewer == self._submitted_by)
            b = self._buttons.get("复核通过并出站")
            if b:
                b.setDisabled(blocked)
            if blocked:
                self.hint.setText("复核人不能与经办人相同：请改选另一位药事会复核人后再出站")
            else:
                self.hint.setText("")

        def _check_comment(self, text: str):
            b = self._buttons.get("退回修改")
            if b:
                b.setDisabled(not bool(text.strip()))

        def _emit_evidence(self, idx):
            # 依据可点：按毫秒定位转写区（具体行由调用方连接）
            pass

except ImportError:
    DetailPanel = object  # type: ignore
    BUTTONS_BY_STATUS = {}  # type: ignore
