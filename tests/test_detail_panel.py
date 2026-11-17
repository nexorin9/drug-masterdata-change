"""T33：按钮随状态切换、复核人同经办人被拦截、退回意见非空、离屏渲染。"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

ITEM = {
    "drug_code": "X1", "field_name": "spec_pack_code", "cur_value": "0.25",
    "proposed_value": "0.5", "status": "pending_review", "submitted_by": "张三",
    "evidence": [
        {"speaker": "spk0", "start_ms": 8000, "end_ms": 15000, "text": "不是0.25是0.5"},
    ],
}


def test_buttons_by_status(qapp):
    from dmchange.ui.widgets.detail import DetailPanel, BUTTONS_BY_STATUS
    assert "确认并送复核" in BUTTONS_BY_STATUS["draft"]
    assert "退回修改" in BUTTONS_BY_STATUS["pending_review"]
    assert BUTTONS_BY_STATUS["acked"] == []


def test_reviewer_blocked(qapp):
    from dmchange.ui.widgets.detail import DetailPanel
    p = DetailPanel(reviewers=["张三", "李四"])
    p.set_item(ITEM)
    p.reviewer_combo.setCurrentText("张三")  # 与经办人相同
    assert "复核通过并出站" in p._buttons
    assert p._buttons["复核通过并出站"].isEnabled() is False
    assert "不能与经办人相同" in p.hint.text()


def test_comment_required(qapp):
    from dmchange.ui.widgets.detail import DetailPanel
    p = DetailPanel()
    p.set_item(ITEM)
    p.comment_edit.setText("")
    assert p._buttons["退回修改"].isEnabled() is False
    p.comment_edit.setText("口径需复核")
    assert p._buttons["退回修改"].isEnabled() is True


def test_evidence_three_lines(qapp):
    from dmchange.ui.widgets.detail import DetailPanel
    p = DetailPanel()
    p.set_item(ITEM)
    assert len(p.evidence_labels) == 3
    assert "8000-15000" in p.evidence_labels[0].text()


def test_offscreen_render(qapp):
    from dmchange.ui.widgets.detail import DetailPanel
    from PySide6.QtGui import QPixmap
    p = DetailPanel()
    p.set_item(ITEM)
    p.resize(600, 400)
    out = ROOT / "docs" / "screenshots" / "detail.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    pix = QPixmap(p.size()); p.render(pix)
    assert pix.save(str(out))
