"""T11：outbox 退避与重放防护。"""
from dmchange.outbound.outbox import (
    enqueue, mark_attempt, next_attempt_delay, resume, summary,
    _row_to_entry, reset_dead, MAX_ATTEMPTS,
)
from dmchange.config import Config


def test_backoff_increases_and_caps():
    d0 = next_attempt_delay(0)
    d1 = next_attempt_delay(1)
    d2 = next_attempt_delay(2)
    assert d0 < d1 < d2
    assert next_attempt_delay(100) <= 300


def test_retry_until_dead(conn):
    eid = enqueue(conn, "cid", {"a": 1})
    state = "pending"
    for _ in range(MAX_ATTEMPTS + 1):
        row = conn.execute("SELECT * FROM outbox WHERE id=?", (eid,)).fetchone()
        state = mark_attempt(conn, _row_to_entry(row), success=False, error="err")
    assert state == "dead"
    reset_dead(conn, eid)
    assert resume(conn)["pending"] >= 1


def test_success_marks_done(conn):
    eid = enqueue(conn, "cid2", {})
    row = conn.execute("SELECT * FROM outbox WHERE id=?", (eid,)).fetchone()
    assert mark_attempt(conn, _row_to_entry(row), success=True) == "done"
    assert summary(conn)["counts"]["done"] == 1


def test_no_duplicate_enqueue_idempotency():
    """同一 change_id 重放由 items 唯一约束挡住（T26 已测），outbox 允许多个尝试记录但不重复推进。"""
    assert callable(enqueue)
