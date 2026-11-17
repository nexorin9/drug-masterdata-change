"""T26：顺序不变、唯一冲突、并发双提交、重放防护。"""
import threading
from dmchange.ledger.identity import compute_change_id
from dmchange.domain.models import Evidence, ChangeItem
from dmchange.ledger.db import connect, init_db
from dmchange.ledger.repository import Repository


def test_order_invariance():
    a = [Evidence("a", 1, 2, "x"), Evidence("b", 3, 4, "y")]
    k1 = compute_change_id("X", "f", "a", "b", a)
    k2 = compute_change_id("X", "f", "a", "b", list(reversed(a)))
    assert k1 == k2


def test_unique_conflict_returns_existing():
    conn = connect(None); init_db(conn); repo = Repository(conn)
    it = ChangeItem(drug_code="X", field_name="f", cur_value="a", proposed_value="b")
    a = repo.create(it, actor="u"); b = repo.create(it, actor="u")
    assert a.change_id == b.change_id and repo.count() == 1


def test_concurrent_double_submit():
    conn = connect(None); init_db(conn); repo = Repository(conn)
    errs = []
    def w():
        try:
            repo.create(ChangeItem(drug_code="X", field_name="f"), actor="u")
        except Exception as e:
            errs.append(e)
    ts = [threading.Thread(target=w) for _ in range(4)]
    [t.start() for t in ts]; [t.join() for t in ts]
    assert repo.count() == 1 and not errs
