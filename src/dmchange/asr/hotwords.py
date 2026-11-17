"""热词包：由院内药品目录快照生成、版本化、增量重建、回滚、过期提示（T7/T20）。

paraformer 形态：gen_kw["hotword"] = " ".join(hotwords)（空格拼接）；
兼容列表形态 gen_kw["hotwords"]。热词覆盖通用名/剂型/规格/厂家。
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable, Optional

from ..audio.vad import Segment  # noqa: F401 - 保持 asr 层内聚
from ..ledger.audit import now_iso

MAX_WORDS = 500
STALE_AFTER_MINUTES = 60


def build_words(snapshot: Iterable[dict[str, Any]], *, max_words: int = MAX_WORDS) -> tuple[list[str], dict]:
    """从目录快照生成热词并清洗：去重、剔除超长/纯标点、按上限截断并计数。"""
    seen: set[str] = set()
    words: list[str] = []
    truncated = 0
    dropped = 0
    for item in snapshot:
        for key in ("generic_name", "dosage_form", "spec", "manufacturer"):
            w = str(item.get(key, "")).strip()
            if not w or len(w) > 20 or all(not ch.isalnum() for ch in w):
                dropped += 1
                continue
            if w in seen:
                continue
            if len(words) >= max_words:
                truncated += 1
                continue
            seen.add(w)
            words.append(w)
    return words, {"truncated": truncated, "dropped": dropped, "total": len(words)}


def pkg_hash(words: list[str]) -> str:
    return hashlib.sha256("\n".join(words).encode("utf-8")).hexdigest()


def as_gen_kw(words: list[str], *, model: str = "paraformer") -> dict[str, Any]:
    """按 paraformer / 其他模型形态产出识别引擎关键字参数。"""
    if model == "paraformer":
        return {"hotword": " ".join(words)}
    return {"hotwords": list(words)}


@dataclass
class HotwordPackage:
    version: int
    words: list[str]
    hash: str
    source_snapshot_id: str
    source_updated_at: str
    state: str = "active"
    word_count: int = 0


def rebuild(
    conn: sqlite3.Connection,
    snapshot: Iterable[dict[str, Any]],
    *,
    source_snapshot_id: str = "",
    source_updated_at: str = "",
    incremental: bool = False,
) -> HotwordPackage:
    """基于快照重建（或增量追加）热词包；旧版本保留标 stale，不删除。"""
    conn.execute("UPDATE hotword_packages SET state='stale' WHERE state='active'")
    row = conn.execute("SELECT MAX(version) AS v FROM hotword_packages").fetchone()
    new_version = int(row["v"] or 0) + 1
    words, _ = build_words(snapshot)
    if incremental:
        prev = conn.execute(
            "SELECT words_json FROM hotword_packages WHERE version=?", (new_version - 1,)
        ).fetchone()
        if prev:
            old = json.loads(prev["words_json"])
            merged = list(old)
            for w in words:
                if w not in merged:
                    merged.append(w)
            words = merged
    h = pkg_hash(words)
    conn.execute(
        "INSERT INTO hotword_packages (version, pkg_hash, source_snapshot_id, source_updated_at, "
        "word_count, words_json, state, created_at) VALUES (?,?,?,?,?,?,?,?)",
        (new_version, h, source_snapshot_id, source_updated_at, len(words),
         json.dumps(words, ensure_ascii=False), "active", now_iso()),
    )
    conn.commit()
    return HotwordPackage(new_version, words, h, source_snapshot_id, source_updated_at,
                          "active", len(words))


def rollback(conn: sqlite3.Connection, version: int) -> Optional[HotwordPackage]:
    """回滚只切版本指针（state 标记），不删除历史包。"""
    row = conn.execute("SELECT * FROM hotword_packages WHERE version=?", (version,)).fetchone()
    if not row:
        return None
    conn.execute("UPDATE hotword_packages SET state='stale' WHERE state='active'")
    conn.execute("UPDATE hotword_packages SET state='active' WHERE version=?", (version,))
    conn.commit()
    return HotwordPackage(
        int(row["version"]), json.loads(row["words_json"]), row["pkg_hash"],
        row["source_snapshot_id"], row["source_updated_at"], "active", int(row["word_count"]),
    )


def active_package(conn: sqlite3.Connection) -> Optional[HotwordPackage]:
    row = conn.execute("SELECT * FROM hotword_packages WHERE state='active' ORDER BY version DESC LIMIT 1").fetchone()
    if not row:
        return None
    return HotwordPackage(
        int(row["version"]), json.loads(row["words_json"]), row["pkg_hash"],
        row["source_snapshot_id"], row["source_updated_at"], row["state"], int(row["word_count"]),
    )


def staleness_notice(pkg: Optional[HotwordPackage], *, now: Optional[datetime] = None) -> str:
    """热词包 stale 或快照超期时产出可见提示文本，供界面与导出共用。"""
    if pkg is None:
        return "尚未生成热词包，请先同步药品目录"
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    try:
        updated = datetime.fromisoformat(pkg.source_updated_at.replace("Z", "+00:00"))
        if updated.tzinfo is None:
            updated = updated.replace(tzinfo=timezone.utc)
        age = now - updated
        if age > timedelta(minutes=STALE_AFTER_MINUTES):
            return f"目录/热词已过期（上次 {updated.strftime('%H:%M')}）"
    except (ValueError, TypeError):
        pass
    if pkg.state == "stale":
        return "热词包已过时，请重建后使用"
    return ""
