"""T7/T20：热词包来自目录、版本递增、hash 稳定、增量/回滚/过期/清洗。"""
import json
from datetime import datetime, timedelta, timezone

from dmchange.asr.hotwords import (
    active_package, as_gen_kw, build_words, pkg_hash, rebuild, rollback, staleness_notice,
)
from dmchange.ledger.db import connect, init_db


SNAP = [
    {"generic_name": "阿莫西林胶囊", "dosage_form": "胶囊", "spec": "0.25g", "manufacturer": "石药"},
    {"generic_name": "阿莫西林胶囊", "dosage_form": "胶囊", "spec": "0.5g", "manufacturer": "石药"},
    {"generic_name": "二甲双胍片", "dosage_form": "片", "spec": "0.5g", "manufacturer": "格华止"},
]


def test_build_words_from_snapshot():
    words, stat = build_words(SNAP)
    assert "阿莫西林胶囊" in words and "胶囊" in words
    assert stat["dropped"] >= 0


def test_paraformer_shape():
    kw = as_gen_kw(["甲", "乙"])
    assert kw["hotword"] == "甲 乙"
    assert as_gen_kw(["甲"], model="other")["hotwords"] == ["甲"]


def test_hash_stable():
    assert pkg_hash(["a", "b"]) == pkg_hash(["a", "b"])
    assert pkg_hash(["a", "b"]) != pkg_hash(["b", "a"])


def test_versioning_and_rollback(conn):
    v1 = rebuild(conn, SNAP, source_snapshot_id="s1")
    assert v1.version == 1
    v2 = rebuild(conn, SNAP, source_snapshot_id="s2")
    assert v2.version == 2
    assert active_package(conn).version == 2
    rb = rollback(conn, 1)
    assert rb.version == 1
    assert active_package(conn).version == 1


def test_incremental(conn):
    rebuild(conn, SNAP[:2])
    v2 = rebuild(conn, SNAP, incremental=True)
    assert "二甲双胍片" in v2.words
    assert "阿莫西林胶囊" in v2.words


def test_empty_snapshot_no_crash():
    words, stat = build_words([])
    assert words == [] and stat["total"] == 0


def test_staleness_notice():
    from dmchange.asr.hotwords import HotwordPackage
    old = (datetime.now(timezone.utc) - timedelta(hours=3)).isoformat()
    pkg = HotwordPackage(1, [], "h", "s", old)
    notice = staleness_notice(pkg)
    assert "过期" in notice
