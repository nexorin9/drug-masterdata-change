"""T30：退避间隔、断点续跑、状态不误推进、dead 重置。"""
from dmchange.outbound.outbox import (
    next_attempt_delay, enqueue, mark_attempt, resume, reset_dead, _row_to_entry, MAX_ATTEMPTS, summary,
)


def test_backoff():
    assert next_attempt_delay(0) < next_attempt_delay(1) < next_attempt_delay(2)
    assert next_attempt_delay(50) <= 300


def test_resume_pending(conn):
    enqueue(conn, "c1", {})
    assert resume(conn)["pending"] >= 1


def test_failure_keeps_submitted_state(conn):
    """出站失败条目状态由业务层控制为 submitted；outbox 只记 attempt。"""
    eid = enqueue(conn, "c1", {})
    row = conn.execute("SELECT * FROM outbox WHERE id=?", (eid,)).fetchone()
    state = mark_attempt(conn, _row_to_entry(row), success=False, error="net")
    assert state == "pending"
    # items 状态未被 outbox 改动
    assert conn.execute("SELECT COUNT(*) FROM items").fetchone()[0] == 0


def test_dead_reset(conn):
    eid = enqueue(conn, "c", {})
    state = ""
    for _ in range(MAX_ATTEMPTS + 1):
        row = conn.execute("SELECT * FROM outbox WHERE id=?", (eid,)).fetchone()
        state = mark_attempt(conn, _row_to_entry(row), success=False, error="e")
    assert state == "dead"
    reset_dead(conn, eid)
    assert summary(conn)["counts"]["pending"] == 1
