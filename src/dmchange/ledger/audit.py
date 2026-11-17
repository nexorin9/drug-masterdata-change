"""只增不改审计链：仅 append 与 select，物理层不提供 update / delete 代码路径。

审计动作（T27 补全）：
  item_created / manual_fill / confirmed / reviewed / submitted / acked /
  rejected / returned / duplicated_submit / illegal_transition / asset_rule_updated
"""
from __future__ import annotations

import csv
import io
import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable, Optional

from ..domain.models import Evidence

AUDIT_ACTIONS = (
    "item_created",
    "manual_fill",
    "confirmed",
    "reviewed",
    "submitted",
    "acked",
    "rejected",
    "returned",
    "duplicated_submit",
    "illegal_transition",
    "asset_rule_updated",
)


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


@dataclass
class AuditEvent:
    actor: str
    action: str
    drug_code: str = ""
    field_name: str = ""
    cur_value: str = ""
    proposed_value: str = ""
    evidence: list[Evidence] | None = None
    detail: dict[str, Any] | None = None
    at: str = ""

    def to_row(self) -> tuple:
        return (
            self.actor,
            self.action,
            self.drug_code,
            self.field_name,
            self.cur_value,
            self.proposed_value,
            json.dumps([e.to_dict() for e in (self.evidence or [])], ensure_ascii=False),
            json.dumps(self.detail or {}, ensure_ascii=False, default=str),
            self.at or now_iso(),
        )


def append(conn: sqlite3.Connection, event: AuditEvent) -> int:
    """只增：写入一条审计事件，返回自增 id。"""
    cur = conn.execute(
        "INSERT INTO audit_log "
        "(actor, action, drug_code, field_name, cur_value, proposed_value, evidence_json, detail_json, at) "
        "VALUES (?,?,?,?,?,?,?,?,?)",
        event.to_row(),
    )
    conn.commit()
    return int(cur.lastrowid)


def select(
    conn: sqlite3.Connection,
    *,
    drug_code: Optional[str] = None,
    action: Optional[str] = None,
    limit: int = 1000,
) -> list[dict[str, Any]]:
    """只读查询审计链。"""
    sql = "SELECT * FROM audit_log WHERE 1=1"
    args: list[Any] = []
    if drug_code is not None:
        sql += " AND drug_code=?"
        args.append(drug_code)
    if action is not None:
        sql += " AND action=?"
        args.append(action)
    sql += " ORDER BY id ASC LIMIT ?"
    args.append(limit)
    return [dict(r) for r in conn.execute(sql, args).fetchall()]


def has_write_path() -> bool:
    """源码级自检辅助：本模块源码中不存在 update/delete 语句。"""
    import inspect

    src = inspect.getsource(append) + inspect.getsource(select) + inspect.getsource(export_csv)
    low = src.lower()
    return "delete from" in low or "update audit_log" in low


# ---------- 导出 ----------

CSV_HEADERS = (
    "序号", "药品码", "字段名", "现值", "应为值", "依据原话", "说话人编号",
    "起始毫秒", "结束毫秒", "经办人", "复核人", "状态", "回执号",
)


def _mask_secrets(text: str, secrets: Iterable[str] = ()) -> str:
    for s in secrets:
        if s and len(s) >= 4:
            text = text.replace(s, "***")
    return text


def export_csv(items: list[dict[str, Any]], *, secrets: Iterable[str] = (),
               demo: bool = False) -> str:
    """药事会材料 CSV：UTF-8 with BOM，含依据原话与起止毫秒。"""
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(CSV_HEADERS)
    for i, item in enumerate(items, 1):
        evidence = item.get("evidence") or []
        if not evidence:
            evidence = [{"text": "", "speaker": "", "start_ms": "", "end_ms": ""}]
        for ev in evidence:
            row = [
                i,
                item.get("drug_code", ""),
                item.get("field_name", ""),
                item.get("cur_value", ""),
                item.get("proposed_value", ""),
                _mask_secrets(str(ev.get("text", "")), secrets),
                ev.get("speaker") or "",
                ev.get("start_ms", ""),
                ev.get("end_ms", ""),
                item.get("submitted_by", ""),
                item.get("reviewed_by", ""),
                item.get("status", ""),
                item.get("receipt_no", ""),
            ]
            if demo:
                row[0] = f"演示数据-{i}"
            w.writerow(row)
    return "\ufeff" + buf.getvalue()


def export_markdown(items: list[dict[str, Any]], *, secrets: Iterable[str] = (),
                    demo: bool = False) -> str:
    """会议用摘要版 Markdown：按药品码分组，附依据原话与毫秒。"""
    lines: list[str] = ["# 药事会目录变更复核材料", ""]
    if demo:
        lines += ["> 演示数据", ""]
    groups: dict[str, list[dict[str, Any]]] = {}
    for it in items:
        groups.setdefault(it.get("drug_code", ""), []).append(it)
    label = {"draft": "待复核", "pending_review": "待复核", "submitted": "已提交",
             "rejected": "已驳回", "acked": "已确认", "returned": "已退回",
             "draft_incomplete": "要素缺失"}
    for code, group in groups.items():
        lines.append(f"## {code}")
        lines.append("")
        for it in group:
            status = it.get("status", "")
            lines.append(
                f"- **{it.get('field_name', '')}** [{label.get(status, status)}] "
                f"现值：{it.get('cur_value', '')} → 应为：{it.get('proposed_value', '')}"
            )
            for ev in (it.get("evidence") or []):
                lines.append(
                    f"  - {ev.get('speaker') or '未分离'} "
                    f"{ev.get('start_ms', '')}–{ev.get('end_ms', '')}ms："
                    f"{_mask_secrets(str(ev.get('text', '')), secrets)}"
                )
            if it.get("reject_reason"):
                lines.append(f"  - 驳回原因：{it['reject_reason']}")
        lines.append("")
    return "\n".join(lines)
