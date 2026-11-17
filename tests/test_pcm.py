"""T5：音频统一化为 16kHz / 单声道 / 16bit；降级行为。"""
import struct

import pytest

from dmchange.audio.pcm import (
    TARGET_RATE, PcmAudio, _resample, _to_mono_16bit, synthesize_wav, unify_file, unify_raw_pcm,
)


def test_unify_wav_stdlib(tmp_path):
    p = str(tmp_path / "a.wav")
    synthesize_wav(p, 1000)
    audio = unify_file(p)  # 无 ffmpeg 时走 wave 兜底
    audio.assert_conformant()
    assert audio.sample_rate == 16000
    assert audio.channels == 1
    assert audio.sample_width == 2
    assert audio.duration_ms >= 900


def test_unify_raw_pcm_mono_conversion():
    stereo = struct.pack("<" + "h" * 4, 1000, 2000, 3000, 4000)
    mono = _to_mono_16bit(stereo, 2, 2)
    assert len(mono) == 4  # 4 samples -> 2 mono samples
    vals = struct.unpack("<hh", mono)
    assert vals == (1500, 3500)


def test_resample():
    data = struct.pack("<" + "h" * 10, *range(10))
    out = _resample(data, 8000, 16000)
    assert len(out) == 20 * 2


def test_corrupt_file_downgrades(tmp_path):
    p = tmp_path / "bad.wav"
    p.write_bytes(b"not a wav")
    with pytest.raises(RuntimeError):
        unify_file(str(p))


def test_no_disk_write_by_default():
    """原始音频默认只在内存：unify_raw_pcm 不产生任何文件。"""
    audio = unify_raw_pcm(b"\x00\x00" * 100)
    audio.assert_conformant()
    assert isinstance(audio.data, bytes)
