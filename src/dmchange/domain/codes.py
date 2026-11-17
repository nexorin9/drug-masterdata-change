"""drug_code 权威结构与校验。

口径来源：domain/dictionaries/医保编码规则_ICD与药品.md §4（西药编码 23 位 6 部分）。
本模块把口径固化为外置可更新的 SEGMENTS 规则表；规则表改动而样例集未同步时，
test_drug_code_asset.py 的漂移检测会失败（T41）。

六部分（西药，共 23 位）：
  ①药品识别码 1 位大写字母，固定 'X'
  ②药品类别码 5 位，字母数字
  ③药品名称码 4 位，字母数字
  ④剂型码 4 位，数字
  ⑤规格包装码 4 位，数字
  ⑥企业码 5 位，字母数字
1+5+4+4+4+5 = 23

外置规则表字段：key / label / length / charset / start(推导) / end(推导)。
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from .errors import InvalidDrugCode


@dataclass(frozen=True)
class Segment:
    key: str
    label: str
    start: int
    length: int
    charset: str  # 'A'(大写字母) / 'N'(数字) / 'AN'(字母数字)
    fixed: Optional[str] = None  # 固定值，如识别码 'X'

    @property
    def end(self) -> int:
        return self.start + self.length

    def pattern(self) -> str:
        return {"A": "[A-Z]", "N": "[0-9]", "AN": "[A-Z0-9]"}[self.charset] + "{" + str(self.length) + "}"

    def expected_text(self) -> str:
        base = {"A": "大写字母 A-Z", "N": "数字 0-9", "AN": "大写字母或数字"}[self.charset]
        if self.fixed:
            return f"{base}（固定为 {self.fixed}）"
        return base


# 外置可更新规则表：换权威口径只改这里 + 样例集
SEGMENTS: tuple[Segment, ...] = (
    Segment("identifier", "药品识别码", 0, 1, "A", fixed="X"),
    Segment("category", "药品类别码", 1, 5, "AN"),
    Segment("name", "药品名称码", 6, 4, "AN"),
    Segment("dosage_form", "剂型码", 10, 4, "N"),
    Segment("spec_pack", "规格包装码", 14, 4, "N"),
    Segment("enterprise", "企业码", 18, 5, "AN"),
)

CODE_LENGTH = sum(s.length for s in SEGMENTS)  # 23

# 供 T41 漂移检测：规则表签名（规则改了样例集没改就要失败）
def rule_signature() -> str:
    return "|".join(f"{s.key}:{s.start}-{s.end}:{s.charset}:{s.fixed or ''}" for s in SEGMENTS)


def _segment_error(code: str, seg: Segment, reason: str = "") -> InvalidDrugCode:
    frag = code[seg.start:seg.end]
    pos = f"第{seg.start + 1}-{seg.end}位"
    msg = f"药品码{seg.label}校验失败：{pos}「{frag}」{reason}，期望{seg.expected_text()}"
    return InvalidDrugCode(msg, segment=seg.key, position=pos, expected=seg.expected_text())


def validate_drug_code(code: str) -> str:
    """校验 drug_code 结构，失败抛 InvalidDrugCode（报错含具体位号与期望字符集）。

    成功时原样返回 `code`。不静默通过：任何一位不合规都定位到段与位号。
    """
    if not isinstance(code, str):
        raise InvalidDrugCode("药品码必须为字符串", segment="root", position="第1位", expected="23 位字符串")
    if len(code) != CODE_LENGTH:
        raise InvalidDrugCode(
            f"药品码长度校验失败：应为 {CODE_LENGTH} 位，实际 {len(code)} 位「{code}」，"
            f"从第{len(code) + 1}位缺失或超出",
            segment="length", position=f"第1-{len(code)}位", expected=f"{CODE_LENGTH} 位",
        )
    if re.search(r"\s", code):
        raise InvalidDrugCode(
            "药品码含空格或空白字符", segment="root", position="含空白位", expected="无空白的连续编码"
        )
    if any(ord(ch) > 127 for ch in code):
        raise InvalidDrugCode(
            "药品码含全角或非 ASCII 字符", segment="root", position="含非 ASCII 位", expected="ASCII 编码"
        )
    for seg in SEGMENTS:
        frag = code[seg.start:seg.end]
        if seg.fixed is not None:
            if frag != seg.fixed:
                raise _segment_error(code, seg, f"应为 {seg.fixed}")
        pattern = {"A": r"[A-Z]", "N": r"[0-9]", "AN": r"[A-Z0-9]"}[seg.charset]
        if not re.fullmatch(pattern + "{" + str(seg.length) + "}", frag):
            raise _segment_error(code, seg, "字符集不合法")
    return code


def is_valid(code: str) -> bool:
    try:
        validate_drug_code(code)
        return True
    except InvalidDrugCode:
        return False


def split_segments(code: str) -> dict[str, str]:
    """按规则表拆分六段，供界面/导出展示（不做校验）。"""
    return {s.key: code[s.start:s.end] for s in SEGMENTS}
