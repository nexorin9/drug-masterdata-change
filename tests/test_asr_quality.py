"""T14：识别质量回归与真实规模跑批报告字段齐全、两档样本量一致。"""
import json
from pathlib import Path

B = Path(__file__).resolve().parents[1] / "samples" / "benchmarks"


def _load(n):
    return json.loads((B / n).read_text(encoding="utf-8"))


def test_asr_quality_report():
    r = _load("asr_quality.json")
    assert r["sample_size"] >= 20
    assert len(r["no_hotword"]["detail"]) == len(r["with_hotword"]["detail"]) == 20
    assert "cer" in r["no_hotword"]["detail"][0]
    assert "hotword_hit" in r["with_hotword"]["detail"][0]
    assert "delta" in r


def test_scale_run():
    r = _load("scale_run.json")
    assert r["dictionary_count"] >= 300
    assert r["segments"] >= 20
    assert len(r["per_segment_ms"]) >= 20
    assert r["peak_memory_mb"] > 0


def test_thresholds_readable():
    t = _load("thresholds.json")
    assert t["max_segment_e2e_ms"] > 0


def test_corpus_manifest():
    m = _load("corpus_manifest.json")
    assert len(m["items"]) >= 20
    assert all("sha256" in x and "duration_s" in x for x in m["items"])


def test_hotword_ab_sample_equal():
    r = _load("hotword_ab.json")
    assert r["on"]["n"] == r["off"]["n"] == 8
    assert "hit_rate" in r["on"] and "hit_rate" in r["off"]
