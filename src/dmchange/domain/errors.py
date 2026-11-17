"""异常层级：每类失败都携带稳定 error_class 与可读中文说明。

error_class 取值见 models.ERROR_CLASSES。业务层只按 error_class 决策，
不解析异常文本；文本用于界面与审计。
"""
from __future__ import annotations

from typing import Optional


class DMChangeError(Exception):
    """所有领域异常的基类。"""

    error_class = "internal_error"

    def __init__(self, message: str = "", *, error_class: Optional[str] = None,
                 detail: Optional[dict] = None):
        super().__init__(message)
        self.message = message
        if error_class is not None:
            self.error_class = error_class
        self.detail = detail or {}

    def __str__(self) -> str:
        return f"[{self.error_class}] {self.message}"


# ---------- 状态机 / 台账 ----------
class IllegalTransition(DMChangeError):
    error_class = "illegal_transition"


class ReviewerMismatch(DMChangeError):
    """复核人 == 经办人，或未复核直接提交。"""

    error_class = "reviewer_mismatch"


class DuplicateSubmit(DMChangeError):
    error_class = "duplicated_submit"


# ---------- 目录守门 ----------
class AmbiguousDrugMatch(DMChangeError):
    """通用名命中多条目录记录：拒绝歧义，不猜。"""

    error_class = "ambiguous_drug_match"

    def __init__(self, message: str = "", *, candidates: Optional[list] = None, **kw):
        super().__init__(message, **kw)
        self.candidates = candidates or []


class DrugNotFound(DMChangeError):
    error_class = "drug_not_found"


class InvalidDrugCode(DMChangeError):
    """drug_code 结构校验失败，报错含具体位号与期望字符集。"""

    error_class = "invalid_drug_code"

    def __init__(self, message: str = "", *, segment: str = "", position: str = "",
                 expected: str = "", **kw):
        super().__init__(message, **kw)
        self.segment = segment
        self.position = position
        self.expected = expected
        self.detail = {"segment": segment, "position": position, "expected": expected}


class GuardRejected(DMChangeError):
    error_class = "guard_rejected"


# ---------- 模型网关 / 抽取 ----------
class ModelUnavailable(DMChangeError):
    """模型不可达族：timeout / http_4xx / http_5xx / parse_error。"""

    error_class = "model_unavailable"

    def __init__(self, message: str = "", *, error_class: str = "model_unavailable", **kw):
        super().__init__(message, error_class=error_class, **kw)


class TimeoutError_(ModelUnavailable):
    error_class = "timeout"

    def __init__(self, message: str = "", **kw):
        super().__init__(message, error_class="timeout", **kw)


class Http4xx(ModelUnavailable):
    error_class = "http_4xx"

    def __init__(self, message: str = "", **kw):
        super().__init__(message, error_class="http_4xx", **kw)


class Http5xx(ModelUnavailable):
    error_class = "http_5xx"

    def __init__(self, message: str = "", **kw):
        super().__init__(message, error_class="http_5xx", **kw)


class ParseError(ModelUnavailable):
    error_class = "parse_error"

    def __init__(self, message: str = "", **kw):
        super().__init__(message, error_class="parse_error", **kw)


class SchemaInvalid(DMChangeError):
    error_class = "schema_invalid"


# ---------- 识别侧（T19） ----------
class ModelLoadFailed(DMChangeError):
    error_class = "model_load_failed"


class DecodeTimeout(DMChangeError):
    error_class = "decode_timeout"


class EmptyResult(DMChangeError):
    error_class = "empty_result"


class AudioDecodeError(DMChangeError):
    error_class = "audio_decode_error"


class VadFailed(DMChangeError):
    error_class = "vad_failed"


# ---------- 出站 ----------
class OutboxError(DMChangeError):
    error_class = "outbox_error"


class ReceiptError(DMChangeError):
    error_class = "receipt_error"
