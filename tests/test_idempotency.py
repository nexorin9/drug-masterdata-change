"""T4/T26：同一核实重复提交库中仅 1 条；change_id 稳定；证据乱序不变。"""
import threading

from dmchange.domain.models import ChangeItem, Evidence
from dmchange.ledger.identity import compute_change_id, evidence_sha256
from dmchange.ledger.repository import Repository


def _item(**kw):
    base = dict(
        drug_code="XA1234ABCD12345678ABCDE", field_name="spec_pack_code",
        cur_value="0.25g", proposed_value="0.5g",
        evidence=[Evidence("spk0", 8000, 15000, "不是0.25，是0.5")],
    )
    base.update(kw)
    return ChangeItem(**base)


def test_same_verification_same_change_id():
    a = compute_change_id("X", "spec_pack_code", "0.25g", "0.5g",
                          [Evidence("spk0", 1, 2, "甲"), Evidence("spk1", 3, 4, "乙")])
    b = compute_change_id("X", "spec_pack_code", "0.25g", "0.5g",
                          [Evidence("spk1", 3, 4, "乙"), Evidence("spk0", 1, 2, "甲")])
    assert a == b


def test_no_timestamp_in_key():
    """改变时钟不影响 change_id——输入里根本没有时间分量。"""
    a = compute_change_id("X", "f", "a", "b", [])
    b = compute_change_id("X", "f", "a", "b", [])
    assert a == b and len(a) == 64


def test_duplicate_submit_single_row(conn):
    repo = Repository(conn)
    i1 = repo.create(_item(), actor="药事岗")
    i2 = repo.create(_item(), actor="药事岗")
    assert i1.change_id == i2.change_id
    assert repo.count() == 1


def test_concurrent_double_submit_single_row(conn):
    repo = Repository(conn)
    results = []
    barrier = threading.Barrier(2)

    def worker():
        barrier.wait()
        results.append(repo.create_or_get(_item(), actor="药事岗").change_id)

    t1 = threading.Thread(target=worker)
    t2 = threading.Thread(target=worker)
    t1.start(); t2.start(); t1.join(); t2.join()
    assert repo.count() == 1
    assert results[0] == results[1]
