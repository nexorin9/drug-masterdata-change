"""幂等键口径：change_id = sha256(drug_code | field_name | cur_value | proposed_value | evidence_sha256)。

为何不含时间戳与重试次数：同一核实重复触发（手抖双击、outbox 重放、脚本重跑）
必须产出同一个键，SQLite UNIQUE 约束才能兜底，不产生第二条条目、不重复写主数据。
"""
from __future__ import annotations

import hashlib
from typing import Iterable

from ..domain.models import Evidence

_SEP = "|"


def evidence_sha256(evidence: Iterable[Evidence]) -> str:
    """证据哈希口径：按 speaker/start_ms/end_ms/text 排序后拼接再哈希，
    保证证据顺序不影响幂等键。"""
    items = []
    for e in evidence:
        items.append(_SEP.join([
            e.speaker or "", str(e.start_ms), str(e.end_ms), e.text,
        ]))
    canonical = _SEP.join(sorted(items))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def compute_change_id(
    drug_code: str,
    field_name: str,
    cur_value: str,
    proposed_value: str,
    evidence: Iterable[Evidence],
) -> str:
    """计算幂等键。同一核实（含证据乱序）产出稳定不变的 sha256。"""
    ev_hash = evidence_sha256(evidence)
    raw = _SEP.join([
        drug_code or "", field_name or "", cur_value or "", proposed_value or "", ev_hash,
    ])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
