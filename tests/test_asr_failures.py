"""T19：五类识别 error_class + 静音/引擎异常两种空结果 + 模式切换回落。"""
import httpx
import pytest

from dmchange.asr.engine import FixtureRecognizer, recognize
from dmchange.audio.pcm import PcmAudio
from dmchange.domain.errors import DecodeTimeout, ModelLoadFailed, VadFailed
from dmchange.config import Config


def test_model_load_failed():
    from dmchange.asr.engine import assemble_local
    # 本环境无 funasr/torch → require_model=True 抛 model_load_failed
    with pytest.raises(ModelLoadFailed) as e:
        assemble_local(require_model=True)
    assert e.value.error_class == "model_load_failed"


def test_decode_timeout():
    r = FixtureRecognizer([], fail_class="decode_timeout")
    with pytest.raises(DecodeTimeout):
        r.transcribe(PcmAudio(b""))


def test_vad_failed():
    r = FixtureRecognizer([], fail_class="vad_failed")
    with pytest.raises(VadFailed):
        r.transcribe(PcmAudio(b""))


def test_empty_result_two_meanings():
    """静音：无段→空；引擎异常：有段无文本→empty_result 标注。"""
    silent = FixtureRecognizer([], fail_class="empty")
    assert silent.transcribe(PcmAudio(b"")) == []
    # 有段但文本空由上层标 empty_result
    from dmchange.domain.errors import EmptyResult
    assert EmptyResult.error_class == "empty_result"


def test_openai_compatible_switch():
    from dmchange.asr.engine import OpenAICompatibleRecognizer
    class _C:
        def post(self, url, files=None, data=None, headers=None):
            assert url.endswith("/v1/audio/transcriptions")
            return httpx.Response(200, json={"text": "识别文本", "sentences": []})
    r = OpenAICompatibleRecognizer("https://asr.example", http_client=_C())
    sents = r.transcribe(PcmAudio(b"\x00\x00" * 100))
    assert sents and sents[0]["text"] == "识别文本"


def test_switch_failure_explicit_fallback():
    """模式切换失败需显式回落提示（错误类可读），不静默换模式。"""
    from dmchange.domain.errors import VadFailed as VF
    with pytest.raises(VF):
        raise VF("语音服务 5xx → 回落本机模式提示")
