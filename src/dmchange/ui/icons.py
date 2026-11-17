"""内联 SVG 图标（T+ 界面规范补建）。

规则（uis/UI_BASELINE.md §5「图标」）：图标用 SVG，不用 PNG 缩放、不用 emoji、
不用 Qt 内置方块图标。SVG 以字符串形式内联在源码里，避免打包额外的资源目录；
颜色不写死在 SVG 里，而是由 theme 的令牌在渲染时注入（源码不出现裸色值）。
"""
from __future__ import annotations

# 统一的 24×24 线性图标，描边宽度 2，与 14px 正文的图标尺寸配套。
_MIC = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
    'stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
    '<rect x="9" y="2" width="6" height="11" rx="3"/>'
    '<path d="M5 10v1a7 7 0 0 0 14 0v-1"/>'
    '<path d="M12 18v4"/>'
    '</svg>'
)

_REFRESH = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
    'stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M20 11a8 8 0 1 0-2.3 5.7"/>'
    '<path d="M20 5v6h-6"/>'
    '</svg>'
)

_EXPORT = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
    'stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M12 3v12"/>'
    '<path d="m7 10 5 5 5-5"/>'
    '<path d="M4 19h16"/>'
    '</svg>'
)

_TEMPLATES = {"mic": _MIC, "refresh": _REFRESH, "export": _EXPORT}


def svg(name: str, color: str) -> str:
    """取指定图标的 SVG 文本；颜色由调用方从设计令牌传入。"""
    template = _TEMPLATES.get(name)
    if template is None:
        raise KeyError(f"未知图标：{name}")
    return template.format(color=color)
