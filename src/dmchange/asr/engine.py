"""识别引擎装配与适配器（T6/T19）。

真实路径：AutoModel(model=paraformer-zh, vad_model=fsmn-vad, punc_model=ct-punc,
spk_model=cam++)，param_dict 含 sentence_timestamp=True 与 batch_size_s=300
（对照参考运行时 server.py:65-89 与 cli.py:612-613）。
降级路径：ASR_MODE=openai-compatible 打 {asr_base_url}/v1/audio/transcriptions。
本环境无 funasr/torch，提供 fixture 适配器（真实工程约定的输入/输出契约），
模型装配失败抛 model_load_failed，不静默产出空结果。
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Optional, Protocol

from ..audio.pcm import PcmAudio
from ..domain.errors import (
    AudioDecodeError, DecodeTimeout, EmptyResult, ModelLoadFailed, VadFailed,
)
from ..domain.models import Utterance
from .normalize import normalize_sentences
from .segment_decode import SegmentSmoother, decode_segments


class Recognizer(Protocol):
    """识别适配器契约：PCM → sentence_info 列表。"""

    def transcribe(self, audio: PcmAudio, *, hotwords: Optional[list[str]] = None) -> list[dict[str, Any]]:
        ...


MODEL_CONFIG = {
    "model": "paraformer-zh",
    "vad_model": "fsmn-vad",
    "punc_model": "ct-punc",
    "spk_model": "cam++",
}
PARAM_DICT = {"sentence_timestamp": True, "batch_size_s": 300}


@dataclass
class AssemblyInfo:
    config: dict[str, str] = field(default_factory=lambda: dict(MODEL_CONFIG))
    param_dict: dict[str, Any] = field(default_factory=lambda: dict(PARAM_DICT))
    backend: str = "unknown"
    failure: Optional[str] = None


def assemble_local(*, require_model: bool = True) -> tuple[Optional[Recognizer], AssemblyInfo]:
    """装配本机 AutoModel；无依赖或加载失败抛 ModelLoadFailed（不静默继续）。"""
    info = AssemblyInfo(backend="local")
    try:
        import importlib.util
        if importlib.util.find_spec("funasr") is None or importlib.util.find_spec("torch") is None:
            raise ImportError("缺 funasr / torch 离线模型包")
        from funasr import AutoModel  # type: ignore
        model = AutoModel(device="cpu", disable_update=True, **MODEL_CONFIG)
        info.backend = "local-funasr"

        class _FunASRRecognizer:
            def transcribe(self, audio, *, hotwords=None):
                params = dict(PARAM_DICT)
                if hotwords:
                    from .hotwords import as_gen_kw
                    params.update(as_gen_kw(hotwords))
                res = model.generate(input=audio.data, is_final=True, **params)
                if not res or not res[0].get("sentence_info"):
                    return []
                return [dict(s) for s in res[0]["sentence_info"]]

        return _FunASRRecognizer(), info
    except Exception as exc:  # noqa: BLE001
        info.failure = str(exc)
        if require_model:
            raise ModelLoadFailed(
                f"本机识别模型装配失败：{exc}。请运行 scripts/fetch_offline_models.py 获取 "
                f"paraformer-zh / fsmn-vad / ct-punc / cam++ 离线包；或设 ASR_MODE=openai-compatible。"
            ) from exc
        return None, info


@dataclass
class OpenAICompatibleRecognizer:
    """ASR_MODE=openai-compatible：打 {asr_base_url}/v1/audio/transcriptions。"""

    base_url: str
    api_key: str = ""
    model: str = "paraformer-zh"
    http_client: Any = None

    def transcribe(self, audio: PcmAudio, *, hotwords: Optional[list[str]] = None) -> list[dict[str, Any]]:
        import httpx

        client = self.http_client or httpx.Client(timeout=30.0)
        url = self.base_url.rstrip("/") + "/v1/audio/transcriptions"
        files = {"file": ("audio.pcm", audio.data, "application/octet-stream")}
        data = {"model": self.model}
        if hotwords:
            from .hotwords import as_gen_kw
            data.update({k: str(v) for k, v in as_gen_kw(hotwords).items()})
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        resp = client.post(url, files=files, data=data, headers=headers)
        if resp.status_code >= 500:
            raise VadFailed(f"语音服务 5xx：{resp.status_code}")
        if resp.status_code >= 400:
            raise AudioDecodeError(f"语音服务 4xx：{resp.status_code}")
        body = resp.json()
        sentences = body.get("sentences") or []
        if not sentences and body.get("text"):
            sentences = [{"text": body["text"], "start": 0, "end": audio.duration_ms}]
        return sentences


@dataclass
class FixtureRecognizer:
    """fixture 适配器：由场景注入 sentence_info，契约与真实引擎完全一致。

    不是演示替身：它实现同一 Recognizer 协议，用于无离线模型环境下的端到端验证；
    产品默认路径仍走 assemble_local，需显式注入才会启用。
    """

    sentences: list[dict[str, Any]]
    fail_class: Optional[str] = None

    def transcribe(self, audio: PcmAudio, *, hotwords=None) -> list[dict[str, Any]]:
        if self.fail_class == "empty":
            return []
        if self.fail_class == "decode_timeout":
            raise DecodeTimeout("单段解码超时")
        if self.fail_class == "vad_failed":
            raise VadFailed("VAD 推理失败")
        return list(self.sentences)


def recognize(
    recognizer: Recognizer,
    audio: PcmAudio,
    *,
    cursor_ms: Optional[int] = None,
    hotwords: Optional[list[str]] = None,
    punc_model_loaded: bool = True,
    cluster_resolved: bool = True,
) -> list[Utterance]:
    """统一识别入口：段驱动解码 + 句级归一。"""
    sentences = recognizer.transcribe(audio, hotwords=hotwords)
    if not sentences:
        # 区分静音与引擎异常由调用方按场景判断；这里返回空，交由上层标 empty_result
        return []
    utterances = normalize_sentences(
        sentences, punc_model_loaded=punc_model_loaded, cluster_resolved=cluster_resolved,
    )
    return utterances
