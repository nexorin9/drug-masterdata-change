"""T36：八阶段埋点、摘要字段、凭据掩码。"""
import json
from dmchange.logging_utils import STAGES, RunSummary, StageTimer, json_line, mask


def test_eight_stages():
    assert len(STAGES) == 8
    for s in ("capture", "unify", "vad", "decode", "extract", "guard", "ledger", "outbound"):
        assert s in STAGES


def test_stage_timing():
    rs = RunSummary(input_source="mic", segment_count=3, item_count=1)
    for s in STAGES:
        with StageTimer(rs, s):
            pass
    assert len(rs.stages) == 8
    d = rs.to_dict()
    assert d["input_source"] == "mic" and d["segment_count"] == 3
    assert all("duration_ms" in x for x in d["stages"])


def test_mask():
    text = "Authorization: Bearer sk-secret-12345 path=/data/rec.wav"
    out = mask(text)
    assert "sk-secret-12345" not in out and "rec.wav" not in out
    assert "Bearer ***" in out


def test_json_line():
    line = json_line("stage_done", stage="vad", duration_ms=12)
    d = json.loads(line)
    assert d["stage"] == "vad" and d["duration_ms"] == 12
