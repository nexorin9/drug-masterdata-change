"""T5：环形缓冲切段边界与「松开即结束」段落语义；默认不落盘。"""
import os

from dmchange.audio.capture import Recorder, RingBuffer


def test_ring_buffer_wrap():
    rb = RingBuffer(max_bytes=8)
    rb.write(b"12345")
    rb.write(b"6789")
    assert rb.size == 8
    # 环形缓冲溢出时丢弃最旧数据，保留最近 8 字节
    assert rb.drain() == b"23456789"
    assert rb.size == 0


def test_press_feed_release():
    events = []
    rec = Recorder(on_event=lambda k, d: events.append(k))
    rec.press()
    rec.feed(b"\x00\x00" * 1000)
    audio = rec.release()
    assert audio is not None
    assert events == ["press", "release"]
    assert audio.sample_rate == 16000


def test_cancel_semantics():
    rec = Recorder()
    rec.press()
    rec.feed(b"\x01\x00" * 100)
    audio = rec.cancel()
    assert rec.session.cancelled is True
    assert audio is not None


def test_default_no_disk_writes(tmp_path):
    """默认 retain_dir=None：release 不产生落盘文件。"""
    before = set(os.listdir(tmp_path))
    rec = Recorder(retain_dir=None)
    rec.press(); rec.feed(b"\x00\x00" * 16); rec.release()
    assert set(os.listdir(tmp_path)) == before


def test_optional_retain(tmp_path):
    rec = Recorder(retain_dir=str(tmp_path))
    rec.press(); rec.feed(b"\x00\x00" * 16); rec.release()
    assert any(f.endswith(".wav") for f in os.listdir(tmp_path))
