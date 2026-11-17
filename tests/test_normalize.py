"""T6/T18：句级归一、标点兜底、编号稳定化、聚类未收敛、时间戳单调。"""
from dmchange.asr.normalize import normalize_sentences
from dmchange.domain.models import Utterance


def test_basic_normalize():
    us = normalize_sentences([
        {"text": "第一句。", "start": 0, "end": 1000, "speaker": "A"},
        {"text": "第二句。", "start": 1000, "end": 2000, "speaker": "B"},
    ])
    assert len(us) == 2
    assert [u.speaker for u in us] == ["spk0", "spk1"]


def test_punct_heuristic():
    us = normalize_sentences([{"text": "没有标点", "start": 0, "end": 1000}])
    assert us[0].punct_source == "heuristic"
    assert us[0].text.endswith("。")


def test_cluster_unresolved():
    us = normalize_sentences(
        [{"text": "说话。", "start": 0, "end": 1000, "speaker": "A"}],
        cluster_resolved=False,
    )
    assert us[0].speaker is None
    assert us[0].speaker_resolved is False


def test_timestamps_monotonic():
    us = normalize_sentences([
        {"text": "一。", "start": 0, "end": 1500},
        {"text": "二。", "start": 1000, "end": 2000},
    ])
    assert us[0].end_ms <= us[1].start_ms


def test_super_short_dropped():
    us = normalize_sentences([{"text": "短。", "start": 0, "end": 20}])
    assert len(us) == 0


def test_long_sentence_split():
    us = normalize_sentences([{"text": "长句。", "start": 0, "end": 70000}])
    assert len(us) == 2
