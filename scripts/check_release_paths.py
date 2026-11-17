"""T39：扫描 src/ 中的替身痕迹与硬编码地址，输出逐项断言结果。

白名单：注释行中说明性的 127.0.0.1（留痕）不算命中，但代码字符串中的算。
"""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"


def scan() -> dict:
    problems = []
    checked = 0
    whitelist_hits = []
    for p in SRC.rglob("*.py"):
        checked += 1
        text = p.read_text(encoding="utf-8")
        # 逐行：跳过纯注释行的说明性地址（白名单留痕）
        for i, line in enumerate(text.splitlines(), 1):
            if re.search(r"localhost|127\.0\.0\.1", line, re.I):
                if line.strip().startswith("#"):
                    whitelist_hits.append(f"{p.relative_to(ROOT)}:{i}")
                    continue
                problems.append(f"硬编码本地地址 {p.relative_to(ROOT)}:{i}")
        # AST：检查 src 是否 import tests 包（替身反向依赖）
        try:
            tree = ast.parse(text)
        except SyntaxError as exc:
            problems.append(f"语法错误 {p.relative_to(ROOT)}: {exc}")
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("tests"):
                problems.append(f"产品代码引用测试替身 {p.relative_to(ROOT)}")
    return {"checked_files": checked, "problems": problems, "whitelist": whitelist_hits}


if __name__ == "__main__":
    r = scan()
    print(f"扫描 {r['checked_files']} 个源文件")
    print(f"白名单命中 {len(r['whitelist'])} 处（注释说明，已留痕）")
    if r["problems"]:
        for p in r["problems"]:
            print("  [FAIL]", p)
        sys.exit(1)
    print("  [OK] 默认路径无本地替身地址，产品代码不引用测试替身")
    sys.exit(0)
