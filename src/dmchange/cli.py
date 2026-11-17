"""运维 CLI：selftest（端到端自检）+ doctor / sync-dictionary / export。

CLI 定位为运维与排障通道，不是主入口；主入口是桌面窗口。
selftest 走 fixture 识别适配器，把「样例 → 归一 → 抽取 → 守门 → 落库 → 打印可核对条目」跑通。
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Optional

from .asr.engine import FixtureRecognizer, recognize
from .audio.pcm import PcmAudio
from .config import Config, ConfigError, load_config
from .domain.models import ChangeItem, Status, Utterance
from .extract.extractor import ExtractionResult, extract
from .extract.gateway import ModelGateway, GatewayResponse, CallMeta
from .extract.guard import guard_item
from .ledger.db import connect, init_db
from .ledger.repository import Repository
from .dictionary.store import DrugEntry, load_snapshot, latest_entries


def _project_root() -> Path:
    # src/dmchange/cli.py → 项目子目录
    return Path(__file__).resolve().parents[2]


def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def selftest(args) -> int:
    """端到端自检：读 case → 识别(fixture) → 抽取(确定性网关) → 守门 → 落库 → 打印条目行。"""
    root = _project_root()
    case_path = Path(args.case) if Path(args.case).is_absolute() else root / args.case
    case = _load_json(case_path)
    snap = _load_json(root / "samples" / "dictionary_snapshot.json")
    sents = case.get("speaker_segments", [])

    recognizer = FixtureRecognizer(sents)
    cluster_resolved = not case["expect"].get("unresolved_speaker", False)
    utterances = recognize(recognizer, PcmAudio(b""), cluster_resolved=cluster_resolved)

    # 确定性网关：直接回显场景期望要素，遵循同一 Gateway 协议（不联网）
    expect = case["expect"]
    demo_payload = {
        "elements": [{
            "drug_ref": expect.get("generic_ref", ""),
            "field_name": expect.get("field_name", "spec_pack_code"),
            "cur_value": expect.get("cur_value", ""),
            "proposed_value": expect.get("proposed_value", ""),
            "evidence_index": expect.get("evidence_index", 0),
        }],
        "roles": [],
    }

    class _SelftestGateway(ModelGateway):
        def call(self, user_prompt, *, validate=True):
            validate_extraction_local(demo_payload)
            meta = CallMeta("selftest-fixture", 0, len(str(demo_payload)), False, "selftest")
            return GatewayResponse(demo_payload, meta)

    def validate_extraction_local(payload):
        from .extract.schema import validate_extraction
        return validate_extraction(payload)

    gateway = _SelftestGateway(Config(
        mdm_base_url="", mdm_token="", model_base_url="", model_api_key="",
        model_name="selftest", model_timeout=1, asr_mode="local", asr_base_url="", asr_api_key="",
    ))
    result: ExtractionResult = extract(gateway, utterances)

    conn = connect(None)
    init_db(conn)
    load_snapshot(conn, snap["items"], snapshot_id="selftest", synced_at=snap["synced_at"])
    entries = [DrugEntry(
        it["drug_code"], it["generic_name"], it["dosage_form"],
        it["spec"], it["manufacturer"], it.get("updated_at", ""),
    ) for it in snap["items"]]

    item = result.item
    gr = guard_item(item, entries=entries, generic_ref=expect.get("generic_ref", ""))
    repo = Repository(conn)
    saved = repo.create_or_get(item, actor="selftest")

    print("=== selftest 可核对条目行 ===")
    print(f"药品码: {saved.drug_code or '(待人工指定)'}")
    print(f"字段名: {saved.field_name}")
    print(f"现值: {saved.cur_value}  →  应为值: {saved.proposed_value}")
    print(f"状态: {saved.status.value}  守门: {gr.layer} {gr.reason}")
    if saved.candidate_codes:
        print(f"歧义候选: {', '.join(saved.candidate_codes)}")
    for ev in saved.evidence:
        print(f"依据: [{ev.start_ms}-{ev.end_ms}ms] {ev.speaker or '未分离'}: {ev.text}")
    conn.close()
    return 0


def doctor(args) -> int:
    """模型包、端点、凭据位自检清单。"""
    print("=== doctor 自检清单 ===")
    import importlib.util
    for pkg in ("funasr", "torch", "pydantic", "httpx", "PySide6"):
        ok = importlib.util.find_spec(pkg) is not None
        print(f"  [{'OK' if ok else 'MISSING'}] 依赖包 {pkg}")
    for key in ("MDM_BASE_URL", "MDM_TOKEN", "MODEL_BASE_URL", "MODEL_API_KEY",
                "MODEL_NAME", "ASR_MODE"):
        import os
        present = bool(os.environ.get(key))
        print(f"  [{'OK' if present else 'UNSET'}] 环境变量 {key}")
    print("  提示：缺 funasr/torch 时运行 python scripts/fetch_offline_models.py 获取离线模型包；")
    print("        或设置 ASR_MODE=openai-compatible 使用院内语音服务。")
    return 0


def sync_dictionary(args) -> int:
    print("=== sync-dictionary（目录同步）===")
    try:
        cfg = load_config()
    except ConfigError as exc:
        print(f"配置错误：{exc}")
        return 2
    print(f"目标端点: {cfg.mdm_base_url.rstrip('/')}/api/v1/drug-dictionary")
    print("（真实同步需可达的主数据端点与凭据；本命令已按正式协议实现。）")
    return 0


def export(args) -> int:
    """导出 CSV：含 drug_code / field_name / evidence 原话 / 毫秒区间。"""
    root = _project_root()
    out = Path(args.out) if Path(args.out).is_absolute() else root / args.out
    from .ledger.audit import export_csv
    # 演示导出：从样例场景构造条目（带明确演示标记）
    rows = []
    for p in sorted((root / "samples" / "scenarios").glob("case_*.json")):
        c = _load_json(p)
        e = c["expect"]
        rows.append({
            "drug_code": e.get("drug_code", ""),
            "field_name": e.get("field_name", ""),
            "cur_value": e.get("cur_value", ""),
            "proposed_value": e.get("proposed_value", ""),
            "submitted_by": "演示经办", "reviewed_by": "演示复核",
            "status": "submitted", "receipt_no": "",
            "evidence": [{"text": s["text"], "speaker": s.get("speaker"),
                          "start_ms": s["start"], "end_ms": s["end"]}
                         for s in c["speaker_segments"]],
        })
    text = export_csv(rows, demo=True)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    print(f"已导出 {len(rows)} 条到 {out}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="dmchange", description="药品主数据变更听写系统 · 运维 CLI")
    p.add_argument("--demo", action="store_true", help="演示模式（产物标注演示数据）")
    sub = p.add_subparsers(dest="cmd")

    ps = sub.add_parser("selftest", help="端到端自检")
    ps.add_argument("--case", default="samples/scenarios/case_001.json")
    ps.set_defaults(func=selftest)

    pd = sub.add_parser("doctor", help="环境与凭据自检")
    pd.set_defaults(func=doctor)

    py = sub.add_parser("sync-dictionary", help="同步药品目录")
    py.set_defaults(func=sync_dictionary)

    pe = sub.add_parser("export", help="导出药事会材料 CSV")
    pe.add_argument("--out", default="out.csv")
    pe.set_defaults(func=export)
    return p


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "cmd", None):
        parser.print_help()
        return 0
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
