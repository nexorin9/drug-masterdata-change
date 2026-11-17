"""T4：合法迁移表逐条覆盖 + 非法迁移抛错记审计。"""
import pytest

from dmchange.domain.errors import IllegalTransition, ReviewerMismatch
from dmchange.domain.models import ChangeItem, Evidence, Status
from dmchange.ledger import audit as audit_mod
from dmchange.ledger.repository import Repository
from dmchange.ledger.state_machine import (
    TRANSITIONS, assert_transition, can_transition, legal_transitions,
)


def _item(**kw):
    base = dict(
        drug_code="XA1234ABCD12345678ABCDE", field_name="spec_pack_code",
        cur_value="0.25g", proposed_value="0.5g",
        evidence=[Evidence("spk0", 8000, 15000, "不是0.25，是0.5")],
    )
    base.update(kw)
    return ChangeItem(**base)


def test_all_legal_transitions():
    for src, dsts in TRANSITIONS.items():
        for dst in dsts:
            assert can_transition(src, dst)
            assert assert_transition(src, dst) == dst


def test_illegal_transition_raises():
    with pytest.raises(IllegalTransition):
        assert_transition(Status.ACKED, Status.DRAFT)
    assert not can_transition(Status.REJECTED, Status.SUBMITTED)


def test_illegal_transition_records_audit(conn):
    repo = Repository(conn)
    item = repo.create(_item(status=Status.ACKED), actor="tester")
    with pytest.raises(IllegalTransition):
        repo.fill_and_confirm(item.change_id, actor="tester")
    rows = audit_mod.select(conn, action="illegal_transition")
    assert len(rows) >= 1


def test_full_happy_path(conn):
    repo = Repository(conn)
    it = repo.create(_item(), actor="药事岗")
    assert it.status == Status.DRAFT
    it = repo.send_to_review(it.change_id, actor="药事岗")
    assert it.status == Status.PENDING_REVIEW
    it = repo.submit(it.change_id, actor="复核人")
    assert it.status == Status.SUBMITTED
    it = repo.ack(it.change_id, receipt_no="RC-001", receipt_at="2026-01-01T09:00:00")
    assert it.status == Status.ACKED
    assert it.receipt_no == "RC-001"


def test_same_reviewer_blocked(conn):
    repo = Repository(conn)
    it = repo.create(_item(submitted_by="张三", reviewed_by="张三"), actor="张三")
    repo.send_to_review(it.change_id, actor="张三")
    with pytest.raises(ReviewerMismatch):
        repo.submit(it.change_id, actor="张三")
    assert repo.get_by_change_id(it.change_id).status == Status.PENDING_REVIEW


def test_submit_without_review_blocked(conn):
    repo = Repository(conn)
    it = repo.create(_item(status=Status.DRAFT, submitted_by="张三"), actor="张三")
    with pytest.raises(IllegalTransition):
        repo.submit(it.change_id, actor="复核人")
