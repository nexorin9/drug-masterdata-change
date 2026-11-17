"""T17：段抖动/重叠/超长/全静音/噪声五类 + 单调性。"""
from dmchange.asr.segment_decode import SegmentSmoother
from dmchange.audio.vad import Segment


def test_jitter():
    sm = SegmentSmoother(silence_threshold_ms=300)
    out = sm.smooth([Segment(0, 1000), Segment(1100, 1800)])
    assert len(out) == 1 and out[0].end_ms == 1800


def test_overlap_half():
    sm = SegmentSmoother()
    out = sm.smooth([Segment(0, 1000), Segment(500, 2000)])
    assert len(out) == 1 and out[0].duration_ms == 2000


def test_long_25s():
    sm = SegmentSmoother(long_segment_ms=20000, cut_chunk_ms=10000)
    out = sm.smooth([Segment(0, 25000)])
    assert len(out) == 3 and all(s.duration_ms <= 10000 for s in out)
    assert any(e.reason == "hard" for e in sm.events)


def test_all_silence():
    sm = SegmentSmoother()
    # VAD 无段 → 空列表
    assert sm.smooth([]) == []


def test_noise_short_dropped():
    sm = SegmentSmoother(min_segment_ms=200)
    out = sm.smooth([Segment(0, 80)])
    assert out == [] and any(e.reason == "too_short" for e in sm.events)


def test_monotonic_after_smooth():
    sm = SegmentSmoother()
    out = sm.smooth([Segment(0, 1000), Segment(1200, 1800), Segment(2000, 3000)])
    ends = [s.end_ms for s in out]
    starts = [s.start_ms for s in out]
    assert all(a <= b for a, b in zip(starts, ends))
    assert all(out[i].end_ms <= out[i+1].start_ms for i in range(len(out)-1))
