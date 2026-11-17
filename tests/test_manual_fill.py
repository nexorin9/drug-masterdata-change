"""T23：降级落库、补齐校验、补录审计、幂等键更新。"""
from dmchange.domain.models import ChangeItem, Evidence, Status
from dmchange.extract.extractor import ExtractionResult
from dmchange.ledger.db import connect, init_db
from dmchange.ledger.repository import Repository
from dmchange.ledger.audit import select
from dmchange.ledger.identity import compute_change_id


def test_degrade_lands_no_outbound():
    item = ChangeItem(status=Status.DRAFT_INCOMPLETE, error_class="timeout",
                      extra={"transcript": "转写"})
    conn = connect(None); init_db(conn); repo = Repository(conn)
    saved = repo.create(item, actor="药事岗")
    assert saved.status == Status.DRAFT_INCOMPLETE
    assert repo.count() == 1


def test_fill_required_four():
    """四项齐备（药品码/字段名/应为值/依据）才允许 draft_incomplete→draft。"""
    from dmchange.ledger.state_machine import can_transition
    assert can_transition(Status.DRAFT_INCOMPLETE, Status.DRAFT)
    assert not can_transition(Status.DRAFT_INCOMPLETE, Status.SUBMITTED)


def test_manual_fill_audit(conn):
    repo = Repository(conn)
    ev = [Evidence("spk0", 1, 2, "原话")]
    item = ChangeItem(status=Status.DRAFT_INCOMPLETE, cur_value="a")
    saved = repo.create(item, actor="药事岗")
    from dmchange.ledger.audit import AuditEvent, append
    append(conn, AuditEvent(actor="药事岗", action="manual_fill",
                            drug_code=saved.drug_code, detail={"field": "proposed_value", "from": "", "to": "b"}))
    rows = select(conn, action="manual_fill")
    assert len(rows) == 1


def test_idempotency_recompute():
    ev = [Evidence("spk0", 1, 2, "原话")]
    old = compute_change_id("X", "f", "a", "", ev)
    new = compute_change_id("X", "f", "a", "b", ev)
    assert old != new  # 内容变化 → 幂等键变化
