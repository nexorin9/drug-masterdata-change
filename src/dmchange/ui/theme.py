"""设计 token 与主题（T12 + 界面规范补建）：语义色、8px 栅格、字号层级、四态、状态色映射。

令牌先行：所有色值/间距/字号/圆角/动效时长集中在 TOKENS 与常量，业务代码不得内联裸色值。
QSS 变量化：theme.qss 用 {{token}} 占位符，render_qss() 启动时注入（QSS 原生不支持变量）。
配色按 plan.md §5 与 visual-target.md：石板蓝主色、米白底、砖红标错、墨绿成功。
深色模式走独立令牌（uis/UI_BASELINE.md §4「深色模式靠反相实现，必须走独立令牌」），不靠反相。
动效降级：set_reduced_motion() 打开后 duration_ms() 归零，等价 prefers-reduced-motion: reduce。
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

# ---------- 语义色板（token） ----------
PRIMARY = "#2F5D8C"
PRIMARY_HOVER = "#254C74"
PRIMARY_PRESSED = "#1D3C5C"
SURFACE = "#F6F4EF"
CARD = "#FFFFFF"
BORDER = "#E4E0D8"
DANGER = "#C0503A"
DANGER_HOVER = "#A64330"
SUCCESS = "#3F7A4F"
WARNING = "#9C6516"         # 深琥珀：作状态字与状态底都达 4.90:1
INFO = "#3A6EA5"
TEXT = "#2B2B2B"
TEXT_SECONDARY = "#6B665F"   # 暖灰，对米白底 5.18:1（WCAG 1.4.3 正文 4.5:1）
PLACEHOLDER = "#A8A29A"
FOCUS_RING = "#2F5D8C"
QUOTE_BG = "#FBF3D3"
NEUTRAL = "#5F6B78"          # 冷石板灰，作状态字与状态底都达 5.44:1
STATUS_RETURNED = "#7A6B8A"

# 实底上的前景色（主按钮、危险按钮、状态标签压色底时的文字）
ON_PRIMARY = "#FFFFFF"
# toast / 提示条底色（深墨，与页面底色区分）
TOAST_BG = "#2B2B2B"

# ---------- 深色模式独立令牌（不复用浅色值） ----------
DARK_SURFACE = "#1E2228"
DARK_CARD = "#262B32"
DARK_BORDER = "#3A4048"
DARK_TEXT = "#E6E9EC"
DARK_TEXT_SECONDARY = "#9AA4AE"
DARK_QUOTE_BG = "#38311F"

SEMANTIC_COLORS = {
    "primary": PRIMARY, "surface": SURFACE, "card": CARD, "border": BORDER,
    "danger": DANGER, "success": SUCCESS, "warning": WARNING,
    "info": INFO, "neutral": NEUTRAL, "text": TEXT,
    "text_secondary": TEXT_SECONDARY, "focus_ring": FOCUS_RING,
}
assert len(SEMANTIC_COLORS) >= 6

# ---------- 间距栅格（8px 基数） ----------
SPACE = {"space-1": 4, "space-2": 8, "space-3": 12, "space-4": 16,
         "space-5": 20, "space-6": 24, "space-8": 32}
GRID_BASE = 8

# ---------- 字号层级（界面密度基数 14px） ----------
FONT_SIZES = {
    "xs": 12, "sm": 13, "base": 14, "lg": 16, "xl": 20, "2xl": 26,
}
FONT_WEIGHTS = {"regular": 400, "medium": 500, "semibold": 600}
# QFont 只认单个真实族名，按候选顺序取系统里第一个可用的（中文字体不联网加载）
SANS_CANDIDATES = ("PingFang SC", "HarmonyOS Sans SC", "Source Han Sans SC",
                   "Microsoft YaHei", "Noto Sans CJK SC")
MONO_CANDIDATES = ("SF Mono", "Menlo", "Consolas", "DejaVu Sans Mono")
MONO_FAMILY = ", ".join(MONO_CANDIDATES)
# QSS 字体栈：Qt 能解析逗号分隔的族列表并取第一个可用族，
# 但 "-apple-system" 是 CSS 专有别名、Qt 不认，会每进程刷一条缺字警告，故不写进 QSS 栈。
SANS_FAMILY = ", ".join(SANS_CANDIDATES)
# 行悬停底色：与斑马纹（暖白 surface）区分开的冷灰，选中态是主色实底
HOVER_BG = "#EDF1F5"
ROW_HEIGHT = {"standard": 36, "compact": 32, "clickable": 44}
HEADER_HEIGHT = 40
# 控件高度三档：32 / 36 / 44（uis/UI_BASELINE.md §5 按钮）
CONTROL_HEIGHT = {"sm": 32, "md": 36, "lg": 44}
RADIUS = 6

# ---------- 状态色映射（7 类条目状态） ----------
STATUS_COLORS = {
    "draft_incomplete": DANGER,   # 要素缺失 砖红
    "draft": NEUTRAL,             # 草稿 灰蓝
    "pending_review": WARNING,    # 待复核 琥珀
    "submitted": PRIMARY,         # 已提交 石板蓝
    "acked": SUCCESS,             # 已确认 墨绿
    "rejected": DANGER,           # 已驳回 砖红加粗
    "returned": STATUS_RETURNED,  # 已退回 紫灰
}
STATUS_BOLD = {"rejected", "draft_incomplete"}

# ---------- 按钮四态 ----------
BUTTON_STATES = ("hover", "active", "disabled", "loading")

# ---------- 动效时长与缓动 ----------
DURATION = {"dur-1": 120, "dur-2": 180, "dur-3": 240, "dur-4": 320}
# Web 等价缓动（uis/UI_BASELINE.md §6）；Qt 侧用 QEasingCurve 的相近曲线
EASING = {"enter": "cubic-bezier(.2,.8,.2,1)", "exit": "cubic-bezier(.4,0,1,1)"}

# 动效降级开关：等价 prefers-reduced-motion: reduce。
# Qt 无 CSS 媒体查询，系统偏好无法直接读取，改由环境变量/运行时开关承载。
_REDUCED_MOTION = os.environ.get("DMCHANGE_REDUCED_MOTION", "").strip().lower() in {
    "1", "true", "yes", "on",
}


def set_reduced_motion(enabled: bool) -> None:
    """打开降级后所有动效时长归零（只保留状态切换本身）。"""
    global _REDUCED_MOTION
    _REDUCED_MOTION = bool(enabled)


def reduced_motion() -> bool:
    return _REDUCED_MOTION


def duration_ms(token: str) -> int:
    """取动效时长（ms）；降级开启时统一返回 0——等价 prefers-reduced-motion: reduce。"""
    if _REDUCED_MOTION:
        return 0
    return DURATION.get(token, DURATION["dur-2"])


# ---------- 等宽数字（tabular-nums） ----------
# CSS 侧写法为 font-variant-numeric: tabular-nums；Qt/QSS 无此属性，
# 改由 QFont 的 OpenType 'tnum' 特性施加，语义与 Web 端一致。
NUMERIC_FEATURE = "tabular-nums"

_FAMILY_CACHE: dict[str, str] = {}


def _pick_family(candidates: tuple[str, ...]) -> str:
    """取系统里第一个可用的字体族；找不到就用候选表最后一族（通用族）。"""
    key = ",".join(candidates)
    if key in _FAMILY_CACHE:
        return _FAMILY_CACHE[key]
    from PySide6.QtGui import QFontDatabase
    from PySide6.QtWidgets import QApplication
    if QApplication.instance() is None:
        # 没有 QGuiApplication 时 QFontDatabase 不可用，先退到候选表第一族
        chosen = candidates[0]
    else:
        available = set(QFontDatabase.families())
        chosen = next((c for c in candidates if c in available), candidates[-1])
    _FAMILY_CACHE[key] = chosen
    return chosen


def _with_tnum(font):
    """给字体打开等宽数字特性；运行环境不支持 OpenType 特性时原样返回。"""
    if hasattr(font, "setFeature"):
        font.setFeature(font.Tag("tnum"), 1)
    return font


def numeric_font(point_size: int = 10, *, bold: bool = False):
    """数字单元格字体：正文字族 + 等宽数字，保证数字列纵向不跳字。"""
    from PySide6.QtGui import QFont
    f = QFont(_pick_family(SANS_CANDIDATES))
    f.setPointSize(point_size)
    f.setBold(bold)
    return _with_tnum(f)


def code_font(point_size: int = 10, *, bold: bool = False):
    """编码/编号列字体：等宽字族 + 等宽数字（药品码、回执号）。"""
    from PySide6.QtGui import QFont
    f = QFont(_pick_family(MONO_CANDIDATES))
    f.setPointSize(point_size)
    f.setBold(bold)
    return _with_tnum(f)


@dataclass(frozen=True)
class StatusTag:
    label: str
    color: str
    bold: bool = False


def status_tag(status: str) -> StatusTag:
    label = {
        "draft_incomplete": "要素缺失", "draft": "草稿", "pending_review": "待复核",
        "submitted": "已提交", "acked": "已确认", "rejected": "已驳回", "returned": "已退回",
    }.get(status, status)
    return StatusTag(label, STATUS_COLORS.get(status, NEUTRAL), status in STATUS_BOLD)


def status_tag_qss(status: str) -> str:
    """状态标签的内联样式：色值全部来自令牌，不出现裸色。"""
    tag = status_tag(status)
    return (
        f"color:{ON_PRIMARY};background:{tag.color};"
        f"border-radius:{RADIUS * 2}px;padding:2px {SPACE['space-2']}px;"
    )


def toast_qss(*, error: bool = False) -> str:
    """toast 提示条的内联样式：错误用危险色，其余用墨色。"""
    bg = DANGER if error else TOAST_BG
    return (
        f"color:{ON_PRIMARY};background:{bg};"
        f"border-radius:{RADIUS}px;padding:{SPACE['space-2']}px {SPACE['space-3']}px;"
    )


def repolish(widget) -> None:
    """动态属性（role / alert）改完后重刷样式，让 QSS 重新匹配选择器。"""
    style = widget.style()
    style.unpolish(widget)
    style.polish(widget)


def _light_tokens() -> dict:
    return dict(SEMANTIC_COLORS)


def _dark_tokens() -> dict:
    tokens = _light_tokens()
    tokens.update({
        "surface": DARK_SURFACE, "card": DARK_CARD, "border": DARK_BORDER,
        "text": DARK_TEXT, "text_secondary": DARK_TEXT_SECONDARY,
        "quote_bg": DARK_QUOTE_BG,
    })
    return tokens


def render_qss(*, dark: bool = False) -> str:
    """把 TOKENS 注入 theme.qss 模板。QSS 不支持变量，用模板占位符方案。"""
    tokens = _dark_tokens() if dark else _light_tokens()
    tokens.update({
        "primary_hover": PRIMARY_HOVER, "primary_pressed": PRIMARY_PRESSED,
        "danger_hover": DANGER_HOVER,
        "on_primary": ON_PRIMARY, "toast_bg": TOAST_BG, "quote_bg": QUOTE_BG,
        "placeholder": PLACEHOLDER, "neutral": NEUTRAL, "info": INFO,
        "hover_bg": HOVER_BG,
        "row_height": str(ROW_HEIGHT["standard"]),
        "header_height": str(HEADER_HEIGHT),
        "control_height": str(CONTROL_HEIGHT["sm"]),
        "control_height_lg": str(CONTROL_HEIGHT["lg"]),
        "space_1": str(SPACE["space-1"]), "space_2": str(SPACE["space-2"]),
        "space_3": str(SPACE["space-3"]), "space_4": str(SPACE["space-4"]),
        "space_5": str(SPACE["space-5"]), "space_6": str(SPACE["space-6"]),
        "font_xs": str(FONT_SIZES["xs"]), "font_sm": str(FONT_SIZES["sm"]),
        "font_base": str(FONT_SIZES["base"]), "font_lg": str(FONT_SIZES["lg"]),
        "font_xl": str(FONT_SIZES["xl"]),
        "font_family": SANS_FAMILY, "radius": str(RADIUS),
    })
    qss_path = Path(__file__).with_name("theme.qss")
    template = qss_path.read_text(encoding="utf-8")
    for key, value in tokens.items():
        template = template.replace("{{" + key + "}}", value)
    return template


def apply_theme(app, *, dark: Optional[bool] = None):
    """应用 QSS 到 QApplication。dark=None 时跟随系统 palette。"""
    from PySide6.QtGui import QPalette, QFont
    if dark is None:
        palette = app.palette()
        bg = palette.color(QPalette.Window)
        dark = bg.lightness() < 128
    # 应用级字体：正文 14px（uis/UI_BASELINE.md §二 的界面密度基数）+ 中文系统字族。
    # 不设的话，QSS 没覆盖到的控件会走 Qt 默认的 "Sans Serif"，中文回落成不可控字形。
    font = QFont(_pick_family(SANS_CANDIDATES))
    font.setPointSize(FONT_SIZES["base"])
    app.setFont(font)
    app.setStyleSheet(render_qss(dark=dark))
