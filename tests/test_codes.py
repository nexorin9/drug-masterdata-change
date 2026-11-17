"""T2/T41：drug_code 23 位 6 部分结构校验。"""
import pytest

from dmchange.domain.codes import (
    CODE_LENGTH, SEGMENTS, is_valid, rule_signature, split_segments, validate_drug_code,
)
from dmchange.domain.errors import InvalidDrugCode


VALID = "XA1234ABCD12345678ABCDE"  # 1+5+4+4+4+5 = 23


def test_valid_code():
    assert len(VALID) == CODE_LENGTH == 23
    assert validate_drug_code(VALID) == VALID
    assert is_valid(VALID)


def test_split_segments():
    parts = split_segments(VALID)
    assert parts["identifier"] == "X"
    assert parts["category"] == "A1234"
    assert len(parts["enterprise"]) == 5


def test_too_short_reports_length_and_position():
    with pytest.raises(InvalidDrugCode) as e:
        validate_drug_code("XA1234")
    assert "23" in str(e.value)
    assert "第" in str(e.value)


def test_wrong_first_char_reports_position_and_expected():
    bad = "Z" + VALID[1:]
    with pytest.raises(InvalidDrugCode) as e:
        validate_drug_code(bad)
    assert "第1" in str(e.value)
    assert "X" in str(e.value)
    assert e.value.segment == "identifier"


def test_category_illegal_char_reports_position():
    bad = VALID[:1] + "12@34" + VALID[6:]
    with pytest.raises(InvalidDrugCode) as e:
        validate_drug_code(bad)
    assert "类别码" in str(e.value)
    assert "第2-6位" in str(e.value)


@pytest.mark.parametrize("bad", [
    VALID[:10] + "12A4" + VALID[14:],   # 剂型码含字母
    VALID[:14] + "12A4" + VALID[18:],   # 规格包装码含字母
    VALID + " ",                        # 尾部空格
    VALID[:5] + " " + VALID[6:],        # 中间空格
    VALID[:20] + "中" + VALID[21:],     # 全角字符
])
def test_variants_rejected(bad):
    with pytest.raises(InvalidDrugCode):
        validate_drug_code(bad)


def test_rule_signature_stable():
    assert len(SEGMENTS) == 6
    assert isinstance(rule_signature(), str) and rule_signature()
