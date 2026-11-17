"""麦克风采集：设备枚举、采集线程、环形缓冲、按住说话起止语义。

原始音频默认只在内存环形缓冲，不落盘；可选本地留存目录默认关闭。
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Callable, Optional

from .pcm import PcmAudio, unify_raw_pcm


@dataclass
class CaptureDevice:
    index: int
    name: str


def enumerate_devices() -> list[CaptureDevice]:
    """设备枚举：无音频后端时返回空列表并给出明确提示（不静默）。"""
    devices: list[CaptureDevice] = []
    try:
        import soundfile as sf  # type: ignore
        for i, dev in enumerate(sf.available_devices()):
            devices.append(CaptureDevice(i, str(dev.get("name", f"device-{i}"))))
    except Exception:
        # 无 soundfile / 无设备：空列表，调用方据此提示「请导入音频文件或配置设备」
        pass
    return devices


class RingBuffer:
    """定长字节环形缓冲，按段落语义切出音频。"""

    def __init__(self, max_bytes: int = 16_000 * 2 * 120):  # 默认 120 秒
        self.max_bytes = max_bytes
        self._buf = bytearray()
        self._lock = threading.Lock()

    def write(self, chunk: bytes) -> None:
        with self._lock:
            self._buf.extend(chunk)
            if len(self._buf) > self.max_bytes:
                del self._buf[: len(self._buf) - self.max_bytes]

    def drain(self) -> bytes:
        with self._lock:
            data = bytes(self._buf)
            self._buf.clear()
            return data

    @property
    def size(self) -> int:
        with self._lock:
            return len(self._buf)


@dataclass
class RecordingSession:
    """一次「按住说话」的实时状态。"""

    started_at: float = 0.0
    ended_at: float = 0.0
    recording: bool = False
    cancelled: bool = False
    chunks: list[bytes] = field(default_factory=list)

    @property
    def duration_ms(self) -> int:
        if not self.started_at:
            return 0
        end = self.ended_at or time.time()
        return int((end - self.started_at) * 1000)

    def finish(self, cancel: bool = False) -> PcmAudio:
        self.recording = False
        self.ended_at = time.time()
        self.cancelled = cancel
        raw = b"".join(self.chunks)
        return unify_raw_pcm(raw)  # 内存中统一化，默认不落盘


class Recorder:
    """按住说话：press() 开始、release() 结束、cancel() 中途放弃。

    feed() 供采集线程写入数据块（测试可直接喂入）。
    """

    def __init__(self, *, retain_dir: Optional[str] = None,
                 on_event: Optional[Callable[[str, dict], None]] = None):
        self.buffer = RingBuffer()
        self.session: Optional[RecordingSession] = None
        self.retain_dir = retain_dir  # 默认 None = 关闭本地留存
        self.on_event = on_event or (lambda *_: None)

    def press(self) -> None:
        self.buffer.drain()
        self.session = RecordingSession(started_at=time.time(), recording=True)
        self.on_event("press", {"at": self.session.started_at})

    def feed(self, chunk: bytes) -> None:
        self.buffer.write(chunk)
        if self.session is not None:
            self.session.chunks.append(chunk)

    def release(self, *, cancel: bool = False) -> Optional[PcmAudio]:
        if self.session is None:
            return None
        audio = self.session.finish(cancel=cancel)
        self.on_event("release", {"duration_ms": self.session.duration_ms, "cancelled": cancel})
        if self.retain_dir and not cancel:
            self._maybe_retain(audio)
        return audio

    def cancel(self) -> Optional[PcmAudio]:
        return self.release(cancel=True)

    def _maybe_retain(self, audio: PcmAudio) -> None:
        """可选本地留存：文件名不含患者标识与业务原文，仅时间戳；默认关闭。"""
        import os
        import wave

        os.makedirs(self.retain_dir, exist_ok=True)
        path = os.path.join(self.retain_dir, f"rec_{int(time.time() * 1000)}.wav")
        with wave.open(path, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(16000)
            wf.writeframes(audio.data)
        self.on_event("retained", {"path": path})
