"""T32：列定义、状态着色映射、筛选、排序、离屏渲染PNG。"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

ITEMS = [
    {"drug_code": "X1", "field_name": "spec_pack_code", "cur_value": "0.25",
     "proposed_value": "0.5", "status": "draft", "submitted_by": "张三",
     "updated_at": "2026-01-01T09:00:00"},
    {"drug_code": "X2", "field_name": "name_code", "cur_value": "A",
     "proposed_value": "B", "status": "acked", "submitted_by": "李四",
     "receipt_no": "R1", "updated_at": "2026-01-02T09:00:00"},
    {"drug_code": "X3", "field_name": "spec_pack_code", "cur_value": "1",
     "proposed_value": "2", "status": "rejected", "submitted_by": "王五",
     "updated_at": "2026-01-03T09:00:00"},
]


def test_columns(qapp):
    from dmchange.ui.tables import COLUMNS
    assert "药品码" in COLUMNS and "状态" in COLUMNS and "回执号" in COLUMNS
    assert len(COLUMNS) == 8


def test_status_colors_all(qapp):
    from dmchange.ui import theme
    for s in ("draft_incomplete", "draft", "pending_review", "submitted",
              "acked", "rejected", "returned"):
        assert s in theme.STATUS_COLORS


def test_model_rows(qapp):
    from dmchange.ui.tables import ItemTableModel
    m = ItemTableModel(ITEMS)
    assert m.rowCount() == 3 and m.columnCount() == 8
    m.set_status_filter("draft")
    assert m.rowCount() == 1


def test_table_filter(qapp):
    from dmchange.ui.tables import ItemTableView
    v = ItemTableView()
    v.set_items(ITEMS)
    v.filter_by_status("acked")
    assert v.proxy.rowCount() == 1


def test_offscreen_render(qapp):
    from dmchange.ui.tables import ItemTableView
    from PySide6.QtGui import QPixmap
    v = ItemTableView()
    v.set_items(ITEMS)
    v.resize(900, 300)
    out = ROOT / "docs" / "screenshots" / "items_table.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    pix = QPixmap(v.size()); v.render(pix)
    assert pix.save(str(out))
