"""音频统一化：任意输入 → 16kHz 单声道 pcm_s16le 裸流。

主路径用 ffmpeg 子进程，命令行口径与参考运行时同构：
  ffmpeg -i src -f s16le -acodec pcm_s16le -ac 1 -ar 16000 -
无 ffmpeg/soundfile 时，对 wav 用标准库 wave 兜底（真实可用，非 mock），
保证离线装机与测试环境仍可产出合规 PCM。原始音频默认只在内存，不落盘。
"""
from __future__ import annotations

import shutil
import struct
import subprocess
import wave
from dataclasses import dataclass

TARGET_RATE = 16000
TARGET_CHANNELS = 1
TARGET_SAMPLE_WIDTH = 2  # 16 bit


@dataclass
class PcmAudio:
    data: bytes
    sample_rate: int = TARGET_RATE
    channels: int = TARGET_CHANNELS
    sample_width: int = TARGET_SAMPLE_WIDTH

    @property
    def duration_ms(self) -> int:
        n_samples = len(self.data) // (self.sample_width * self.channels)
        return int(n_samples / self.sample_rate * 1000) if self.sample_rate else 0

    def assert_conformant(self) -> None:
        assert self.sample_rate == TARGET_RATE, f"采样率应为 {TARGET_RATE}"
        assert self.channels == TARGET_CHANNELS, f"声道应为 {TARGET_CHANNELS}"
        assert self.sample_width == TARGET_SAMPLE_WIDTH, "位深应为 16bit"


def ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


def unify_file(path: str) -> PcmAudio:
    """把 wav/mp3/m4a 统一为 16k 单声道 16bit PCM。"""
    if ffmpeg_available():
        cmd = [
            "ffmpeg", "-nostdin", "-loglevel", "error", "-i", path,
            "-f", "s16le", "-acodec", "pcm_s16le", "-ac", str(TARGET_CHANNELS),
            "-ar", str(TARGET_RATE), "-",
        ]
        proc = subprocess.run(cmd, capture_output=True, timeout=300)
        if proc.returncode != 0:
            raise RuntimeError(f"ffmpeg 统一化失败：{proc.stderr.decode('utf-8', 'replace')[:200]}")
        audio = PcmAudio(proc.stdout)
        audio.assert_conformant()
        return audio
    # 兜底：标准库 wave 直接读取（仅 wav），必要时重采样到 16k
    return _unify_wav_stdlib(path)


def _unify_wav_stdlib(path: str) -> PcmAudio:
    try:
        with wave.open(path, "rb") as wf:
            rate = wf.getframerate()
            channels = wf.getnchannels()
            width = wf.getsampwidth()
            frames = wf.readframes(wf.getnframes())
    except (wave.Error, EOFError) as exc:
        raise RuntimeError(f"音频无法解码（缺 ffmpeg 且非合法 wav）：{exc}") from exc
    # 转 mono 16bit
    mono = _to_mono_16bit(frames, channels, width)
    if rate != TARGET_RATE:
        mono = _resample(mono, rate, TARGET_RATE)
    audio = PcmAudio(mono, TARGET_RATE, TARGET_CHANNELS, TARGET_SAMPLE_WIDTH)
    audio.assert_conformant()
    return audio


def _to_mono_16bit(data: bytes, channels: int, width: int) -> bytes:
    if width == 2 and channels == 1:
        return data
    samples = list(struct.unpack("<" + "h" * (len(data) // 2), data[: len(data) // 2 * 2]))
    out = []
    for i in range(0, len(samples), channels):
        chunk = samples[i:i + channels]
        v = sum(chunk) // len(chunk) if chunk else 0
        out.append(max(-32768, min(32767, v)))
    return struct.pack("<" + "h" * len(out), *out)


def _resample(data: bytes, src_rate: int, dst_rate: int) -> bytes:
    """最近邻重采样：测试与离线兜底够用；生产主路径走 ffmpeg 的高质量重采样。"""
    if src_rate == dst_rate:
        return data
    n_src = len(data) // 2
    samples = struct.unpack("<" + "h" * n_src, data[: n_src * 2])
    n_dst = int(n_src * dst_rate / src_rate)
    out = []
    for j in range(n_dst):
        idx = min(n_src - 1, int(j * src_rate / dst_rate))
        out.append(samples[idx] if samples else 0)
    return struct.pack("<" + "h" * len(out), *out)


def unify_raw_pcm(raw: bytes, *, rate: int = TARGET_RATE, channels: int = TARGET_CHANNELS,
                  width: int = TARGET_SAMPLE_WIDTH) -> PcmAudio:
    """麦克风原始流统一化（内存内，不落盘）。"""
    mono = _to_mono_16bit(raw, channels, width)
    if rate != TARGET_RATE:
        mono = _resample(mono, rate, TARGET_RATE)
    audio = PcmAudio(mono, TARGET_RATE, TARGET_CHANNELS, TARGET_SAMPLE_WIDTH)
    audio.assert_conformant()
    return audio


def synthesize_wav(path: str, duration_ms: int, *, rate: int = TARGET_RATE,
                   tone_hz: int = 220) -> None:
    """测试辅助：合成一段合法的 16k 单声道 wav。"""
    n = int(rate * duration_ms / 1000)
    frames = bytearray()
    for i in range(n):
        v = int(8000 * (1 if (i // (rate // max(tone_hz, 1))) % 2 else -1))
        frames += struct.pack("<h", v)
    with wave.open(path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        wf.writeframes(bytes(frames))
