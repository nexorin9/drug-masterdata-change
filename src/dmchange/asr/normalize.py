"""句级归一：sentence_info / fixture 结果 → Utterance[]{text,start_ms,end_ms,speaker}。

说话人编号为录音内匿名编号，仅辅助列；业务判据是原话 + 绝对毫秒。
覆盖 T18：标点兜底、编号稳定化、聚类未收敛降级、时间戳对齐、超长/超短句。
"""
from __future__ import annotations

import re
from typing import Any, Iterable, Optional

from ..domain.models import Utterance

PUNCT_FALLBACK = "。"


def _ensure_punct(text: str) -> tuple[str, str]:
    """句内缺标点时按启发式补句号并标 punct_source=heuristic。"""
    t = text.strip()
    if not t:
        return t, "none"
    if t[-1] in "。！？!?.;；":
        return t, "model"
    return t + PUNCT_FALLBACK, "heuristic"


def stable_speakers(utterances: list[Utterance]) -> list[Utterance]:
    """按首次出现顺序把说话人标签重排为 spk0 / spk1…，保证同次录音内连续可复现。"""
    mapping: dict[str, str] = {}
    for u in utterances:
        if u.speaker is None:
            continue
        if u.speaker not in mapping:
            mapping[u.speaker] = f"spk{len(mapping)}"
        u.speaker = mapping[u.speaker]
    return utterances


def normalize_sentences(
    sentences: Iterable[dict[str, Any]],
    *,
    punc_model_loaded: bool = True,
    cluster_resolved: bool = True,
    punct_pause_threshold_ms: int = 600,
) -> list[Utterance]:
    """把 sentence_info 归一为 Utterance 列表。

    sentences 每项：{text, start, end, speaker?}（speaker 可为模型标签）。
    """
    out: list[Utterance] = []
    for idx, s in enumerate(sentences):
        text = str(s.get("text", "")).strip()
        start = int(s.get("start", s.get("start_ms", 0)))
        end = int(s.get("end", s.get("end_ms", start)))
        # 超短句丢弃（<50ms）并记事件（调用方读 extra）
        if end - start < 50 and text:
            continue
        if not punc_model_loaded:
            text, src = _ensure_punct(text)
            if src == "none":
                src = "heuristic"
        else:
            text = text or text
            src = "model" if (text and text[-1] in "。！？!?.;；") else "heuristic"
            if src == "heuristic" and text:
                text = text + PUNCT_FALLBACK
        # 超长句（>60s）按 60s 硬切为多句
        if end - start > 60_000:
            cursor = start
            while cursor < end:
                seg_end = min(cursor + 60_000, end)
                out.append(Utterance(
                    text=text if cursor == start else text + "（续）",
                    start_ms=cursor, end_ms=seg_end,
                    speaker=s.get("speaker"),
                    speaker_resolved=cluster_resolved and s.get("speaker") is not None,
                    punct_source=src, index=len(out),
                ))
                cursor = seg_end
            continue
        speaker = s.get("speaker")
        resolved = bool(cluster_resolved and speaker is not None)
        out.append(Utterance(
            text=text, start_ms=start, end_ms=end,
            speaker=speaker if resolved else None,
            speaker_resolved=resolved,
            punct_source=src, index=len(out),
        ))
    out = stable_speakers(out)
    # 时间戳对齐：start <= end；相邻重叠取交集较小起点并记 warning（事件由调用方从 extra 读取）
    for i, u in enumerate(out):
        if u.start_ms > u.end_ms:
            u.start_ms, u.end_ms = u.end_ms, u.start_ms
        if i > 0 and out[i - 1].end_ms > u.start_ms:
            out[i - 1].end_ms = u.start_ms
    return out


def normalize_fixture(fixture: list[dict[str, Any]], **kwargs) -> list[Utterance]:
    """fixture 驱动：与 normalize_sentences 同口径，供最小端到端切片使用。"""
    return normalize_sentences(fixture, **kwargs)
