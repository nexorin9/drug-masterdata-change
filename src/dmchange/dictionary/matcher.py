"""目录匹配器：按通用名/别名/剂型/规格检索，返回候选列表。

匹配优先级：精确 > 前缀 > 包含；多命中由守门层判歧义拒绝，不猜。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .store import DrugEntry


@dataclass
class MatchResult:
    entries: list[DrugEntry]
    rule: str  # exact / prefix / contains / none

    @property
    def count(self) -> int:
        return len(self.entries)


def _score(entry: DrugEntry, query: str) -> int:
    """列评分：精确=3，前缀=2，包含=1，无=0。"""
    q = query.strip().lower()
    fields = [entry.generic_name, entry.dosage_form, entry.spec, entry.manufacturer]
    best = 0
    for f in fields:
        fl = f.lower()
        if fl == q:
            best = max(best, 3)
        elif fl.startswith(q):
            best = max(best, 2)
        elif q and q in fl:
            best = max(best, 1)
    return best


def match(entries: Iterable[DrugEntry], query: str) -> MatchResult:
    q = query.strip()
    if not q:
        return MatchResult([], "none")
    scored = [(_score(e, q), e) for e in entries]
    scored = [(s, e) for s, e in scored if s > 0]
    if not scored:
        return MatchResult([], "none")
    top = max(s for s, _ in scored)
    chosen = [e for s, e in scored if s == top]
    rule = {3: "exact", 2: "prefix", 1: "contains"}[top]
    return MatchResult(chosen, rule)


def match_generic_name(entries: Iterable[DrugEntry], generic_name: str) -> MatchResult:
    """按通用名硬匹配：只用 generic_name 字段，避免误命中剂型/厂家。"""
    q = generic_name.strip().lower()
    exact = [e for e in entries if e.generic_name.strip().lower() == q]
    if exact:
        return MatchResult(exact, "exact")
    contains = [e for e in entries if q and q in e.generic_name.strip().lower()]
    return MatchResult(contains, "contains" if contains else "none")
