"""回执回读与状态刷新（T29）：终态不变、字段缺失记 warning、并发上限、轮询停止。"""
from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from ..domain.models import Status


@dataclass
class ReceiptView:
    change_id: str
    status: str = "unknown"
    receipt_no: str = ""
    receipt_at: str = ""
    reject_reason: str = ""
    warnings: list[str] = field(default_factory=list)

    @property
    def terminal(self) -> bool:
        return self.status in ("acked", "rejected")


def parse_receipt(change_id: str, body: dict[str, Any]) -> ReceiptView:
    """字段缺失按未知处理并记 warning，不抛错阻断界面。"""
    view = ReceiptView(change_id)
    status = body.get("status")
    if status in ("acked", "rejected", "submitted"):
        view.status = status
    else:
        view.warnings.append(f"回执 status 未知：{status!r}")
    view.receipt_no = str(body.get("receipt_no") or "")
    view.receipt_at = str(body.get("receipt_at") or "")
    view.reject_reason = str(body.get("reject_reason") or "")
    if view.status == "acked" and not view.receipt_no:
        view.warnings.append("acked 回执缺 receipt_no")
    if view.status == "rejected" and not view.reject_reason:
        view.warnings.append("rejected 回执缺 reject_reason")
    return view


def refresh_many(
    change_ids: list[str],
    fetch: Callable[[str], dict[str, Any]],
    *,
    max_workers: int = 4,
) -> list[ReceiptView]:
    """批量刷新并发上限 4，避免压垮主数据系统。"""
    workers = min(4, max(1, max_workers))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(fetch, cid): cid for cid in change_ids}
        results = []
        for fut, cid in futures.items():
            try:
                results.append(parse_receipt(cid, fut.result()))
            except Exception as exc:  # noqa: BLE001
                rv = ReceiptView(cid)
                rv.warnings.append(f"回读失败：{exc}")
                results.append(rv)
        return results


def should_continue_polling(views: list[ReceiptView], *, elapsed_ms: int,
                            timeout_ms: int) -> bool:
    """轮询停止条件：全部终态或超时即停，不无限重试。"""
    if elapsed_ms >= timeout_ms:
        return False
    return any(not v.terminal for v in views)


def is_terminal_status(status: Status | str) -> bool:
    s = status.value if isinstance(status, Status) else str(status)
    return s in ("acked", "rejected")
