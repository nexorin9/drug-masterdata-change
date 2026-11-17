"""模型输出 JSON Schema（pydantic v2）：不信模型自述合规，本地强校验。"""
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field, ValidationError, field_validator

from ..domain.errors import SchemaInvalid
from ..domain.models import FIELD_NAME_VALUES

SYSTEM_PROMPT = (
    "你是药品目录核实要素抽取器。只输出 JSON 对象，不要任何解释文字。"
    "elements 数组每项含 drug_ref(通用名或俗称)、field_name、cur_value、proposed_value、evidence_index。"
    "field_name 只能是 name_code/category_code/dosage_form_code/spec_pack_code/enterprise_code 之一。"
    "roles 数组每项含 speaker、role(临床科室/供应商/药事岗)。"
    "否定式纠正如「不是0.25，是0.5」表示把现值 0.25 改为 0.5，proposed_value 取纠正后的值。"
)


class ElementModel(BaseModel):
    drug_ref: str = ""
    field_name: str
    cur_value: Optional[str] = None
    proposed_value: Optional[str] = None
    evidence_index: int = -1

    @field_validator("field_name")
    @classmethod
    def _check_field(cls, v: str) -> str:
        if v not in FIELD_NAME_VALUES:
            raise ValueError(f"field_name 越界：{v}")
        return v


class RoleModel(BaseModel):
    speaker: str
    role: str = "未判定"


class ExtractionModel(BaseModel):
    elements: list[ElementModel] = Field(default_factory=list)
    roles: list[RoleModel] = Field(default_factory=list)


def validate_extraction(data: Any, *, strict_field: bool = True) -> ExtractionModel:
    """本地 Schema 校验；越界 field_name 判 schema_invalid。"""
    try:
        if isinstance(data, str):
            import json
            data = json.loads(data)
        return ExtractionModel.model_validate(data)
    except (ValidationError, ValueError, TypeError) as exc:
        raise SchemaInvalid(f"结构化校验失败：{exc}") from exc
