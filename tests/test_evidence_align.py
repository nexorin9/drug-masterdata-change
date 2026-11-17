"""T22：越界、去口水、共用句、强度、区间校正。"""
from dmchange.domain.models import Evidence, Utterance
from dmchange.extract.evidence import align_evidence, strip_filler, dedup_for_export, assess_strength

US = [Utterance("那个就是说不是0.25是0.5克。", 1000, 5000, "spk0")]


def test_out_of_range():
    a = align_evidence(5, US)
    assert a.missing and a.evidence is None


def test_filler_removed_raw_kept():
    a = align_evidence(0, US)
    assert "那个" not in a.evidence.display_text
    assert "那个" in a.evidence.text  # 原话保留


def test_shared_sentence():
    e = Evidence("spk0", 1000, 5000, "同一句")
    assert len(dedup_for_export([e, e])) == 1


def test_strength_strong():
    assert assess_strength("不是0.25是0.5") == "strong"
    assert assess_strength("好的") == "weak"


def test_correction_event():
    a = align_evidence(0, US, model_start_ms=999)
    assert a.corrected and a.evidence.start_ms == 1000
