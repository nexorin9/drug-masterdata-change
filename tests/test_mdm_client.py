"""T11/T40：MDM 出站协议逐项断言（替身只在测试层）。"""
import httpx

from dmchange.config import Config
from dmchange.domain.models import ChangeItem, Evidence
from dmchange.outbound.mdm_client import (
    HttpMdmClient, assert_field_conformance, build_payload,
)
from dmchange.outbound.outbox import enqueue, mark_attempt, resume


def cfg():
    return Config("https://mdm.example", "token-abc", "x", "x", "x", 1, "local", "", "")


item = ChangeItem(
    change_id="a" * 64, drug_code="XA1234ABCD12345678ABCDE", field_name="spec_pack_code",
    cur_value="0.25", proposed_value="0.5",
    evidence=[Evidence("spk0", 8000, 15000, "不是0.25是0.5")],
    submitted_by="张三", reviewed_by="李四", status="submitted",
)


class _Client:
    def __init__(self, status=200):
        self.status, self.calls = status, []

    def post(self, url, json=None, headers=None):
        self.calls.append((url, json, headers))
        return httpx.Response(self.status, json={"ok": True})

    def get(self, url, headers=None):
        return httpx.Response(200, json={"status": "acked", "receipt_no": "R1"})


def test_post_contract():
    fc = _Client()
    client = HttpMdmClient(cfg(), http_client=fc)
    payload = build_payload(item)
    rec = client.submit_change(payload, idempotency_key=item.change_id)
    url, body, headers = fc.calls[0]
    assert url == "https://mdm.example/api/v1/master-data/changes"
    assert rec.request_method == "POST"
    assert headers["Authorization"] == "Bearer token-abc"
    assert headers["Idempotency-Key"] == item.change_id
    assert body["change_id"] == item.change_id
    assert body["evidence"][0]["text"] == "不是0.25是0.5"


def test_field_conformance():
    assert assert_field_conformance(build_payload(item)) == []
    bad = build_payload(item)
    del bad["proposed_value"]
    assert "proposed_value" in " ".join(assert_field_conformance(bad))


def test_fetch_receipt():
    client = HttpMdmClient(cfg(), http_client=_Client())
    r = client.fetch_receipt(item.change_id)
    assert r["status"] == "acked"


def test_outbox_retry_state_stays_submitted(conn):
    eid = enqueue(conn, item.change_id, build_payload(item))
    from dmchange.outbound.outbox import _row_to_entry
    row = conn.execute("SELECT * FROM outbox WHERE id=?", (eid,)).fetchone()
    state = mark_attempt(conn, _row_to_entry(row), success=False, error="network")
    assert state == "pending"
    assert resume(conn)["pending"] >= 1
