"""要素抽取编排（T9/T15/T23）。

模型负责方向判定 / 依据句选择 / 跨句指代；数值实体由规则做。
模型不可达或 Schema 校验失败 → 确定性降级：转写文本 + 出处毫秒 + 空要素，
status=draft_incomplete，不出站、不推进任何状态。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from ..domain.errors import DMChangeError, ModelUnavailable
from ..domain.models import ChangeItem, Evidence, Status, Utterance
from . import evidence as evidence_mod
from . import parser as parser_mod
from . import roles as roles_mod
from .gateway import GatewayResponse, ModelGateway
from .schema import validate_extraction


@dataclass
class ExtractionResult:
    item: ChangeItem
    degraded: bool = False
    error_class: Optional[str] = None
    warnings: list[str] = field(default_factory=list)
    roles: list[Any] = field(default_factory=list)


def build_user_prompt(utterances: list[Utterance]) -> str:
    lines = []
    for i, u in enumerate(utterances):
        spk = u.speaker or "未分离"
        lines.append(f"[{i}] ({spk} {u.start_ms}-{u.end_ms}ms) {u.text}")
    return "药品核实通话转写（方括号内为 evidence_index）：\n" + "\n".join(lines)


def extract(
    gateway: ModelGateway,
    utterances: list[Utterance],
    *,
    fallback_text: str = "",
) -> ExtractionResult:
    """调用模型抽取要素；失败则确定性降级为 draft_incomplete。"""
    prompt = build_user_prompt(utterances)
    try:
        resp = gateway.call(prompt, validate=True)
    except DMChangeError as exc:
        return _degrade(utterances, exc.error_class, str(exc))

    try:
        model_data = validate_extraction(resp.raw).model_dump()
    except DMChangeError as exc:
        return _degrade(utterances, exc.error_class, str(exc))

    warnings: list[str] = []
    evidence_list: list[Evidence] = []
    elements: list[ChangeItem] = []
    for el in model_data.get("elements", []):
        idx = int(el.get("evidence_index", -1))
        aln = evidence_mod.align_evidence(idx, utterances)
        warnings.extend(aln.warnings)
        ev = aln.evidence
        if ev:
            evidence_list.append(ev)
        cur = el.get("cur_value") or ""
        prop = el.get("proposed_value") or ""
        # 方向解析：模型给的方向若含否定句式，用规则再校正一次（数值由规则定）
        text_for_dir = ev.text if ev else ""
        corr = parser_mod.parse_correction(text_for_dir)
        if corr and corr.corrected:
            if not prop:
                prop = corr.corrected
            if not cur and corr.negated:
                cur = corr.negated
        spec = parser_mod.parse_spec(prop or text_for_dir)
        elements.append(ChangeItem(
            drug_code="",  # 由守门层按目录表决定，模型不碰
            field_name=el.get("field_name", ""),
            cur_value=cur,
            proposed_value=prop,
            cur_value_normalized=(
                f"{spec.content_value}{spec.content_unit}" if spec.content_value else ""
            ),
            proposed_value_normalized=(
                f"{spec.content_value}{spec.content_unit}" if spec.content_value else ""
            ),
            evidence=[ev] if ev else [],
            evidence_source="voice",
        ))

    # 角色判定
    turns = roles_mod.assign_roles(utterances)
    roles_out = [{"speaker": t.speaker, "role": t.role, "clue": t.role_clue} for t in turns]
    roles_mod.attach_roles_to_evidence(evidence_list, turns)

    primary = elements[0] if elements else ChangeItem()
    if elements:
        primary.evidence = evidence_mod.dedup_for_export(evidence_list)
    primary.status = Status.DRAFT
    return ExtractionResult(primary, False, None, warnings, roles_out)


def _degrade(utterances: list[Utterance], error_class: Optional[str], reason: str) -> ExtractionResult:
    """确定性降级草稿：只留转写文本 + 出处毫秒 + 空要素。"""
    evs = [
        Evidence(u.speaker, u.start_ms, u.end_ms, u.text,
                 evidence_strength="weak")
        for u in utterances
    ]
    item = ChangeItem(
        status=Status.DRAFT_INCOMPLETE,
        evidence=evs,
        error_class=error_class or "parse_error",
        extra={"degrade_reason": reason, "transcript": "\n".join(u.text for u in utterances)},
    )
    return ExtractionResult(item, True, error_class, [reason], [])
