"""T29：四类终态、字段缺失、并发上限、轮询停止。"""
from dmchange.outbound.receipt import (
    ReceiptView, parse_receipt, refresh_many, should_continue_polling, is_terminal_status,
)
from dmchange.domain.models import Status


def test_acked_and_rejected():
    a = parse_receipt("c1", {"status": "acked", "receipt_no": "R1", "receipt_at": "t"})
    assert a.status == "acked" and a.terminal and a.receipt_no == "R1"
    b = parse_receipt("c2", {"status": "rejected", "reject_reason": "口径不符"})
    assert b.status == "rejected" and b.terminal and "口径不符" in b.reject_reason


def test_missing_fields_warn():
    v = parse_receipt("c", {"status": "weird"})
    assert v.status == "unknown" and v.warnings


def test_concurrency_cap_4():
    active = {"n": 0, "max": 0}
    import threading
    lock = threading.Lock()
    def fetch(cid):
        with lock:
            active["n"] += 1
            active["max"] = max(active["max"], active["n"])
        import time; time.sleep(0.01)
        with lock: active["n"] -= 1
        return {"status": "acked", "receipt_no": "R"}
    refresh_many([f"c{i}" for i in range(20)], fetch, max_workers=4)
    assert active["max"] <= 4


def test_polling_stop_and_terminal():
    views = [ReceiptView("c", status="acked")]
    assert not should_continue_polling(views, elapsed_ms=100, timeout_ms=10000)
    assert not should_continue_polling([ReceiptView("c", status="submitted")],
                                       elapsed_ms=20000, timeout_ms=10000)
    assert should_continue_polling([ReceiptView("c", status="submitted")],
                                   elapsed_ms=100, timeout_ms=10000)


def test_is_terminal():
    assert is_terminal_status(Status.ACKED) and is_terminal_status("rejected")
    assert not is_terminal_status("submitted")
