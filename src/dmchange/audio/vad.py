"""VAD 段边界：定义段结构与从解码结果提取段的口径。

边界口径与参考 pipeline 一致：vad_res[0]["value"] = [[start_ms, end_ms], ...]。
实际 VAD 推理由 asr 引擎完成；本模块只负责段数据结构与基础判定。
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Segment:
    start_ms: int
    end_ms: int

    @property
    def duration_ms(self) -> int:
        return self.end_ms - self.start_ms

    def overlaps(self, other: "Segment") -> bool:
        return self.start_ms < other.end_ms and other.start_ms < self.end_ms

    def overlap_ratio(self, other: "Segment") -> float:
        inter = max(0, min(self.end_ms, other.end_ms) - max(self.start_ms, other.start_ms))
        union = max(self.end_ms, other.end_ms) - min(self.start_ms, other.start_ms)
        return inter / union if union else 0.0


def from_value(value: list[list[int]]) -> list[Segment]:
    """把 [[start,end],...] 转为 Segment 列表。"""
    return [Segment(int(s), int(e)) for s, e in value if e > s]


def is_closed(seg: Segment, cursor_ms: int) -> bool:
    """只解码已闭合语音段：段尾不超过当前已接收音频游标。"""
    return seg.end_ms <= cursor_ms
