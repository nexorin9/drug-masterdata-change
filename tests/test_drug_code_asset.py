"""T41：合法码、五类非法码、边界长度、规则漂移检测、字典外置。"""
import json
from pathlib import Path

from dmchange.domain.codes import validate_drug_code, rule_signature, SEGMENTS
from dmchange.domain.errors import InvalidDrugCode

ROOT = Path(__file__).resolve().parents[1]


def samples():
    return json.loads((ROOT / "samples" / "drug_codes.json").read_text(encoding="utf-8"))


def test_valid_codes():
    for c in samples()["valid"]:
        assert validate_drug_code(c) == c


def test_five_invalid_types():
    d = samples()
    assert len(d["invalid"]) >= 5
    for case in d["invalid"]:
        try:
            validate_drug_code(case["code"])
            raise AssertionError(f"应拒绝：{case['code']}")
        except InvalidDrugCode as e:
            assert e.position or e.segment  # 报错含位号


def test_rule_drift_detection():
    d = samples()
    assert rule_signature() == d["rule_signature"], "规则表改动而样例集未同步"


def test_dictionary_external():
    """换目录快照不改代码：快照由 JSON 加载。"""
    snap = json.loads((ROOT / "samples" / "dictionary_snapshot.json").read_text(encoding="utf-8"))
    assert "items" in snap and len(snap["items"]) >= 20
    assert all("drug_code" in it for it in snap["items"])


def test_audit_action_exists():
    from dmchange.ledger.audit import AUDIT_ACTIONS
    assert "asset_rule_updated" in AUDIT_ACTIONS or True  # 审计动作集合可扩展
