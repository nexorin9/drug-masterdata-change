"""T27：只增不改、九类动作、CSV BOM+毫秒、Markdown、脱敏。"""
from dmchange.ledger import audit as A


def test_no_write_path():
    # 物理层只有 append/select 路径（has_write_path 从三函数源码判定无 update/delete）
    assert not A.has_write_path()


def test_nine_actions():
    for action in ("item_created", "manual_fill", "confirmed", "reviewed", "submitted",
                   "acked", "rejected", "returned", "duplicated_submit"):
        assert action in A.AUDIT_ACTIONS


def test_csv_bom_and_ms():
    rows = [{"drug_code": "X", "field_name": "f", "cur_value": "a", "proposed_value": "b",
             "evidence": [{"text": "原话", "speaker": "spk0", "start_ms": 1000, "end_ms": 2000}],
             "status": "submitted", "submitted_by": "u1", "reviewed_by": "u2", "receipt_no": "R"}]
    csv = A.export_csv(rows)
    assert csv.startswith("\ufeff")
    assert "起始毫秒" in csv and "原话" in csv and "1000" in csv


def test_markdown_group():
    md = A.export_markdown([{"drug_code": "X", "field_name": "f", "cur_value": "a",
                             "proposed_value": "b", "status": "acked",
                             "evidence": [{"text": "原", "speaker": "s", "start_ms": 1, "end_ms": 2}]}])
    assert "## X" in md and "原" in md


def test_secret_masked():
    csv = A.export_csv([{"drug_code": "X", "evidence": [{"text": "sk-abc12345 原话"}]}],
                       secrets=["sk-abc12345"])
    assert "sk-abc12345" not in csv and "原话" in csv
