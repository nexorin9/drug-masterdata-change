"""目录快照存储：加载目录到 dictionary_snapshot 表，提供检索与候选返回。

drug_code 与 field_name 由目录表硬匹配决定（模型不碰）；通用名命中多条返回多候选，
由守门层判歧义拒绝。字典表外置可更新，换快照不改代码。
"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from typing import Any, Iterable, Optional

from ..domain.errors import AmbiguousDrugMatch, DrugNotFound
from ..ledger.audit import now_iso


@dataclass
class DrugEntry:
    drug_code: str
    generic_name: str = ""
    dosage_form: str = ""
    spec: str = ""
    manufacturer: str = ""
    updated_at: str = ""


def load_snapshot(conn: sqlite3.Connection, items: Iterable[dict[str, Any]],
                  *, snapshot_id: str = "", synced_at: str = "") -> int:
    """加载目录快照（幂等：同 snapshot_id + drug_code 覆盖）。"""
    synced_at = synced_at or now_iso()
    count = 0
    for it in items:
        conn.execute(
            "INSERT INTO dictionary_snapshot "
            "(drug_code, generic_name, dosage_form, spec, manufacturer, updated_at, synced_at, snapshot_id) "
            "VALUES (?,?,?,?,?,?,?,?) "
            "ON CONFLICT(drug_code, snapshot_id) DO UPDATE SET "
            "generic_name=excluded.generic_name, dosage_form=excluded.dosage_form, "
            "spec=excluded.spec, manufacturer=excluded.manufacturer, "
            "updated_at=excluded.updated_at, synced_at=excluded.synced_at",
            (
                str(it.get("drug_code", "")), str(it.get("generic_name", "")),
                str(it.get("dosage_form", "")), str(it.get("spec", "")),
                str(it.get("manufacturer", "")), str(it.get("updated_at", "")),
                synced_at, snapshot_id,
            ),
        )
        count += 1
    conn.commit()
    return count


def latest_entries(conn: sqlite3.Connection) -> list[DrugEntry]:
    rows = conn.execute(
        "SELECT * FROM dictionary_snapshot WHERE id IN "
        "(SELECT MAX(id) FROM dictionary_snapshot GROUP BY drug_code)"
    ).fetchall()
    return [DrugEntry(
        r["drug_code"], r["generic_name"], r["dosage_form"],
        r["spec"], r["manufacturer"], r["updated_at"],
    ) for r in rows]


def by_code(conn: sqlite3.Connection, code: str) -> Optional[DrugEntry]:
    r = conn.execute(
        "SELECT * FROM dictionary_snapshot WHERE drug_code=? ORDER BY id DESC LIMIT 1", (code,)
    ).fetchone()
    if not r:
        return None
    return DrugEntry(r["drug_code"], r["generic_name"], r["dosage_form"],
                     r["spec"], r["manufacturer"], r["updated_at"])
