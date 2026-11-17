"""T6/T17：给定 VAD 段边界时只解码已闭合段；段调度器边界加固。"""
from dmchange.asr.segment_decode import SegmentSmoother, decode_segments
from dmchange.audio.vad import Segment


def test_only_closed_segments_decoded():
    segs = [Segment(0, 1000), Segment(2000, 3000), Segment(4000, 5000)]
    got = decode_segments(segs, cursor_ms=3000, decoder=lambda s: f"文本{s.start_ms}")
    assert [u.start_ms for u in got.utterances] == [0, 2000]  # 4000-5000 未闭合


def test_output_monotonic():
    segs = [Segment(0, 1000), Segment(1001, 2000)]
    got = decode_segments(segs, cursor_ms=5000, decoder=lambda s: "文本")
    ms = [(u.start_ms, u.end_ms) for u in got.utterances]
    assert ms == sorted(ms)


def test_jitter_merge():
    sm = SegmentSmoother(silence_threshold_ms=300)
    out = sm.smooth([Segment(0, 1000), Segment(1200, 2000)])
    assert len(out) == 1
    assert out[0].start_ms == 0 and out[0].end_ms == 2000
    assert any(e.kind == "merged" for e in sm.events)


def test_overlap_dedup():
    sm = SegmentSmoother()
    out = sm.smooth([Segment(0, 1000), Segment(200, 1800)])
    assert len(out) == 1
    assert out[0].duration_ms == 1800  # 保留较长段


def test_long_segment_cut():
    sm = SegmentSmoother(long_segment_ms=20000, cut_chunk_ms=10000)
    out = sm.smooth([Segment(0, 25000)])
    assert len(out) == 3
    assert all(s.duration_ms <= 10000 for s in out)
    assert any(e.kind == "cut" for e in sm.events)


def test_too_short_dropped():
    sm = SegmentSmoother(min_segment_ms=200)
    out = sm.smooth([Segment(0, 100)])
    assert len(out) == 0
    assert any(e.reason == "too_short" for e in sm.events)


def test_empty_decoder_result():
    got = decode_segments([Segment(0, 1000)], 2000, decoder=lambda s: "")
    assert len(got.utterances) == 0
