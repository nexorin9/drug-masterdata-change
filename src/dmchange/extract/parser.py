"""口语否定式纠正与规格数值解析器（T21）。

模型负责判方向与选依据句，数值与实体一律由规则做。
「不是 0.25，是 0.5」「1g×10 支」必须拆准，原文必须留档。
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

# 单位归一表：外置可更新
UNIT_NORMALIZE = {
    "mg": "mg", "毫克": "mg",
    "g": "g", "克": "g",
    "ug": "ug", "μg": "ug", "微克": "ug",
    "ml": "ml", "mL": "ml", "毫升": "ml",
    "支": "支", "瓶": "瓶", "袋": "袋", "片": "片",
}
CN_NUM = {"一": "1", "二": "2", "两": "2", "三": "3", "四": "4", "五": "5",
          "六": "6", "七": "7", "八": "8", "九": "9", "十": "10"}


@dataclass
class SpecValue:
    content_value: str = ""
    content_unit: str = ""
    fill_value: str = ""
    fill_unit: str = ""
    raw_text: str = ""


@dataclass
class Correction:
    negated: str       # 否定项（现值）
    corrected: str     # 正确项（应为值）
    raw_text: str
    pattern: str       # not_x_is_y / said_wrong / x_written_as_y


def normalize_cn_number(token: str) -> str:
    if token in CN_NUM:
        return CN_NUM[token]
    m = re.fullmatch(r"十([一二三四五六七八九])", token)
    if m:
        return "1" + CN_NUM[m.group(1)]
    return token


_NUM = r"[0-9]+(?:\.[0-9]+)?|十[一二三四五六七八九]|[一二三四五六七八九十]"
_NUM_C = rf"(?:{_NUM})"  # 非捕获包裹，保证与单位拼接时不因 | 而松散绑定
_UNIT = r"(?:mg|ug|μg|ml|mL|克|毫克|微克|毫升|g|支|瓶|袋|片)"
_VAL = rf"{_NUM_C}{_UNIT}?|{_NUM_C}"  # 数值+可选单位，供否定句式捕获


def parse_correction(text: str) -> Optional[Correction]:
    """三类否定句式归一为（否定项、正确项）。"""
    raw = text.strip()
    # 不是 X，是 Y
    m = re.search(rf"不是\s*({_VAL})\s*[，,、]?\s*是\s*({_VAL})", raw)
    if m:
        return Correction(m.group(1), m.group(2), raw, "not_x_is_y")
    # 说错了，应该是 Y（现值从上下文另取，这里否定项留空标记）
    m = re.search(rf"说错(?:了)?[，,]?\s*应该是\s*({_NUM_C}{_UNIT}|{_NUM_C})", raw)
    if m:
        return Correction("", m.group(1), raw, "said_wrong")
    # X 写成了 Y
    m = re.search(rf"({_VAL})\s*写成(?:了)?\s*({_VAL})", raw)
    if m:
        return Correction(m.group(1), m.group(2), raw, "x_written_as_y")
    return None


def parse_spec(text: str) -> SpecValue:
    """解析规格：含量×装量拆分，单位归一，原文并存。"""
    raw = text.strip()
    result = SpecValue(raw_text=raw)
    # 含量×装量：如 1g×10支 / 0.25g*2ml
    m = re.search(
        rf"({_NUM_C})\s*({_UNIT})\s*[×xX*]\s*({_NUM_C})\s*({_UNIT})", raw
    )
    if m:
        result.content_value = normalize_cn_number(m.group(1))
        result.content_unit = UNIT_NORMALIZE.get(m.group(2), m.group(2))
        result.fill_value = normalize_cn_number(m.group(3))
        result.fill_unit = UNIT_NORMALIZE.get(m.group(4), m.group(4))
        return result
    # 单个含量值
    m = re.search(rf"({_NUM_C})\s*({_UNIT})", raw)
    if m:
        result.content_value = normalize_cn_number(m.group(1))
        result.content_unit = UNIT_NORMALIZE.get(m.group(2), m.group(2))
    return result


def direction_values(text: str) -> tuple[str, str]:
    """返回（现值原文, 应为值原文）；供要素抽取使用。"""
    corr = parse_correction(text)
    if corr:
        return corr.negated, corr.corrected
    return "", ""
