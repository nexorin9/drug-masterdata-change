"""T18：标点兜底、编号重排、聚类未收敛、时间戳单调四类。"""
from dmchange.asr.normalize import normalize_sentences, stable_speakers
from dmchange.domain.models import Utterance


def test_punct_fallback():
    us = normalize_sentences([{"text": "没标点", "start": 0, "end": 1000}], punc_model_loaded=False)
    assert us[0].punct_source == "heuristic"


def test_speaker_renumber():
    us = [Utterance("a", 0, 1, "说话人甲"), Utterance("b", 1, 2, "说话人甲"),
          Utterance("c", 2, 3, "说话人乙")]
    stable_speakers(us)
    assert [u.speaker for u in us] == ["spk0", "spk0", "spk1"]


def test_unresolved():
    us = normalize_sentences([{"text": "说话。", "start": 0, "end": 1000}], cluster_resolved=False)
    assert us[0].speaker_resolved is False


def test_monotonic_nonoverlap():
    us = normalize_sentences([
        {"text": "一。", "start": 0, "end": 2000},
        {"text": "二。", "start": 1500, "end": 3000},
    ])
    assert us[0].end_ms <= us[1].start_ms
