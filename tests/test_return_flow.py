"""T28：退回留痕、空意见拒绝、连续两次退回、再提交 superseded。"""
import pytest
from dmchange.domain.models import ChangeItem, Evidence, Status
from dmchange.domain.errors import IllegalTransition
from dmchange.ledger.db import connect, init_db
from dmchange.ledger.repository import Repository
from dmchange.ledger.audit import select


def _item():
    return ChangeItem(drug_code="X", field_name="spec_pack_code", cur_value="a",
                      proposed_value="b", submitted_by="张三",
                      evidence=[Evidence("s", 1, 2, "原话")])


def test_empty_comment_rejected(conn):
    repo = Repository(conn)
    it = repo.create(_item(), actor="张三")
    repo.send_to_review(it.change_id, actor="张三")
    with pytest.raises(IllegalTransition):
        repo.return_item(it.change_id, "", actor="李四")


def test_return_logged(conn):
    repo = Repository(conn)
    it = repo.create(_item(), actor="张三")
    repo.send_to_review(it.change_id, actor="张三")
    repo.return_item(it.change_id, "规格口径需复核", actor="李四")
    rows = select(conn, action="returned")
    assert rows and any("规格口径需复核" in str(r) for r in rows)


def test_double_return_two_audits(conn):
    repo = Repository(conn)
    it = repo.create(_item(), actor="张三")
    repo.send_to_review(it.change_id, actor="张三")
    repo.return_item(it.change_id, "第一次", actor="李四")
    repo.fill_and_confirm(it.change_id, actor="张三")
    repo.send_to_review(it.change_id, actor="张三")
    repo.return_item(it.change_id, "第二次", actor="李四")
    rows = select(conn, action="returned")
    comments = [r for r in rows if "review_comment" in r.get("detail_json", "")]
    assert len(comments) == 2


def test_resubmit_supersedes_old(conn):
    repo = Repository(conn)
    it = repo.create(_item(), actor="张三")
    repo.send_to_review(it.change_id, actor="张三")
    repo.return_item(it.change_id, "改一下", actor="李四")
    new = repo.resubmit(it.change_id, actor="张三")
    assert new.status == Status.DRAFT
    rows = select(conn, action="duplicated_submit")
    assert any("superseded" in str(r) for r in rows)
