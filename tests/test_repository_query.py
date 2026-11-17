"""T25：四表读写、索引、过滤、分页排序、一致性、2000 条 P95。"""
import time

from dmchange.domain.models import ChangeItem, Evidence
from dmchange.ledger.db import connect, init_db
from dmchange.ledger.repository import Repository


def _item(code, status, by, cur="", prop="b"):
    return ChangeItem(drug_code=code, field_name="spec_pack_code", cur_value=cur or "a",
                      proposed_value=prop, submitted_by=by,
                      evidence=[Evidence("spk0", 1, 2, "原话")], status=status)


def test_four_filters(conn):
    repo = Repository(conn)
    repo.create(_item("X1", "draft", "张三", prop="p1"))
    repo.create(_item("X2", "submitted", "李四", prop="p2"))
    repo.create(_item("X1", "acked", "张三", prop="p3"))
    assert len(repo.query(status="draft")) == 1
    assert len(repo.query(drug_code="X1")) == 2
    assert len(repo.query(submitted_by="张三")) == 2
    assert len(repo.query(keyword="原话")) == 3


def test_pagination_sort():
    conn = connect(None); init_db(conn); repo = Repository(conn)
    for i in range(10):
        repo.create(_item(f"X{i}", "draft", "张三", cur=str(i)))
    page = repo.query(limit=3, offset=0, order_by="drug_code", desc=False)
    assert len(page) == 3 and page[0].drug_code == "X0"


def test_consistency_warning(conn):
    repo = Repository(conn)
    repo.create(_item("X1", "draft", "张三"))
    assert repo.consistency_warnings() == []


def test_index_used():
    conn = connect(None); init_db(conn)
    plan = conn.execute("EXPLAIN QUERY PLAN SELECT * FROM items WHERE status='draft'").fetchall()
    assert any("INDEX" in str(r[3]).upper() or "USING INDEX" in str(r).upper() for r in plan)


def test_2000_scale_p95():
    conn = connect(None); init_db(conn); repo = Repository(conn)
    for i in range(2000):
        repo.create(_item(f"X{i%300}", "draft", f"用户{i%10}", cur=str(i)))
    lat = []
    for _ in range(20):
        t = time.time(); repo.query(status="draft", drug_code="X1", limit=50); lat.append((time.time()-t)*1000)
    p95 = sorted(lat)[18]
    print(f"\n[scale] 2000 条查询 P95 = {p95:.2f}ms")
    assert p95 < 1000
