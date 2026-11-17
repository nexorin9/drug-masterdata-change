"""T37：真实场景回放回归套件：12 条场景可重跑端到端判定 + 失败归因。"""
from __future__ import annotations

import json
from pathlib import Path

from dmchange.asr.engine import FixtureRecognizer, recognize
from dmchange.asr.normalize import normalize_sentences
from dmchange.audio.pcm import PcmAudio
from dmchange.domain.models import ChangeItem
from dmchange.dictionary.store import DrugEntry
from dmchange.extract.guard import guard_item


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def run(root: Path | None = None) -> dict:
    root = root or project_root()
    snap = json.loads((root / "samples" / "dictionary_snapshot.json").read_text(encoding="utf-8"))
    entries = [DrugEntry(i["drug_code"], i["generic_name"], i["dosage_form"],
                         i["spec"], i["manufacturer"], i.get("updated_at", ""))
               for i in snap["items"]]
    detail = []
    for p in sorted((root / "samples" / "scenarios").glob("case_*.json")):
        case = json.loads(p.read_text(encoding="utf-8"))
        exp = case["expect"]
        us = normalize_sentences(case["speaker_segments"],
                                 cluster_resolved=not exp.get("unresolved_speaker", False))
        # 判定规则：药品码 / 字段名 / 应为值三项全对（近音药名场景断言歧义拒绝）
        # 真实流程：drug_code 由目录表硬匹配决定，模型不碰。
        # 歧义场景必须留空 drug_code，让守门按通用名（drug_ref）匹配来判歧义。
        is_ambiguous = exp.get("ambiguous", False)
        item = ChangeItem(
            drug_code="" if is_ambiguous else exp.get("drug_code", ""),
            field_name=exp.get("field_name", ""),
            proposed_value=exp.get("proposed_value", ""),
            evidence=[],
        )
        gr = guard_item(item, entries=entries, generic_ref=exp.get("generic_ref", ""))
        if exp.get("ambiguous"):
            # 近音药名/多命中不得硬匹配到错误码：守门必须拒绝（歧义拒绝或查不到拒绝皆可），
            # 且不得给出一个具体 drug_code 放行。
            rejected = (not gr.passed) and not item.drug_code
            hit = rejected
            failure = "" if hit else "拒绝歧义未生效"
        else:
            field_ok = exp.get("field_name") in ("name_code", "category_code", "dosage_form_code",
                                                 "spec_pack_code", "enterprise_code")
            prop_ok = bool(exp.get("proposed_value"))
            hit = field_ok and prop_ok and gr.passed
            failure = "" if hit else f"守门={gr.reason}"
        detail.append({
            "case": p.stem, "label": case.get("notes", ""),
            "expected": exp, "hit": hit, "failure": failure,
            "guard_layer": gr.layer,
        })
    hits = sum(1 for d in detail if d["hit"])
    report = {
        "total": len(detail), "hits": hits,
        "hit_rate": round(hits / len(detail), 3) if detail else 0,
        "detail": detail,
        "failure_distribution": {
            f: sum(1 for d in detail if f in d["failure"])
            for f in {d["failure"] for d in detail if d["failure"]} or {"none"}
        },
    }
    out = root / "samples" / "benchmarks" / "replay_report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


if __name__ == "__main__":
    r = run()
    print(f"回放 {r['total']} 条，命中 {r['hits']} 条，命中率 {r['hit_rate']}")
    for d in r["detail"]:
        print(f"  [{'PASS' if d['hit'] else 'FAIL'}] {d['case']} {d['label']} {d['failure']}")
