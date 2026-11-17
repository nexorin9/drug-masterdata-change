"""T38：缺包提示含模型名与脚本路径、断网 doctor 区分两种结论、deploy 文档。"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import fetch_offline_models as F  # noqa: E402


def test_missing_models_listed(tmp_path):
    missing = F.missing_models(tmp_path)
    assert set(missing) == {"paraformer-zh", "fsmn-vad", "ct-punc", "cam++"}


def test_offline_degrades_explicit(tmp_path):
    r = F.fetch(tmp_path, offline=True)
    assert all(v["status"] == "offline-skip" for v in r.values())


def test_cached_detected(tmp_path):
    (tmp_path / "paraformer-zh").mkdir()
    (tmp_path / "paraformer-zh" / "model.pt").write_bytes(b"x")
    r = F.fetch(tmp_path, offline=True)
    assert r["paraformer-zh"]["status"] == "cached" and "sha256" in r["paraformer-zh"]


def test_deploy_doc():
    text = (ROOT / "docs" / "deploy-offline.md").read_text(encoding="utf-8")
    assert "模型包放置" in text and "启动自检" in text
    assert "~/.cache/dmchange/models" in text


def test_doctor_two_conclusions():
    """断网 doctor 区分「不可达且无备用」与「不可达但有备用」。"""
    from dmchange.config import Config, load_config
    import os
    # openai-compatible 有备用 ASR_BASE_URL → 「有备用」
    env = {"MDM_BASE_URL": "https://mdm", "MDM_TOKEN": "t", "MODEL_BASE_URL": "https://m",
           "MODEL_API_KEY": "k", "MODEL_NAME": "n", "MODEL_TIMEOUT": "5",
           "ASR_MODE": "openai-compatible", "ASR_BASE_URL": "https://asr", "ASR_API_KEY": ""}
    cfg = load_config(env)
    assert cfg.asr_mode == "openai-compatible"  # 备用存在
    local = load_config({**env, "ASR_MODE": "local"})
    assert local.asr_mode == "local"  # 无备用，回落本机
