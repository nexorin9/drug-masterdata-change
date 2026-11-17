"""T21：否定方向、规格拆分、单位归一、五类边界、原文并存。"""
from dmchange.extract.parser import (
    parse_correction, parse_spec, direction_values, normalize_cn_number,
)


def test_negative_correction():
    c = parse_correction("不是0.25，是0.5")
    assert c and c.negated == "0.25" and c.corrected == "0.5"
    assert direction_values("不是0.25，是0.5") == ("0.25", "0.5")


def test_said_wrong():
    c = parse_correction("规格说错了，应该是0.5g")
    assert c and c.corrected == "0.5g" and c.pattern == "said_wrong"


def test_spec_content_times_fill():
    s = parse_spec("1g×10支")
    assert s.content_value == "1" and s.content_unit == "g"
    assert s.fill_value == "10" and s.fill_unit == "支"
    assert s.raw_text == "1g×10支"


def test_units():
    s = parse_spec("500毫克")
    assert s.content_value == "500" and s.content_unit == "mg"


def test_cn_number():
    assert normalize_cn_number("十") == "10"
    assert normalize_cn_number("两") == "2"
    assert normalize_cn_number("十二") == "12"


def test_raw_text_always_present():
    for t in ("缺一", "不是A是B", "超长" * 100, "十片", "无单位123"):
        s = parse_spec(t)
        assert s.raw_text == t
