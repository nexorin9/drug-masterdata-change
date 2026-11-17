"""SQLite 台账 schema：四张表 + 索引。

- items：变更条目，change_id 唯一约束（幂等兜底）
- audit_log：只增不改审计链
- dictionary_snapshot：药品目录快照（外置可更新）
- hotword_packages：热词包版本
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional, Union

SCHEMA = """
CREATE TABLE IF NOT EXISTS items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    change_id TEXT NOT NULL UNIQUE,
    drug_code TEXT NOT NULL,
    field_name TEXT NOT NULL,
    cur_value TEXT NOT NULL DEFAULT '',
    proposed_value TEXT NOT NULL DEFAULT '',
    cur_value_normalized TEXT NOT NULL DEFAULT '',
    proposed_value_normalized TEXT NOT NULL DEFAULT '',
    evidence_json TEXT NOT NULL DEFAULT '[]',
    evidence_source TEXT NOT NULL DEFAULT 'voice',
    submitted_by TEXT NOT NULL DEFAULT '',
    reviewed_by TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'draft',
    error_class TEXT,
    generic_name TEXT NOT NULL DEFAULT '',
    candidate_codes_json TEXT NOT NULL DEFAULT '[]',
    code_pending_manual INTEGER NOT NULL DEFAULT 0,
    review_comment TEXT NOT NULL DEFAULT '',
    reject_reason TEXT NOT NULL DEFAULT '',
    receipt_no TEXT NOT NULL DEFAULT '',
    receipt_at TEXT NOT NULL DEFAULT '',
    demo INTEGER NOT NULL DEFAULT 0,
    extra_json TEXT NOT NULL DEFAULT '{}',
    previous_change_id TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    actor TEXT NOT NULL DEFAULT '',
    action TEXT NOT NULL,
    drug_code TEXT NOT NULL DEFAULT '',
    field_name TEXT NOT NULL DEFAULT '',
    cur_value TEXT NOT NULL DEFAULT '',
    proposed_value TEXT NOT NULL DEFAULT '',
    evidence_json TEXT NOT NULL DEFAULT '[]',
    detail_json TEXT NOT NULL DEFAULT '{}',
    at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS dictionary_snapshot (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    drug_code TEXT NOT NULL,
    generic_name TEXT NOT NULL DEFAULT '',
    dosage_form TEXT NOT NULL DEFAULT '',
    spec TEXT NOT NULL DEFAULT '',
    manufacturer TEXT NOT NULL DEFAULT '',
    updated_at TEXT NOT NULL DEFAULT '',
    synced_at TEXT NOT NULL DEFAULT '',
    snapshot_id TEXT NOT NULL DEFAULT '',
    UNIQUE(drug_code, snapshot_id)
);

CREATE TABLE IF NOT EXISTS hotword_packages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    version INTEGER NOT NULL,
    pkg_hash TEXT NOT NULL,
    source_snapshot_id TEXT NOT NULL DEFAULT '',
    source_updated_at TEXT NOT NULL DEFAULT '',
    word_count INTEGER NOT NULL DEFAULT 0,
    words_json TEXT NOT NULL DEFAULT '[]',
    state TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL,
    UNIQUE(version)
);

-- outbox（T30 建立，提前纳入 schema 以便一次性建表）
CREATE TABLE IF NOT EXISTS outbox (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    change_id TEXT NOT NULL,
    payload_json TEXT NOT NULL DEFAULT '{}',
    attempt_count INTEGER NOT NULL DEFAULT 0,
    next_attempt_at TEXT NOT NULL DEFAULT '',
    last_error TEXT NOT NULL DEFAULT '',
    state TEXT NOT NULL DEFAULT 'pending',
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_items_status ON items(status);
CREATE INDEX IF NOT EXISTS idx_items_drug_code ON items(drug_code);
CREATE INDEX IF NOT EXISTS idx_items_created_at ON items(created_at);
CREATE INDEX IF NOT EXISTS idx_items_submitted_by ON items(submitted_by);
CREATE INDEX IF NOT EXISTS idx_audit_drug_at ON audit_log(drug_code, at);
CREATE INDEX IF NOT EXISTS idx_outbox_state_next ON outbox(state, next_attempt_at);
"""


def connect(db_path: Union[str, Path, None] = None) -> sqlite3.Connection:
    """建立连接。db_path=None 用内存库（测试友好）；调用方负责关闭。"""
    if db_path is None:
        conn = sqlite3.connect(":memory:", check_same_thread=False)
    else:
        path = Path(db_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    """幂等建表：可重复调用不破坏数据。"""
    conn.executescript(SCHEMA)
    conn.commit()


def table_names(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    return sorted(r["name"] for r in rows)


def reset_db(conn: sqlite3.Connection) -> None:
    """仅用于测试：清空所有业务表。"""
    for name in ("items", "audit_log", "dictionary_snapshot", "hotword_packages", "outbox"):
        conn.execute(f"DELETE FROM {name}")
    conn.commit()
