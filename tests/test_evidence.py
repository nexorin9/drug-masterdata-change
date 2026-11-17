"""T10/T22：证据对齐——越界、去口水、共用句、强度、区间校正。"""
from dmchange.domain.models import Utterance
from dmchange.extract.evidence import (
    align_evidence, assess_strength, dedup_for_export, strip_filler,
)

US = [
    Utterance("那个就是说规格改成0.5克。", 8000, 15000, "spk0"),
    Utterance("寒暄。", 0, 2000, "spk1"),
]


def test_align_basic():
    a = align_evidence(0, US)
    assert not a.missing
    assert a.evidence.start_ms == 8000 and a.evidence.end_ms == 15000
    assert a.evidence.text and a.evidence.evidence_strength in ("strong", "weak")


def test_out_of_range_missing_but_kept():
    a = align_evidence(99, US)
    assert a.missing
    assert a.evidence is None
    assert "缺失" in a.warnings[0]


def test_strip_filler():
    assert strip_filler("那个就是说对对对改成0.5") == "改成0.5"


def test_strength():
    assert assess_strength("不是0.25是0.5") == "strong"
    assert assess_strength("您好") == "weak"


def test_shared_sentence_dedup():
    from dmchange.domain.models import Evidence
    e = Evidence("spk0", 8000, 15000, "同一句")
    out = dedup_for_export([e, e, e])
    assert len(out) == 1


def test_interval_correction():
    a = align_evidence(0, US, model_start_ms=999)
    assert a.corrected
    assert a.evidence.start_ms == 8000  # 以解码为准
