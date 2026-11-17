"""E2E 演练主体：正向 + 两类负向 + 驳回场景，落请求体证据到 round 根 logs/。"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from dmchange.config import Config
from dmchange.domain.errors import ReviewerMismatch
from dmchange.domain.models import ChangeItem, Evidence, Status
from dmchange.ledger.audit import export_csv
from dmchange.ledger.db import connect, init_db
from dmchange.ledger.repository import Repository
from dmchange.outbound.mdm_client import HttpMdmClient, build_payload


class _FakeMdm:
    """协议替身：只在演练/测试层，非默认路径。"""

    def __init__(self):
        self.calls = []
        self.mode = "ack"

    def submit_change(self, payload, *, idempotency_key):
        self.calls.append((payload, idempotency_key))
        from dmchange.outbound.mdm_client import SubmitReceipt
        if self.mode == "5xx":
            return SubmitReceipt(503, {}, "https://mdm/.../changes", "POST", {})
        return SubmitReceipt(200, {"ok": True}, "https://mdm/.../changes", "POST", {})

    def fetch_receipt(self, change_id):
        if self.mode == "rejected":
            return {"status": "rejected", "receipt_no": "", "reject_reason": "规格口径不符"}
        return {"status": "acked", "receipt_no": "R-2026-001", "receipt_at": "2026-01-01T09:00:00+08:00"}


def make_item(**kw):
    base = dict(
        drug_code="XC0014N01400140014E0014", field_name="spec_pack_code",
        cur_value="0.5mg", proposed_value="1mg",
        evidence=[Evidence("spk0", 8000, 15000, "恩替卡韦片的规格不是0.5毫克，是1毫克")],
        submitted_by="张三", reviewed_by="李四",
    )
    base.update(kw)
    return ChangeItem(**base)


def run(logdir: Path):
    conn = connect(None)
    init_db(conn)
    repo = Repository(conn)
    mdm = _FakeMdm()

    # 正向
    it = repo.create(make_item(), actor="张三")
    repo.send_to_review(it.change_id, actor="张三")
    it = repo.submit(it.change_id, actor="李四")
    assert it.status == Status.SUBMITTED
    payload = build_payload(it)
    rec = mdm.submit_change(payload, idempotency_key=it.change_id)
    (logdir / "e2e_request_body.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    assert rec.status == 200 and rec.request_method == "POST"
    rcpt = mdm.fetch_receipt(it.change_id)
    it = repo.ack(it.change_id, receipt_no=rcpt["receipt_no"], receipt_at=rcpt["receipt_at"])
    assert it.status == Status.ACKED and it.receipt_no == "R-2026-001"
    print(f"[正向] 条目 {it.change_id[:12]}... → acked 回执 {it.receipt_no}")

    # 负向一：复核人=经办人
    it2 = repo.create(make_item(cur_value="0.25g", proposed_value="0.5g",
                                submitted_by="王五", reviewed_by=""), actor="王五")
    repo.send_to_review(it2.change_id, actor="王五")
    before = len(mdm.calls)
    try:
        repo.submit(it2.change_id, actor="王五")
        raise AssertionError("同人复核应被拦下")
    except ReviewerMismatch:
        assert len(mdm.calls) == before  # 出站计数未增加
    print("[负向一] 复核人=经办人 → 出站前拦下，出站计数 0")

    # 负向二：5xx → 停 submitted
    it3 = repo.create(make_item(cur_value="1g", proposed_value="2g"), actor="赵六")
    repo.send_to_review(it3.change_id, actor="赵六")
    it3 = repo.submit(it3.change_id, actor="李四")
    mdm.mode = "5xx"
    rec3 = mdm.submit_change(build_payload(it3), idempotency_key=it3.change_id)
    assert rec3.status >= 500
    assert repo.get_by_change_id(it3.change_id).status == Status.SUBMITTED
    print("[负向二] 端点 5xx → 条目停 submitted，未标 acked")

    # 正向三：驳回
    mdm.mode = "rejected"
    rcpt4 = mdm.fetch_receipt(it.change_id)
    assert rcpt4["status"] == "rejected" and rcpt4["reject_reason"]
    csv_text = export_csv([it.to_payload_dict()], demo=True)
    (logdir / "e2e_reject_evidence.csv").write_text(csv_text, encoding="utf-8")
    print(f"[正向三] 驳回原因：{rcpt4['reject_reason']}")

    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--logdir", required=True)
    args = ap.parse_args()
    run(Path(args.logdir))
