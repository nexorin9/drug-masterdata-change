"""领域模型：状态枚举、字段取值域、ChangeItem / Evidence / Utterance / Turn。

这些结构是纯数据，不含任何 I/O 或业务推进逻辑；状态推进集中在 ledger/state_machine.py。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class Status(str, Enum):
    """条目状态生命周期（spec.md §4 / plan.md §4）。

    draft_incomplete → draft → pending_review → submitted → acked | rejected
    pending_review → returned → draft
    非法迁移一律由状态机拒绝并记审计。
    """

    DRAFT_INCOMPLETE = "draft_incomplete"
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    SUBMITTED = "submitted"
    ACKED = "acked"
    REJECTED = "rejected"
    RETURNED = "returned"

    def __str__(self) -> str:  # pragma: no cover - 便于日志
        return self.value


class FieldName(str, Enum):
    """可变更字段取值域，取药品编码六部分中的可变更字段（spec.md §2.3）。"""

    NAME_CODE = "name_code"
    CATEGORY_CODE = "category_code"
    DOSAGE_FORM_CODE = "dosage_form_code"
    SPEC_PACK_CODE = "spec_pack_code"
    ENTERPRISE_CODE = "enterprise_code"

    @classmethod
    def values(cls) -> tuple[str, ...]:
        return tuple(m.value for m in cls)


FIELD_NAME_VALUES = FieldName.values()
TERMINAL_STATUSES = (Status.ACKED, Status.REJECTED)
ERROR_CLASSES = (
    "timeout",
    "http_4xx",
    "http_5xx",
    "schema_invalid",
    "parse_error",
    # 识别侧（T19）
    "model_load_failed",
    "decode_timeout",
    "empty_result",
    "audio_decode_error",
    "vad_failed",
)


@dataclass
class Evidence:
    """一条要素的原话出处。

    speaker 是录音内匿名编号，仅作辅助列；业务判据是 text + start_ms/end_ms。
    """

    speaker: Optional[str]
    start_ms: int
    end_ms: int
    text: str
    display_text: str = ""
    evidence_strength: str = "weak"  # strong / weak
    role: Optional[str] = None  # 话轮角色（T24）
    turn_id: Optional[int] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "speaker": self.speaker,
            "start_ms": self.start_ms,
            "end_ms": self.end_ms,
            "text": self.text,
            "display_text": self.display_text or self.text,
            "evidence_strength": self.evidence_strength,
            "role": self.role,
            "turn_id": self.turn_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Evidence":
        return cls(
            speaker=data.get("speaker"),
            start_ms=int(data.get("start_ms", 0)),
            end_ms=int(data.get("end_ms", 0)),
            text=str(data.get("text", "")),
            display_text=str(data.get("display_text", "")),
            evidence_strength=str(data.get("evidence_strength", "weak")),
            role=data.get("role"),
            turn_id=data.get("turn_id"),
        )


@dataclass
class Utterance:
    """句级归一结果：一段已闭合语音对应的一行转写。

    start_ms / end_ms 为录音内绝对毫秒；speaker 为匿名编号，仅辅助列。
    """

    text: str
    start_ms: int
    end_ms: int
    speaker: Optional[str] = None
    speaker_resolved: bool = True
    punct_source: str = "model"  # model / heuristic / none
    index: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "start_ms": self.start_ms,
            "end_ms": self.end_ms,
            "speaker": self.speaker,
            "speaker_resolved": self.speaker_resolved,
            "punct_source": self.punct_source,
            "index": self.index,
        }


@dataclass
class Turn:
    """话轮：连续同说话人的句子聚合（T24）。"""

    speaker: Optional[str]
    start_ms: int
    end_ms: int
    utterances: list[Utterance] = field(default_factory=list)
    role: str = "未判定"
    role_clue: str = ""


@dataclass
class ChangeItem:
    """变更条目草稿。所有金额/规格口径同时保留原文与归一值，界面与导出只显示原文。"""

    drug_code: str = ""
    field_name: str = ""
    cur_value: str = ""
    proposed_value: str = ""
    evidence: list[Evidence] = field(default_factory=list)
    evidence_source: str = "voice"
    submitted_by: str = ""
    reviewed_by: str = ""
    status: Status = Status.DRAFT
    change_id: str = ""
    error_class: Optional[str] = None
    generic_name: str = ""
    # 原文 / 归一值并存（口径不静默换算）
    cur_value_normalized: str = ""
    proposed_value_normalized: str = ""
    # 目录守门产物
    candidate_codes: list[str] = field(default_factory=list)
    code_pending_manual: bool = False
    review_comment: str = ""
    reject_reason: str = ""
    receipt_no: str = ""
    receipt_at: str = ""
    created_at: str = ""
    updated_at: str = ""
    demo: bool = False
    extra: dict[str, Any] = field(default_factory=dict)

    def to_payload_dict(self) -> dict[str, Any]:
        """生成符合 spec.md §2.3 的出站请求体（只传原文，不传归一值）。"""
        return {
            "change_id": self.change_id,
            "drug_code": self.drug_code,
            "field_name": self.field_name,
            "cur_value": self.cur_value,
            "proposed_value": self.proposed_value,
            "evidence": [e.to_dict() for e in self.evidence],
            "evidence_source": self.evidence_source,
            "submitted_by": self.submitted_by,
            "reviewed_by": self.reviewed_by,
            "status": self.status.value if isinstance(self.status, Status) else str(self.status),
        }
