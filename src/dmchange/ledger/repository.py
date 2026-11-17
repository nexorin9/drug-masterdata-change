"""条目仓储：CRUD + 状态推进入口 + 幂等 + 查询过滤。

所有状态推进都先过 state_machine；change_id 唯一约束冲突返回既有条目不新建。
"""
from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from ..domain.errors import DuplicateSubmit, GuardRejected, ReviewerMismatch
from ..domain.models import ChangeItem, Evidence, Status
from . import audit as audit_mod
from .identity import compute_change_id
from .state_machine import (
    assert_reviewer_not_submitter,
    assert_return_comment,
    assert_transition,
    can_transition,
)


def _now() -> str:
    return audit_mod.now_iso()


def _item_from_row(row: sqlite3.Row) -> ChangeItem:
    d = dict(row)
    return ChangeItem(
        change_id=d["change_id"],
        drug_code=d["drug_code"],
        field_name=d["field_name"],
        cur_value=d["cur_value"],
        proposed_value=d["proposed_value"],
        cur_value_normalized=d.get("cur_value_normalized", ""),
        proposed_value_normalized=d.get("proposed_value_normalized", ""),
        evidence=[Evidence.from_dict(x) for x in json.loads(d.get("evidence_json") or "[]")],
        evidence_source=d.get("evidence_source", "voice"),
        submitted_by=d.get("submitted_by", ""),
        reviewed_by=d.get("reviewed_by", ""),
        status=Status(d["status"]),
        error_class=d.get("error_class"),
        generic_name=d.get("generic_name", ""),
        candidate_codes=json.loads(d.get("candidate_codes_json") or "[]"),
        code_pending_manual=bool(d.get("code_pending_manual", 0)),
        review_comment=d.get("review_comment", ""),
        reject_reason=d.get("reject_reason", ""),
        receipt_no=d.get("receipt_no", ""),
        receipt_at=d.get("receipt_at", ""),
        demo=bool(d.get("demo", 0)),
        extra=json.loads(d.get("extra_json") or "{}"),
        created_at=d.get("created_at", ""),
        updated_at=d.get("updated_at", ""),
    )


