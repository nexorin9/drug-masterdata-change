"""VAD 段驱动增量解码 + 段边界加固（T6/T17）。

只解码已闭合 VAD 段；段抖动合并、重叠去重、超长切分、丢弃原因枚举，
保证输出毫秒区间单调不重叠（违反抛错，不返回乱序区间）。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Iterable, Optional

from ..audio.vad import Segment
from ..domain.models import Utterance


@dataclass
class SegmentEvent:
    kind: str  # merged / dropped_overlap / cut / dropped
    reason: str = ""
    segment: Optional[Segment] = None


@dataclass
class SegmentSmoother:
    """段边界策略：合并抖动、去重重叠、切分超长、丢弃无效段。"""

    silence_threshold_ms: int = 300
    overlap_ratio_threshold: float = 0.5
    long_segment_ms: int = 20_000
    cut_chunk_ms: int = 10_000
    min_segment_ms: int = 200
    events: list[SegmentEvent] = field(default_factory=list)

    def smooth(self, segments: Iterable[Segment]) -> list[Segment]:
        segs = [Segment(int(s.start_ms), int(s.end_ms)) for s in segments]
        segs = [s for s in segs if s.end_ms > s.start_ms]
        # 1. 抖动合并：间隔小于静音阈值则并集
        merged: list[Segment] = []
        for s in segs:
            if merged and s.start_ms - merged[-1].end_ms < self.silence_threshold_ms:
                prev = merged[-1]
                merged[-1] = Segment(prev.start_ms, max(prev.end_ms, s.end_ms))
                self.events.append(SegmentEvent("merged", "jitter", s))
            else:
                merged.append(s)
        # 2. 重叠去重：重叠 > 阈值保留较长段
        dedup: list[Segment] = []
        for s in merged:
            if dedup and dedup[-1].overlap_ratio(s) > self.overlap_ratio_threshold:
                keep = max((dedup[-1], s), key=lambda x: x.duration_ms)
                drop = s if keep is dedup[-1] else dedup[-1]
                self.events.append(SegmentEvent("dropped_overlap", "overlap>50%", drop))
                if dedup[-1] is not keep:
                    dedup[-1] = keep
            else:
                dedup.append(s)
        # 3. 超长切分 + 4. 丢弃过短/空
        final: list[Segment] = []
        for s in dedup:
            if s.duration_ms < self.min_segment_ms:
                self.events.append(SegmentEvent("dropped", "too_short", s))
                continue
            if s.duration_ms > self.long_segment_ms:
                cursor = s.start_ms
                while cursor < s.end_ms:
                    ce = min(cursor + self.cut_chunk_ms, s.end_ms)
                    final.append(Segment(cursor, ce))
                    self.events.append(SegmentEvent("cut", "hard", Segment(cursor, ce)))
                    cursor = ce
            else:
                final.append(s)
        # 5. 单调不重叠断言
        for a, b in zip(final, final[1:]):
            if a.end_ms > b.start_ms:
                raise ValueError("段区间重叠未消除，拒绝返回乱序区间")
        return final


@dataclass
class DecodeResult:
    utterances: list[Utterance]
    segments_decoded: list[Segment]
    events: list[SegmentEvent]


def decode_segments(
    segments: Iterable[Segment],
    cursor_ms: int,
    decoder: Callable[[Segment], Optional[str]],
    *,
    smoother: Optional[SegmentSmoother] = None,
    speaker_for: Optional[Callable[[Segment], Optional[str]]] = None,
) -> DecodeResult:
    """只解码已闭合段（end <= cursor）；返回按段出句的 Utterance 列表。"""
    smoother = smoother or SegmentSmoother()
    smoothed = smoother.smooth(segments)
    decoded: list[Segment] = []
    utterances: list[Utterance] = []
    for seg in smoothed:
        if seg.end_ms > cursor_ms:
            continue  # 未闭合，不解码
        text = decoder(seg)
        if text is None or not text.strip():
            smoother.events.append(SegmentEvent("dropped", "empty_result", seg))
            continue
        decoded.append(seg)
        utterances.append(Utterance(
            text=text.strip(), start_ms=seg.start_ms, end_ms=seg.end_ms,
            speaker=speaker_for(seg) if speaker_for else None,
            index=len(utterances),
        ))
    return DecodeResult(utterances, decoded, smoother.events)
