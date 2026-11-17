"""运行摘要与结构化日志（T36）：八阶段耗时、错误码、凭据脱敏。"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from .config import Config

STAGES = (
    "capture", "unify", "vad", "decode", "extract",
    "guard", "ledger", "outbound",
)


@dataclass
class StageTiming:
    stage: str
    duration_ms: int
    error_class: Optional[str] = None


@dataclass
class RunSummary:
    input_source: str = ""
    segment_count: int = 0
    item_count: int = 0
    total_ms: int = 0
    failed_stage: str = ""
    stages: list[StageTiming] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "input_source": self.input_source,
            "segment_count": self.segment_count,
            "item_count": self.item_count,
            "total_ms": self.total_ms,
            "failed_stage": self.failed_stage,
            "stages": [{"stage": s.stage, "duration_ms": s.duration_ms,
                        "error_class": s.error_class} for s in self.stages],
        }


def mask(text: str, cfg: Optional[Config] = None) -> str:
    """凭据掩码：Bearer token / api key / 本地音频路径。"""
    secrets = []
    if cfg is not None:
        secrets = [cfg.mdm_token, cfg.model_api_key, cfg.asr_api_key]
    for s in secrets:
        if s and len(s) >= 4:
            text = text.replace(s, "***")
    import re
    text = re.sub(r"Bearer\s+\S+", "Bearer ***", text)
    text = re.sub(r"(/[^\s]*\.(?:wav|mp3|m4a|pcm))", "<audio-path>", text)
    return text


class StageTimer:
    """八阶段计时器：with 用法，退出时记录耗时。"""

    def __init__(self, summary: RunSummary, stage: str):
        self.summary = summary
        self.stage = stage
        self.t0 = 0.0

    def __enter__(self):
        self.t0 = time.time()
        return self

    def __exit__(self, exc_type, exc, tb):
        dur = int((time.time() - self.t0) * 1000)
        ec = getattr(exc, "error_class", None) if exc else None
        self.summary.stages.append(StageTiming(self.stage, dur, ec))
        if exc and not self.summary.failed_stage:
            self.summary.failed_stage = self.stage
        return False


def json_line(event: str, *, stage: str = "", level: str = "INFO",
              duration_ms: int = 0, error_class: Optional[str] = None,
              drug_code: str = "", change_id: str = "") -> str:
    """结构化日志行（JSON Lines）。"""
    return json.dumps({
        "event": event, "stage": stage, "level": level,
        "duration_ms": duration_ms, "error_class": error_class,
        "drug_code": drug_code, "change_id": change_id,
    }, ensure_ascii=False)
