"""T10：目录守门三层校验与歧义拒绝。"""
from dmchange.domain.models import ChangeItem, Evidence
from dmchange.dictionary.store import DrugEntry
from dmchange.extract.guard import guard_item

ENTRIES = [
    DrugEntry("XA1234ABCD12345678ABCDE", "阿莫西林胶囊", "胶囊", "0.25g", "石药"),
    DrugEntry("XB1234ABCD12345678ABCDE", "阿莫西林胶囊", "胶囊", "0.5g", "石药"),
    DrugEntry("XC1234ABCD12345678ABCDE", "二甲双胍片", "片", "0.5g", "格华止"),
]


def test_ambiguous_rejected():
    item = ChangeItem(field_name="spec_pack_code", cur_value="0.25g", proposed_value="0.5g")
    gr = guard_item(item, entries=ENTRIES, generic_ref="阿莫西林胶囊")
    assert not gr.passed
    assert item.drug_code == ""
    assert len(item.candidate_codes) >= 2
    assert item.code_pending_manual is True


def test_unique_match_fills_code():
    item = ChangeItem(field_name="spec_pack_code", cur_value="0.5g", proposed_value="1g")
    gr = guard_item(item, entries=ENTRIES, generic_ref="二甲双胍片")
    assert gr.passed
    assert item.drug_code == ENTRIES[2].drug_code


def test_not_found_not_passed():
    item = ChangeItem(field_name="spec_pack_code")
    gr = guard_item(item, entries=ENTRIES, generic_ref="不存在的药")
    assert not gr.passed
    assert item.error_class == "drug_not_found"


def test_field_domain_checked():
    item = ChangeItem(drug_code=ENTRIES[2].drug_code, field_name="bogus")
    gr = guard_item(item, entries=ENTRIES, generic_ref="二甲双胍片")
    assert not gr.passed
    assert gr.layer == "business"


def test_bad_code_structure_layer():
    item = ChangeItem(drug_code="BAD", field_name="spec_pack_code")
    gr = guard_item(item, entries=ENTRIES, generic_ref="二甲双胍片")
    assert not gr.passed
    assert gr.layer == "structure"


def test_scale_matching_under_1000_entries():
    import time
    many = [DrugEntry(f"X{i:022d}", f"药品{i}", "片", "1g", "厂") for i in range(500)]
    t = time.time()
    gr = guard_item(ChangeItem(field_name="spec_pack_code"), entries=many, generic_ref="药品499")
    assert gr.passed
    assert (time.time() - t) < 3
