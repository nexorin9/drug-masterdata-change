"""目录表守门与歧义拒绝（T10）。

三层校验：结构校验（codes）→ 字典映射校验（目录快照）→ 业务校验（field_name 取值域）。
drug_code 与 field_name 由目录表硬匹配决定，模型不碰；通用名多命中拒绝歧义不猜。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from ..domain.codes import validate_drug_code
from ..domain.errors import AmbiguousDrugMatch, DrugNotFound, InvalidDrugCode
from ..domain.models import FIELD_NAME_VALUES, ChangeItem
from ..dictionary.matcher import MatchResult, match_generic_name
from ..dictionary.store import DrugEntry


@dataclass
class GuardResult:
    passed: bool
    item: ChangeItem
    candidates: list[DrugEntry] = field(default_factory=list)
    reason: str = ""
    layer: str = ""  # structure / dictionary / business / ok


def guard_item(
    item: ChangeItem,
    *,
    entries: list[DrugEntry],
    generic_ref: str = "",
) -> GuardResult:
    """对条目执行三层守门；不通过时标红、列候选、status 停 draft，不放行。"""
    # 第一层：结构校验（仅当已给出 drug_code）
    if item.drug_code:
        try:
            validate_drug_code(item.drug_code)
        except InvalidDrugCode as exc:
            item.error_class = exc.error_class
            return GuardResult(False, item, reason=str(exc), layer="structure")

    # 第二层：字典映射校验 + 歧义拒绝
    ref = generic_ref or item.generic_name or item.drug_code
    mr: MatchResult = match_generic_name(entries, ref)
    candidates = mr.entries
    if not item.drug_code:
        if mr.count > 1:
            item.candidate_codes = [e.drug_code for e in candidates]
            item.code_pending_manual = True
            item.error_class = "ambiguous_drug_match"
            return GuardResult(False, item, candidates, "通用名命中多条，药品码待人工指定", "dictionary")
        if mr.count == 1:
            item.drug_code = candidates[0].drug_code
            item.generic_name = candidates[0].generic_name
            item.cur_value = item.cur_value or candidates[0].spec
        else:
            item.error_class = "drug_not_found"
            return GuardResult(False, item, [], "目录表查不到该药品，不放行", "dictionary")
    else:
        if not any(e.drug_code == item.drug_code for e in entries):
            item.error_class = "drug_not_found"
            return GuardResult(False, item, [], "药品码不在目录快照中，不放行", "dictionary")

    # 第三层：业务校验（field_name 取值域）
    if item.field_name and item.field_name not in FIELD_NAME_VALUES:
        item.error_class = "guard_rejected"
        return GuardResult(False, item, candidates, f"字段名越界：{item.field_name}", "business")
    return GuardResult(True, item, candidates, "守门通过", "ok")
