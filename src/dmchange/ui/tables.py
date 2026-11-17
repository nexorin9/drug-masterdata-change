"""条目工作台表（T32 + 界面规范补建）：QTableView + QAbstractTableModel。

一屏一个主角：条目表是本屏的主角，转写区与详情页都是它的陪衬。
样式与色值一律来自 theme 令牌，组件内不出现裸色值。
"""
from __future__ import annotations

from typing import Any, Optional

try:
    from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt, Signal, QSortFilterProxyModel
    from PySide6.QtGui import QColor, QBrush, QFont
    from PySide6.QtWidgets import QTableView, QHeaderView

    from .theme import (
        HOVER_BG, NEUTRAL, STATUS_COLORS, code_font, numeric_font, status_tag,
    )

    COLUMNS = ("药品码", "字段名", "现值", "应为值", "状态", "回执号", "回执时间", "经办人")
    # 含数字的列：施加等宽数字（tabular-nums / OpenType tnum），保证纵向数字不跳字。
    # 本表没有金额/比率列，药品码与回执号是标识符而非度量值，保持左对齐更易扫读。
    TABULAR_COLUMNS = ("药品码", "回执号", "回执时间")
    CODE_COLUMNS = ("药品码",)
    # 药品码是主标识，固定够宽不截断（uis/UI_BASELINE.md §5：长文本截断加 title）
    DRUG_CODE_WIDTH = 208

    class ItemTableModel(QAbstractTableModel):
        """条目表 model：数据驱动，不用 QTableWidget 逐格塞。"""

        def __init__(self, items: Optional[list[dict[str, Any]]] = None, parent=None):
            super().__init__(parent)
            self._items: list[dict[str, Any]] = list(items or [])
            self._status_filter: str = ""
            self._hovered_row: int = -1

        def rowCount(self, parent=QModelIndex()):
            return len(self._visible())

        def columnCount(self, parent=QModelIndex()):
            return len(COLUMNS)

        def data(self, index, role=Qt.DisplayRole):
            if not index.isValid():
                return None
            row = self._visible()
            if index.row() >= len(row):
                return None
            item = row[index.row()]
            col = COLUMNS[index.column()]
            key = {
                "药品码": "drug_code", "字段名": "field_name", "现值": "cur_value",
                "应为值": "proposed_value", "状态": "status", "回执号": "receipt_no",
                "回执时间": "receipt_at", "经办人": "submitted_by",
            }[col]
            val = item.get(key, "")
            if col == "状态" and isinstance(val, str):
                tag = status_tag(val)
                val = tag.label
            if role == Qt.DisplayRole:
                return str(val) if val else ("待回执" if col == "回执号" else "")
            if role == Qt.ForegroundRole and col == "状态":
                return QColor(STATUS_COLORS.get(item.get("status", ""), NEUTRAL))
            if role == Qt.BackgroundRole and index.row() == self._hovered_row:
                return QBrush(QColor(HOVER_BG))
            if role == Qt.FontRole:
                if col in CODE_COLUMNS:
                    # 23 位药品码用 12px 等宽体（基线下限），保证整码不截断
                    return code_font(point_size=9)
                if col in TABULAR_COLUMNS:
                    return numeric_font()
                if col in ("现值", "应为值") and any(c.isdigit() for c in str(val)):
                    # 含剂量的现值/应为值同样开等宽数字，避免小数点跳动
                    return numeric_font()
            if role == Qt.TextAlignmentRole and col == "药品码":
                return int(Qt.AlignVCenter | Qt.AlignLeft)
            if role == Qt.ToolTipRole:
                return str(item.get("reject_reason", "")) or str(val)
            return None

        def headerData(self, section, orientation, role=Qt.DisplayRole):
            if role == Qt.DisplayRole and orientation == Qt.Horizontal:
                return COLUMNS[section]
            return None

        def _visible(self):
            if not self._status_filter:
                return self._items
            return [i for i in self._items if i.get("status") == self._status_filter]

        def set_items(self, items: list[dict[str, Any]]):
            self.beginResetModel()
            self._items = list(items)
            self._hovered_row = -1
            self.endResetModel()

        def set_status_filter(self, status: str):
            self.beginResetModel()
            self._status_filter = status
            self._hovered_row = -1
            self.endResetModel()

        def set_hovered_row(self, row: int) -> None:
            """行悬停高亮：与选中态可区分（uis/UI_BASELINE.md §5 表格）。"""
            if row == self._hovered_row:
                return
            old, self._hovered_row = self._hovered_row, row
            visible = self._visible()
            for r in (old, self._hovered_row):
                if 0 <= r < len(visible):
                    self.dataChanged.emit(self.index(r, 0), self.index(r, len(COLUMNS) - 1))

        def all_items(self):
            return list(self._items)

    class ItemTableView(QTableView):
        """条目表视图：粘性表头（QHeaderView）、行悬停、选中态。"""

        rowSelected = Signal(dict)

        def __init__(self, parent=None):
            super().__init__(parent)
            self.model_obj = ItemTableModel()
            self.proxy = QSortFilterProxyModel()
            self.proxy.setSourceModel(self.model_obj)
            self.setModel(self.proxy)
            self.setSelectionBehavior(QTableView.SelectRows)
            self.setSelectionMode(QTableView.SingleSelection)
            self.setSortingEnabled(True)
            self.setMouseTracking(True)
            self.setWordWrap(False)
            self.verticalHeader().setVisible(False)
            self.verticalHeader().setDefaultSectionSize(36)
            header = self.horizontalHeader()
            header.setHighlightSections(False)
            header.setStretchLastSection(True)
            # 列宽策略：药品码固定够宽，其余按内容自适应，最后一列吸收余量
            for i, col in enumerate(COLUMNS):
                if col in CODE_COLUMNS:
                    header.setSectionResizeMode(i, QHeaderView.Interactive)
                    self.setColumnWidth(i, DRUG_CODE_WIDTH)
                else:
                    header.setSectionResizeMode(i, QHeaderView.ResizeToContents)
            self.clicked.connect(self._on_click)
            self.entered.connect(self._on_entered)

        def set_items(self, items):
            self.model_obj.set_items(items)

        def filter_by_status(self, status):
            self.model_obj.set_status_filter(status)

        def _on_click(self, index):
            src = self.proxy.mapToSource(index)
            items = self.model_obj._visible()
            if 0 <= src.row() < len(items):
                self.rowSelected.emit(items[src.row()])

        def _on_entered(self, index):
            self.model_obj.set_hovered_row(index.row())

        def leaveEvent(self, event):
            self.model_obj.set_hovered_row(-1)
            super().leaveEvent(event)

except ImportError:
    ItemTableModel = object  # type: ignore
    ItemTableView = object  # type: ignore
    COLUMNS = ()  # type: ignore
