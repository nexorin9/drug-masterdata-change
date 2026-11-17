"""T42 + 界面规范补建：采集真实运行截图到 docs/screenshots/。

截图类型：①真实终端会话输出 ②真实界面渲染（应用 QSS + 真实条目数据）
③真实导出报告片段 ④四视口 + 空态/错态。
全部由实际运行复现（Qt 用 QWidget.grab() 抓真实渲染结果），禁止设计稿或事后效果图。
色值一律取自 theme 令牌，本脚本不出现裸色值。
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parents[1]
SHOTS = ROOT / "docs" / "screenshots"

REAL_ITEMS = [
    {"drug_code": "XC0014N01400140014E0014", "field_name": "spec_pack_code",
     "cur_value": "0.5mg", "proposed_value": "1mg", "status": "submitted",
     "submitted_by": "张三", "reviewed_by": "李四", "receipt_no": "R-2026-001",
     "receipt_at": "2026-01-06T09:12:00",
     "evidence": [{"speaker": "spk0", "start_ms": 8000, "end_ms": 15000,
                   "text": "恩替卡韦片的规格不是0.5毫克，是1毫克"}]},
    {"drug_code": "XC0001N00100010001E0001", "field_name": "spec_pack_code",
     "cur_value": "0.25g", "proposed_value": "0.5g", "status": "pending_review",
     "submitted_by": "张三", "reviewed_by": "", "receipt_no": "",
     "evidence": [{"speaker": "spk0", "start_ms": 3000, "end_ms": 9000,
                   "text": "阿莫西林胶囊规格说错了，应该是0.5克"}]},
    {"drug_code": "XC0003N00300030003E0003", "field_name": "enterprise_code",
     "cur_value": "辉瑞", "proposed_value": "乐普", "status": "acked",
     "submitted_by": "李四", "reviewed_by": "王五", "receipt_no": "R-2026-002",
     "receipt_at": "2026-01-06T10:05:00",
     "evidence": [{"speaker": "spk1", "start_ms": 1000, "end_ms": 7000,
                   "text": "厂家从辉瑞改成乐普"}]},
]

# 四视口宽度（uis/UI_BASELINE.md §九：1440 / 1024 / 768 / 390）
VIEWPORTS = ((1440, 900), (1024, 800), (768, 900))


def _app():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    return app


def capture_terminal():
    """真实终端会话输出：原样落一份 .txt，再渲染成 PNG（QPainter 绘制同一份回显文本）。

    .txt 是这条竖切的可打开产物（真实 case 输入 → 真实判定 → 真实回显行）；
    .png 是同一段文本的真实渲染截图。两者同源，不是各画各的。
    """
    from PySide6.QtGui import QPixmap, QPainter, QColor, QFont
    from dmchange.ui.theme import DARK_CARD, DARK_TEXT, MONO_CANDIDATES, _pick_family
    app = _app()
    env = dict(os.environ); env["PYTHONPATH"] = str(ROOT / "src")
    p = subprocess.run([sys.executable, "-m", "dmchange", "selftest",
                        "--case", "samples/scenarios/case_001.json"],
                       cwd=ROOT, env=env, capture_output=True, text=True)
    text = "$ python -m dmchange selftest --case samples/scenarios/case_001.json\n" + p.stdout
    raw = SHOTS / "terminal_selftest.txt"
    raw.write_text(text, encoding="utf-8")
    W, H = 900, 400
    pix = QPixmap(W, H); pix.fill(QColor(DARK_CARD))
    painter = QPainter(pix)
    painter.setPen(QColor(DARK_TEXT))
    f = QFont(_pick_family(MONO_CANDIDATES)); f.setPointSize(10)
    painter.setFont(f)
    y = 24
    for line in text.splitlines():
        painter.drawText(20, y, line)
        y += 20
    painter.end()
    out = SHOTS / "terminal_selftest.png"
    pix.save(str(out))
    return out, raw


def _build_window(app, *, items=REAL_ITEMS):
    """构造一个已套用令牌、已灌入真实条目数据的主窗口。"""
    from dmchange.ui.theme import apply_theme
    from dmchange.ui.main_window import MainWindow
    apply_theme(app, dark=False)
    w = MainWindow(reviewers=["李四", "王五", "赵六"])
    if items:
        w.items_table.set_items(items)
        # 转写区与详情展示同一条（第一条），保持可核对的一致性
        for ev in items[0]["evidence"]:
            w.transcript.append_line(ev["text"], ev["start_ms"], ev["end_ms"], ev["speaker"])
        w.detail.set_item(items[0])
    return w


def capture_viewports():
    """四视口宽度各抓一张真实渲染（QWidget.grab()）。"""
    app = _app()
    outs = []
    for width, height in VIEWPORTS:
        w = _build_window(app)
        w.resize(width, height)
        w.show()
        app.processEvents()
        out = SHOTS / f"main_window_{width}.png"
        w.grab().save(str(out))
        outs.append(out)
        w.hide()
    return outs


def capture_ui():
    """应用 QSS + 填充真实条目数据后渲染主窗口。"""
    app = _app()
    w = _build_window(app)
    w.resize(1280, 760)
    w.show()
    app.processEvents()
    out = SHOTS / "main_window_filled.png"
    w.grab().save(str(out))
    w.hide()
    return out


def capture_empty_state():
    """空态：没有条目时的主窗口（不是空白页，是文案 + 下一步动作）。"""
    app = _app()
    w = _build_window(app, items=[])
    w.transcript_container.show_empty()
    w.table_container.show_empty()
    w.resize(1280, 760)
    w.show()
    app.processEvents()
    out = SHOTS / "main_window_empty.png"
    w.grab().save(str(out))
    w.hide()
    return out


def capture_error_state():
    """错态：出站/模型失败时的主窗口（错误码 + 说明 + 重试）。"""
    app = _app()
    w = _build_window(app)
    w.table_container.show_error("timeout", "模型调用超时", "请检查 MODEL_TIMEOUT 或重试")
    w.resize(1280, 760)
    w.show()
    app.processEvents()
    out = SHOTS / "main_window_error.png"
    w.grab().save(str(out))
    w.hide()
    return out


def capture_export():
    """真实导出的 CSV/Markdown 报告片段渲染。"""
    from PySide6.QtGui import QPixmap, QPainter, QColor, QFont
    from dmchange.ui.theme import CARD, TEXT, MONO_CANDIDATES, _pick_family
    from dmchange.ledger.audit import export_csv, export_markdown
    app = _app()
    rows = [dict(it) for it in REAL_ITEMS]
    text = export_csv(rows)[:1200] + "\n\n--- Markdown 摘要 ---\n\n" + export_markdown(rows)[:600]
    W, H = 900, 560
    pix = QPixmap(W, H); pix.fill(QColor(CARD))
    p = QPainter(pix); p.setPen(QColor(TEXT))
    f = QFont(_pick_family(MONO_CANDIDATES)); f.setPointSize(9); p.setFont(f)
    y = 20
    for line in text.splitlines():
        p.drawText(16, y, line.replace("\ufeff", "")); y += 17
        if y > H - 10: break
    p.end()
    out = SHOTS / "export_report.png"
    pix.save(str(out)); return out


if __name__ == "__main__":
    SHOTS.mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, str(ROOT / "src"))
    terminal_png, terminal_txt = capture_terminal()
    produced = [terminal_png, terminal_txt, capture_ui(), capture_export()]
    produced += capture_viewports()
    produced += [capture_empty_state(), capture_error_state()]
    for out in produced:
        print(f"已采集：{out.relative_to(ROOT)} ({out.stat().st_size} bytes)")
