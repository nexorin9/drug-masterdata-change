"""T4/T27：审计表只增不改、八类动作、CSV 含原话与毫秒、脱敏。"""
import inspect

from dmchange.domain.models import ChangeItem, Evidence
from dmchange.ledger import audit as audit_mod
from dmchange.ledger.repository import Repository


def test_no_update_delete_path():
    src = inspect.getsource(audit_mod)
    assert "DELETE FROM audit_log" not in src
    assert "UPDATE audit_log" not in src
    assert not audit_mod.has_write_path()


def test_actions_and_append(conn):
    ev = audit_mod.AuditEvent(
        actor="药事岗", action="confirmed", drug_code="X1", field_name="spec_pack_code",
        cur_value="0.25", proposed_value="0.5",
        evidence=[Evidence("spk0", 8000, 15000, "不是0.25是0.5")],
    )
    rid = audit_mod.append(conn, ev)
    assert rid > 0
    rows = audit_mod.select(conn, action="confirmed")
    assert len(rows) == 1
    assert "不是0.25是0.5" in rows[0]["evidence_json"]
    assert "8000" in rows[0]["evidence_json"]


def test_csv_bom_and_columns(conn):
    repo = Repository(conn)
    it = repo.create(ChangeItem(
        drug_code="X1", field_name="spec_pack_code", cur_value="0.25", proposed_value="0.5",
        submitted_by="张三", reviewed_by="李四", status="submitted",
        evidence=[Evidence("spk0", 8000, 15000, "原话证据")],
    ), actor="tester")
    csv_text = audit_mod.export_csv([it.to_payload_dict()])
    assert csv_text.startswith("\ufeff")
    assert "依据原话" in csv_text and "起始毫秒" in csv_text
    assert "原话证据" in csv_text and "8000" in csv_text


def test_markdown_grouping(conn):
    md = audit_mod.export_markdown([
        {"drug_code": "X1", "field_name": "spec_pack_code", "cur_value": "a",
         "proposed_value": "b", "status": "submitted",
         "evidence": [{"speaker": "spk0", "start_ms": 1, "end_ms": 2, "text": "原话"}]},
    ])
    assert "## X1" in md and "原话" in md


def test_secret_masked_in_export():
    csv_text = audit_mod.export_csv(
        [{"drug_code": "X", "evidence": [{"text": "token=sk-secret-1234 原话"}]}],
        secrets=["sk-secret-1234"],
    )
    assert "sk-secret-1234" not in csv_text
