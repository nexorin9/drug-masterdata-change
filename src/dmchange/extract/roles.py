"""角色判定与话轮归属（T24）。

说话人编号只是辅助列；用话轮语义判角色，判不出就明说未判定，不硬猜。
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, Optional

from ..domain.models import Turn, Utterance

IDENTITY_CUES = {
    "临床科室": ("我们科室", "临床", "病区", "大夫", "医生", "主任"),
    "供应商": ("我们公司", "供货", "厂家这边", "供应商", "报价"),
    "药事岗": ("药事会", "目录", "我们药学部", "变更单", "主数据"),
}


def aggregate_turns(utterances: Iterable[Utterance]) -> list[Turn]:
    """连续同说话人的句子合并为话轮。"""
    turns: list[Turn] = []
    for u in utterances:
        if turns and turns[-1].speaker == u.speaker:
            t = turns[-1]
            t.end_ms = max(t.end_ms, u.end_ms)
            t.utterances.append(u)
        else:
            turns.append(Turn(u.speaker, u.start_ms, u.end_ms, [u]))
    return turns


def infer_role(turn: Turn) -> tuple[str, str]:
    """规则侧给候选角色与线索句；线索不足返回（未判定, ''）。"""
    text = "".join(u.text for u in turn.utterances)
    scores = {role: 0 for role in IDENTITY_CUES}
    clue = ""
    for role, cues in IDENTITY_CUES.items():
        for c in cues:
            if c in text:
                scores[role] += 1
                clue = c
    best = max(scores, key=lambda k: scores[k])
    if scores[best] == 0:
        return "未判定", ""
    # 双方都自称药事岗 / 平局 → 未判定
    top = [r for r, v in scores.items() if v == scores[best]]
    if len(top) > 1:
        return "未判定", ""
    return best, clue


def assign_roles(utterances: Iterable[Utterance]) -> list[Turn]:
    turns = aggregate_turns(utterances)
    for t in turns:
        role, clue = infer_role(t)
        t.role, t.role_clue = role, clue
    return turns


def attach_roles_to_evidence(evidence_list, turns: list[Turn]):
    """把要素所在话轮的角色写入证据元数据。"""
    for ev in evidence_list:
        role = "未判定"
        for t in turns:
            if t.start_ms <= ev.start_ms <= t.end_ms:
                role = t.role
                break
        if hasattr(ev, "role"):
            ev.role = role
    return evidence_list
