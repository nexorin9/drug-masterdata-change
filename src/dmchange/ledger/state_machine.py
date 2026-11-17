"""业务状态机：合法迁移表 + 非法迁移拒绝。

状态生命周期（spec.md §4）：
  draft_incomplete → draft → pending_review → submitted → acked | rejected
  pending_review → returned → draft
模型输出永不推进状态；每次推进由显式业务动作触发。
"""
from __future__ import annotations

from typing import Callable, Optional

from ..domain.errors import IllegalTransition, ReviewerMismatch
from ..domain.models import Status

# 合法迁移表：from -> {to}
TRANSITIONS: dict[Status, set[Status]] = {
    Status.DRAFT_INCOMPLETE: {Status.DRAFT},
    Status.DRAFT: {Status.PENDING_REVIEW},
    Status.PENDING_REVIEW: {Status.SUBMITTED, Status.RETURNED},
    Status.RETURNED: {Status.DRAFT},
    Status.SUBMITTED: {Status.ACKED, Status.REJECTED},
    Status.ACKED: set(),
    Status.REJECTED: set(),
}

ACTION_LABEL = {
    "confirm": "药事岗确认",
    "submit_review": "送复核",
    "review_pass": "复核通过并出站",
    "return": "退回修改",
    "resubmit": "修改后重提",
    "ack": "回执确认",
    "reject": "回执驳回",
}


def _coerce(status: Status | str) -> Status:
    return status if isinstance(status, Status) else Status(str(status))


def can_transition(src: Status | str, dst: Status | str) -> bool:
    return _coerce(dst) in TRANSITIONS.get(_coerce(src), set())


def legal_transitions(src: Status | str) -> set[Status]:
    return set(TRANSITIONS.get(_coerce(src), set()))


def assert_transition(
    src: Status | str,
    dst: Status | str,
    *,
    action: str = "",
    on_illegal: Optional[Callable[[str, str, str], None]] = None,
) -> Status:
    """校验迁移合法；非法时抛 IllegalTransition，并可选触发审计回调。

    on_illegal(from, to, note) 供仓储层记录被拒审计（不静默）。
    """
    s, d = _coerce(src), _coerce(dst)
    if d not in TRANSITIONS.get(s, set()):
        note = f"非法迁移 {s.value} → {d.value}" + (f"（动作 {action}）" if action else "")
        if on_illegal is not None:
            on_illegal(s.value, d.value, note)
        raise IllegalTransition(note)
    return d


def assert_reviewer_not_submitter(
    submitted_by: str,
    reviewed_by: str,
    *,
    on_illegal: Optional[Callable[[str, str, str], None]] = None,
) -> None:
    """复核人 ≠ 经办人强校验；未复核直接提交同样拒绝。"""
    if not reviewed_by or not submitted_by:
        note = "未复核或缺少经办人：不得提交出站"
        if on_illegal is not None:
            on_illegal(submitted_by, reviewed_by, note)
        raise ReviewerMismatch(note)
    if reviewed_by == submitted_by:
        note = f"复核人不能与经办人相同（均为 {reviewed_by}）"
        if on_illegal is not None:
            on_illegal(submitted_by, reviewed_by, note)
        raise ReviewerMismatch(note)


def assert_return_comment(comment: str) -> None:
    """退回必须带非空复核意见，否则拒绝迁移。"""
    if not comment or not comment.strip():
        raise IllegalTransition("退回必须填写复核意见，不得为空")
