"""T40：出站请求体逐字段与 spec.md §2.3 对齐。"""
from dmchange.config import Config
from dmchange.domain.models import ChangeItem, Evidence
from dmchange.outbound.mdm_client import (
    REQUIRED_BODY_FIELDS, EVIDENCE_FIELDS, build_payload, assert_field_conformance,
)
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def item():
    return ChangeItem(
        change_id="a" * 64, drug_code="XC0014N01400140014E0014", field_name="spec_pack_code",
        cur_value="0.5mg", proposed_value="1mg",
        evidence=[Evidence("spk0", 8000, 15000, "原话")],
        evidence_source="voice", submitted_by="张三", reviewed_by="李四", status="submitted",
    )


def test_all_required_fields():
    p = build_payload(item())
    assert set(REQUIRED_BODY_FIELDS).issubset(p.keys())
    assert assert_field_conformance(p) == []


def test_evidence_fields():
    p = build_payload(item())
    assert set(EVIDENCE_FIELDS).issubset(p["evidence"][0].keys())
    assert p["evidence"][0]["text"] == "原话"


def test_idempotency_key_equals_change_id():
    p = build_payload(item())
    assert p["change_id"] == "a" * 64  # Header 用同值


def test_field_domain():
    p = build_payload(item())
    p["field_name"] = "bad"
    assert "field_name 越界" in " ".join(assert_field_conformance(p))


def test_raw_values_only_no_normalized():
    p = build_payload(item())
    assert "normalized" not in str(p).lower()


def test_schema_doc():
    text = (ROOT / "docs" / "mdm-change-schema.md").read_text(encoding="utf-8")
    for f in REQUIRED_BODY_FIELDS:
        assert f in text
