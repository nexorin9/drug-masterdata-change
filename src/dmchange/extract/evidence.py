"""要素与证据对齐引擎（T10/T22）。

模型只给句序号；本模块把它变成「能点的原话 + 绝对毫秒区间」，
处理越界索引、口水词、多要素共用一句、证据强度、区间校正。
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from ..domain.models import Evidence, Utterance

FILLER_WORDS = ("那个", "就是说", "对对对", "呃", "嗯", "这个这个", "然后呢")


@dataclass
class Alignment:
    evidence: Optional[Evidence]
    missing: bool = False
    corrected: bool = False
    warnings: list[str] = None  # type: ignore[assignment]

    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


def strip_filler(text: str) -> str:
    out = text
    for w in FILLER_WORDS:
        out = out.replace(w, "")
    return re.sub(r"\s+", " ", out).strip()


def assess_strength(text: str) -> str:
    """含否定词或数值的证据为 strong，否则 weak。"""
    if re.search(r"不是|应该是|说错|写成|改为|纠正", text) or re.search(r"\d", text):
        return "strong"
    return "weak"


def align_evidence(
    evidence_index: int,
    utterances: list[Utterance],
    *,
    model_start_ms: Optional[int] = None,
) -> Alignment:
    """evidence_index → 原话与毫秒区间；越界标「依据缺失」但要素仍保留。"""
    warnings: list[str] = []
    if evidence_index < 0 or evidence_index >= len(utterances):
        return Alignment(None, missing=True, warnings=["依据缺失：索引越界"])
    u = utterances[evidence_index]
    corrected = False
    start, end = u.start_ms, u.end_ms
    if model_start_ms is not None and model_start_ms != u.start_ms:
        corrected = True
        warnings.append("证据区间以解码毫秒为准，已校正")
    ev = Evidence(
        speaker=u.speaker,
        start_ms=start,
        end_ms=end,
        text=u.text,
        display_text=strip_filler(u.text),
        evidence_strength=assess_strength(u.text),
    )
    return Alignment(ev, corrected=corrected, warnings=warnings)


def dedup_for_export(evidence: list[Evidence]) -> list[Evidence]:
    """导出按句子去重（same speaker+start+end+text），但不丢要素行。"""
    seen = set()
    out = []
    for e in evidence:
        key = (e.speaker, e.start_ms, e.end_ms, e.text)
        if key in seen:
            continue
        seen.add(key)
        out.append(e)
    return out
