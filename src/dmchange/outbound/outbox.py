"""outbox 退避重试与断点续跑（T11/T30）。

提交动作与出站入队在同一事务；网络失败条目停 submitted 不标 acked；
指数退避，达到最大次数转 dead；进程重启可继续处理 pending。
"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Optional

from ..ledger.audit import now_iso

BASE_INTERVAL_S = 2
MAX_INTERVAL_S = 300
MAX_ATTEMPTS = 6


def next_attempt_delay(attempt_count: int, *, base: int = BASE_INTERVAL_S,
                       cap: int = MAX_INTERVAL_S) -> int:
    """指数退避：base * 2^attempt，封顶 cap。"""
    return min(cap, base * (2 ** max(0, attempt_count)))


@dataclass
class OutboxEntry:
    id: int
    change_id: str
    payload: dict[str, Any]
    attempt_count: int
    next_attempt_at: str
    last_error: str
    state: str


def _row_to_entry(r: sqlite3.Row) -> OutboxEntry:
    return OutboxEntry(
        int(r["id"]), r["change_id"], json.loads(r["payload_json"]),
        int(r["attempt_count"]), r["next_attempt_at"], r["last_error"], r["state"],
    )


def enqueue(conn: sqlite3.Connection, change_id: str, payload: dict[str, Any]) -> int:
    now = datetime.now(timezone.utc).isoformat()
    cur = conn.execute(
        "INSERT INTO outbox (change_id, payload_json, attempt_count, next_attempt_at, "
        "last_error, state, created_at) VALUES (?,?,?,?,?,?,?)",
        (change_id, json.dumps(payload, ensure_ascii=False), 0, now, "", "pending", now_iso()),
    )
    conn.commit()
    return int(cur.lastrowid)


def due_entries(conn: sqlite3.Connection, *, now: Optional[datetime] = None) -> list[OutboxEntry]:
    now = now or datetime.now(timezone.utc)
    rows = conn.execute("SELECT * FROM outbox WHERE state='pending' ORDER BY id").fetchall()
    out = []
    for r in rows:
        try:
            t = datetime.fromisoformat(r["next_attempt_at"].replace("Z", "+00:00"))
        except (ValueError, TypeError):
            t = now
        if t.tzinfo is None:
            t = t.replace(tzinfo=now.tzinfo)
        if t <= now:
            out.append(_row_to_entry(r))
    return out


def mark_attempt(conn: sqlite3.Connection, entry: OutboxEntry, *, success: bool,
                 error: str = "") -> str:
    """记录一次尝试；成功转 done，失败退避重试，超限转 dead。"""
    if success:
        conn.execute("UPDATE outbox SET state='done', last_error='' WHERE id=?", (entry.id,))
        conn.commit()
        return "done"
    attempt = entry.attempt_count + 1
    if attempt >= MAX_ATTEMPTS:
        conn.execute(
            "UPDATE outbox SET state='dead', attempt_count=?, last_error=? WHERE id=?",
            (attempt, error[:500], entry.id),
        )
        conn.commit()
        return "dead"
    nxt = (datetime.now(timezone.utc) + timedelta(seconds=next_attempt_delay(attempt))).isoformat()
    conn.execute(
        "UPDATE outbox SET state='pending', attempt_count=?, next_attempt_at=?, last_error=? WHERE id=?",
        (attempt, nxt, error[:500], entry.id),
    )
    conn.commit()
    return "pending"


def resume(conn: sqlite3.Connection) -> dict[str, int]:
    """断点续跑：重启后把因超时卡住的 pending 重新纳管（pending 保持，dead 需人工重置）。"""
    pending = conn.execute("SELECT COUNT(*) FROM outbox WHERE state='pending'").fetchone()[0]
    dead = conn.execute("SELECT COUNT(*) FROM outbox WHERE state='dead'").fetchone()[0]
    return {"pending": int(pending), "dead": int(dead)}


def reset_dead(conn: sqlite3.Connection, entry_id: int) -> None:
    conn.execute(
        "UPDATE outbox SET state='pending', attempt_count=0, last_error='' WHERE id=?", (entry_id,)
    )
    conn.commit()


def summary(conn: sqlite3.Connection) -> dict[str, Any]:
    """队列摘要：各状态条数、下一批重试时间、最近错误摘要。"""
    rows = conn.execute("SELECT state, COUNT(*) c FROM outbox GROUP BY state").fetchall()
    counts = {r["state"]: int(r["c"]) for r in rows}
    nxt = conn.execute(
        "SELECT MIN(next_attempt_at) t FROM outbox WHERE state='pending'"
    ).fetchone()["t"]
    err = conn.execute(
        "SELECT last_error FROM outbox WHERE last_error!='' ORDER BY id DESC LIMIT 1"
    ).fetchone()
    return {
        "counts": {s: counts.get(s, 0) for s in ("pending", "done", "dead")},
        "next_attempt_at": nxt or "",
        "last_error": err["last_error"] if err else "",
    }