class Repository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        # 并发提交串行化：同进程内同一连接上的写操作串行，配合唯一约束保证幂等
        self._write_lock = threading.RLock()

    # ---------- 创建 ----------
    def create(self, item: ChangeItem, *, actor: str = "system") -> ChangeItem:
        """落草稿。change_id 不存在则计算；唯一冲突返回既有条目并记 duplicated_submit。"""
        if not item.change_id:
            item.change_id = compute_change_id(
                item.drug_code, item.field_name, item.cur_value,
                item.proposed_value, item.evidence,
            )
        # 经办人缺省取创建者；状态统一 coerce 为枚举
        if not item.submitted_by:
            item.submitted_by = actor
        if not isinstance(item.status, Status):
            item.status = Status(str(item.status))
        now = _now()
        item.created_at = item.created_at or now
        item.updated_at = now
        with self._write_lock:
            try:
                self.conn.execute(
                    "INSERT INTO items (change_id, drug_code, field_name, cur_value, proposed_value, "
                    "cur_value_normalized, proposed_value_normalized, evidence_json, evidence_source, "
                    "submitted_by, reviewed_by, status, error_class, generic_name, candidate_codes_json, "
                    "code_pending_manual, review_comment, reject_reason, receipt_no, receipt_at, demo, "
                    "extra_json, created_at, updated_at) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        item.change_id, item.drug_code, item.field_name, item.cur_value,
                        item.proposed_value, item.cur_value_normalized, item.proposed_value_normalized,
                        json.dumps([e.to_dict() for e in item.evidence], ensure_ascii=False),
                        item.evidence_source, item.submitted_by, item.reviewed_by,
                        item.status.value if isinstance(item.status, Status) else item.status,
                        item.error_class, item.generic_name,
                        json.dumps(item.candidate_codes, ensure_ascii=False),
                        int(item.code_pending_manual), item.review_comment, item.reject_reason,
                        item.receipt_no, item.receipt_at, int(item.demo),
                        json.dumps(item.extra, ensure_ascii=False, default=str),
                        item.created_at, item.updated_at,
                    ),
                )
                self.conn.commit()
            except sqlite3.IntegrityError:
                self.conn.rollback()
                audit_mod.append(self.conn, audit_mod.AuditEvent(
                    actor=actor, action="duplicated_submit", drug_code=item.drug_code,
                    field_name=item.field_name, detail={"change_id": item.change_id},
                ))
                existing = self.get_by_change_id(item.change_id)
                if existing is None:
                    raise DuplicateSubmit("唯一冲突但未找到既有条目")
                return existing
            audit_mod.append(self.conn, audit_mod.AuditEvent(
                actor=actor, action="item_created", drug_code=item.drug_code,
                field_name=item.field_name, cur_value=item.cur_value,
                proposed_value=item.proposed_value, evidence=item.evidence,
                detail={"change_id": item.change_id, "status": item.status.value},
            ))
            return item

    def create_or_get(self, item: ChangeItem, *, actor: str = "system") -> ChangeItem:
        """幂等入口：同 change_id 返回既有条目（不新建、不中断）。"""
        return self.create(item, actor=actor)

    # ---------- 读取 ----------
    def get_by_change_id(self, change_id: str) -> Optional[ChangeItem]:
        row = self.conn.execute("SELECT * FROM items WHERE change_id=?", (change_id,)).fetchone()
        return _item_from_row(row) if row else None

    def get(self, item_id: int) -> Optional[ChangeItem]:
        row = self.conn.execute("SELECT * FROM items WHERE id=?", (item_id,)).fetchone()
        return _item_from_row(row) if row else None

    def all(self) -> list[ChangeItem]:
        return [_item_from_row(r) for r in self.conn.execute("SELECT * FROM items ORDER BY id").fetchall()]

    def count(self) -> int:
        return int(self.conn.execute("SELECT COUNT(*) FROM items").fetchone()[0])

    # ---------- 字段更新（人工补录 / 状态推进的配套写） ----------
    def update_fields(self, change_id: str, **fields: Any) -> ChangeItem:
        allowed = {
            "drug_code", "field_name", "cur_value", "proposed_value", "generic_name",
            "code_pending_manual", "review_comment", "reject_reason", "receipt_no",
            "receipt_at", "error_class", "candidate_codes_json", "evidence_json",
            "cur_value_normalized", "proposed_value_normalized",
            "submitted_by", "reviewed_by", "status", "previous_change_id",
        }
        sets, args = [], []
        for k, v in fields.items():
            if k not in allowed:
                continue
            sets.append(f"{k}=?")
            args.append(int(v) if k == "code_pending_manual" else v)
        if not sets:
            return self.get_by_change_id(change_id)  # type: ignore[return-value]
        sets.append("updated_at=?")
        args.append(_now())
        args.append(change_id)
        self.conn.execute(f"UPDATE items SET {','.join(sets)} WHERE change_id=?", args)
        self.conn.commit()
        return self.get_by_change_id(change_id)  # type: ignore[return-value]

    # ---------- 状态推进 ----------
    def _transition(self, change_id: str, dst: Status | str, *, actor: str,
                    action: str, extra_fields: Optional[dict] = None,
                    reviewer_check: bool = False) -> ChangeItem:
        item = self.get_by_change_id(change_id)
        if item is None:
            raise GuardRejected(f"条目不存在：{change_id}")
        src = item.status

        def on_illegal(f: str, t: str, note: str):
            audit_mod.append(self.conn, audit_mod.AuditEvent(
                actor=actor, action="illegal_transition", drug_code=item.drug_code,
                field_name=item.field_name, detail={"from": f, "to": t, "note": note},
            ))

        if reviewer_check:
            assert_reviewer_not_submitter(item.submitted_by, item.reviewed_by, on_illegal=on_illegal)
        new_status = assert_transition(src, dst, action=action, on_illegal=on_illegal)
        fields = {"status": new_status.value}
        if extra_fields:
            fields.update(extra_fields)
        # status 不在 update_fields 白名单，单独写
        fields.pop("status")
        self.conn.execute(
            "UPDATE items SET status=?, updated_at=? WHERE change_id=?",
            (new_status.value, _now(), change_id),
        )
        if fields:
            self.update_fields(change_id, **fields)
        self.conn.commit()
        audit_mod.append(self.conn, audit_mod.AuditEvent(
            actor=actor, action=action, drug_code=item.drug_code,
            field_name=item.field_name, cur_value=item.cur_value,
            proposed_value=item.proposed_value, evidence=item.evidence,
            detail={"from": src.value, "to": new_status.value},
        ))
        return self.get_by_change_id(change_id)  # type: ignore[return-value]

    def fill_and_confirm(self, change_id: str, *, actor: str = "药事岗") -> ChangeItem:
        """draft_incomplete → draft（人工补齐四项后）。"""
        return self._transition(change_id, Status.DRAFT, actor=actor, action="confirmed")

    def send_to_review(self, change_id: str, *, actor: str = "药事岗") -> ChangeItem:
        return self._transition(change_id, Status.PENDING_REVIEW, actor=actor, action="reviewed")

    def submit(self, change_id: str, *, actor: str = "") -> ChangeItem:
        """pending_review → submitted，出站前强校验复核人≠经办人。

        actor 是本动作的复核人；若条目尚未记录 reviewed_by 则以此人填充。
        """
        item = self.get_by_change_id(change_id)
        # 复核人以执行复核动作的人为准：actor 非空则覆盖预存值，
        # 否则退回条目已记录的 reviewed_by（如详情页已选好复核人的场景）。
        reviewer = actor or (item.reviewed_by if item else "")
        if item and reviewer:
            self.update_fields(change_id, reviewed_by=reviewer)
            item = self.get_by_change_id(change_id)
        extra = {"reviewed_by": reviewer} if reviewer else {}
        return self._transition(change_id, Status.SUBMITTED, actor=reviewer or "system",
                                action="submitted", extra_fields=extra, reviewer_check=True)

    def return_item(self, change_id: str, comment: str, *, actor: str = "复核人") -> ChangeItem:
        """pending_review → returned，退回意见非空。"""
        assert_return_comment(comment)
        item = self.get_by_change_id(change_id)
        result = self._transition(change_id, Status.RETURNED, actor=actor, action="returned",
                                  extra_fields={"review_comment": comment})
        # 复核意见原文单独写一条审计留痕（返回动作审计不含意见全文）
        audit_mod.append(self.conn, audit_mod.AuditEvent(
            actor=actor, action="returned", drug_code=item.drug_code if item else "",
            field_name=item.field_name if item else "", detail={"review_comment": comment},
        ))
        return result

    def resubmit(self, change_id: str, *, actor: str = "药事岗") -> ChangeItem:
        """returned → draft → pending_review，按最新内容重算 change_id，旧键标 superseded。"""
        item = self.get_by_change_id(change_id)
        if item is None:
            raise GuardRejected(f"条目不存在：{change_id}")
        new_id = compute_change_id(item.drug_code, item.field_name, item.cur_value,
                                   item.proposed_value, item.evidence)
        self._transition(change_id, Status.DRAFT, actor=actor, action="resubmit")
        # 旧 change_id 记 superseded 审计，历史可回溯
        audit_mod.append(self.conn, audit_mod.AuditEvent(
            actor=actor, action="duplicated_submit", drug_code=item.drug_code,
            detail={"old_change_id": change_id, "new_change_id": new_id, "reason": "superseded"},
        ))
        if new_id != change_id:
            self.conn.execute("UPDATE items SET change_id=?, previous_change_id=? WHERE change_id=?",
                              (new_id, change_id, change_id))
            self.conn.commit()
        return self.get_by_change_id(new_id)  # type: ignore[return-value]

    def ack(self, change_id: str, *, receipt_no: str = "", receipt_at: str = "",
            actor: str = "system") -> ChangeItem:
        return self._transition(change_id, Status.ACKED, actor=actor, action="acked",
                                extra_fields={"receipt_no": receipt_no, "receipt_at": receipt_at})

    def reject(self, change_id: str, reason: str, *, actor: str = "system") -> ChangeItem:
        return self._transition(change_id, Status.REJECTED, actor=actor, action="rejected",
                                extra_fields={"reject_reason": reason})

    # ---------- 查询（T25） ----------
    def query(
        self,
        *,
        status: Optional[str] = None,
        drug_code: Optional[str] = None,
        submitted_by: Optional[str] = None,
        time_from: Optional[str] = None,
        time_to: Optional[str] = None,
        keyword: Optional[str] = None,
        order_by: str = "updated_at",
        desc: bool = True,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ChangeItem]:
        """按状态/药品码/经办人/时间窗/关键字过滤，支持分页排序。"""
        allowed_order = {"updated_at", "created_at", "drug_code", "status", "field_name"}
        order_col = order_by if order_by in allowed_order else "updated_at"
        sql = "SELECT * FROM items WHERE 1=1"
        args: list[Any] = []
        if status:
            sql += " AND status=?"
            args.append(status)
        if drug_code:
            sql += " AND drug_code=?"
            args.append(drug_code)
        if submitted_by:
            sql += " AND submitted_by=?"
            args.append(submitted_by)
        if time_from:
            sql += " AND created_at>=?"
            args.append(time_from)
        if time_to:
            sql += " AND created_at<=?"
            args.append(time_to)
        if keyword:
            sql += " AND (evidence_json LIKE ? OR drug_code LIKE ? OR generic_name LIKE ?)"
            kw = f"%{keyword}%"
            args += [kw, kw, kw]
        sql += f" ORDER BY {order_col} {'DESC' if desc else 'ASC'} LIMIT ? OFFSET ?"
        args += [limit, offset]
        return [_item_from_row(r) for r in self.conn.execute(sql, args).fetchall()]

    def consistency_warnings(self) -> list[str]:
        """一致性校验：每条条目至少有一条创建审计，否则告警。"""
        warnings = []
        rows = self.conn.execute("SELECT change_id FROM items").fetchall()
        for r in rows:
            n = self.conn.execute(
                "SELECT COUNT(*) FROM audit_log WHERE action='item_created' AND detail_json LIKE ?",
                (f'%"{r["change_id"]}"%',),
            ).fetchone()[0]
            if n == 0:
                warnings.append(f"条目 {r['change_id']} 缺少创建审计")
        return warnings
