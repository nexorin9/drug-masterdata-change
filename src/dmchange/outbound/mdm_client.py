"""MDM 变更单适配器（T11/T40）：落生产真实出站。

POST /api/v1/master-data/changes：Idempotency-Key = change_id，body 严格按 spec.md §2.3。
GET  /api/v1/master-data/changes/{change_id}：回执回读。
默认直连 $MDM_BASE_URL / Bearer $MDM_TOKEN；替身只在 tests/ 通过 http_client 注入。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from ..config import Config
from ..domain.models import ChangeItem

REQUIRED_BODY_FIELDS = (
    "change_id", "drug_code", "field_name", "cur_value", "proposed_value",
    "evidence", "evidence_source", "submitted_by", "reviewed_by", "status",
)
EVIDENCE_FIELDS = ("speaker", "start_ms", "end_ms", "text")


@dataclass
class SubmitReceipt:
    status: int
    body: dict[str, Any]
    request_url: str
    request_method: str
    headers: dict[str, str]


class MdmPort:
    """正式对接层协议（便于测试替身实现同一协议）。"""

    def submit_change(self, payload: dict[str, Any], *, idempotency_key: str) -> SubmitReceipt:
        raise NotImplementedError

    def fetch_receipt(self, change_id: str) -> dict[str, Any]:
        raise NotImplementedError


class HttpMdmClient(MdmPort):
    def __init__(self, cfg: Config, *, http_client: Any = None, demo: bool = False):
        self.cfg = cfg
        self._client = http_client
        self.demo = demo

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.cfg.mdm_token}",
            "Content-Type": "application/json",
        }

    def submit_change(self, payload: dict[str, Any], *, idempotency_key: str) -> SubmitReceipt:
        import httpx

        missing = [f for f in REQUIRED_BODY_FIELDS if f not in payload]
        if missing:
            raise ValueError(f"出站请求体缺字段：{missing}")
        for ev in payload.get("evidence", []):
            if not all(f in ev for f in EVIDENCE_FIELDS):
                raise ValueError(f"evidence 条目缺字段：{ev}")
        url = self.cfg.mdm_base_url.rstrip("/") + "/api/v1/master-data/changes"
        headers = self._headers()
        headers["Idempotency-Key"] = idempotency_key
        client = self._client or httpx.Client(timeout=30.0)
        resp = client.post(url, json=payload, headers=headers)
        body = resp.json() if resp.content else {}
        return SubmitReceipt(resp.status_code, body, url, "POST", headers)

    def fetch_receipt(self, change_id: str) -> dict[str, Any]:
        import httpx

        url = self.cfg.mdm_base_url.rstrip("/") + f"/api/v1/master-data/changes/{change_id}"
        client = self._client or httpx.Client(timeout=30.0)
        resp = client.get(url, headers=self._headers())
        return resp.json() if resp.content else {}


def build_payload(item: ChangeItem) -> dict[str, Any]:
    """从条目构造 §2.3 出站请求体（只传原文）。"""
    return item.to_payload_dict()


def assert_field_conformance(payload: dict[str, Any]) -> list[str]:
    """字段级规范核对：返回问题列表，空表示逐项匹配。"""
    problems: list[str] = []
    for f in REQUIRED_BODY_FIELDS:
        if f not in payload:
            problems.append(f"缺字段 {f}")
    if payload.get("idempotency_key_mismatch"):
        problems.append("Idempotency-Key 与 change_id 不一致")
    ev = payload.get("evidence", [])
    if not ev:
        problems.append("evidence 数组为空")
    for i, e in enumerate(ev):
        for f in EVIDENCE_FIELDS:
            if f not in e:
                problems.append(f"evidence[{i}] 缺 {f}")
        if not str(e.get("text", "")).strip():
            problems.append(f"evidence[{i}] text 为空")
    allowed = {"name_code", "category_code", "dosage_form_code", "spec_pack_code", "enterprise_code"}
    if payload.get("field_name") not in allowed:
        problems.append("field_name 越界")
    return problems
