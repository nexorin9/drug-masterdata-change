"""T39：替身只在 tests/、演示产物带标记、默认配置缺失报错。"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_check_release_paths():
    import os
    env = dict(os.environ); env["PYTHONPATH"] = str(ROOT / "src")
    p = subprocess.run([sys.executable, str(ROOT / "scripts" / "check_release_paths.py")],
                       cwd=ROOT, env=env, capture_output=True, text=True)
    assert p.returncode == 0, p.stdout + p.stderr


def test_no_localhost_in_src():
    found = []
    for p in (ROOT / "src").rglob("*.py"):
        for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            if ("localhost" in line or "127.0.0.1" in line) and not line.strip().startswith("#"):
                found.append(f"{p}:{i}")
    assert found == []


def test_demo_export_marked():
    import os
    env = dict(os.environ); env["PYTHONPATH"] = str(ROOT / "src")
    out = ROOT / ".pytest_tmp" / "demo_out.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    p = subprocess.run([sys.executable, "-m", "dmchange", "export", "--out", str(out)],
                       cwd=ROOT, env=env, capture_output=True, text=True)
    assert p.returncode == 0, p.stderr
    assert "演示数据" in out.read_text(encoding="utf-8")


def test_default_config_missing_errors():
    from dmchange.config import load_config, ConfigError
    try:
        load_config({})
        raise AssertionError("空配置应报错")
    except ConfigError:
        pass
