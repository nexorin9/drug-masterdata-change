"""T20：重建/增量/回滚/过期/清洗五类。"""
from dmchange.asr.hotwords import (
    active_package, build_words, rebuild, rollback, staleness_notice,
)
from dmchange.asr.hotwords import HotwordPackage


SNAP1 = [{"generic_name": "阿莫西林", "dosage_form": "胶囊", "spec": "0.25g", "manufacturer": "石药"}]
SNAP2 = SNAP1 + [{"generic_name": "二甲双胍", "dosage_form": "片", "spec": "0.5g", "manufacturer": "格华止"}]


def test_rebuild_increments(conn):
    a = rebuild(conn, SNAP1)
    b = rebuild(conn, SNAP2)
    assert b.version == a.version + 1


def test_rollback_preserves_history(conn):
    rebuild(conn, SNAP1)
    rebuild(conn, SNAP2)
    r = rollback(conn, 1)
    assert r and r.version == 1
    assert active_package(conn).version == 1


def test_incremental_append_only(conn):
    rebuild(conn, SNAP1)
    v2 = rebuild(conn, SNAP2, incremental=True)
    assert "阿莫西林" in v2.words and "二甲双胍" in v2.words
    # 原顺序保持
    assert v2.words.index("阿莫西林") < v2.words.index("二甲双胍")


def test_stale_notice():
    pkg = HotwordPackage(1, [], "h", "s1", "2020-01-01T00:00:00+08:00", state="active")
    assert "过期" in staleness_notice(pkg)
    assert "热词包" in staleness_notice(None)


def test_cleaning_dedup_truncate():
    snap = [{"generic_name": "重复药", "dosage_form": "重复药"}] * 3
    words, stat = build_words(snap, max_words=1)
    assert len(words) == 1 and stat["truncated"] >= 0
