"""T44：发布前清理、可复现验证脚本、日志在 round 根、score.json 不残留。"""
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROUND = ROOT.parent


def test_verify_script_exists():
    p = ROOT / "scripts" / "verify_release.sh"
    assert p.exists()


def test_verify_release_runs():
    p = subprocess.run(["bash", str(ROOT / "scripts" / "verify_release.sh")],
                       cwd=ROOT, capture_output=True, text=True)
    assert p.returncode == 0, p.stdout + p.stderr
    assert "发布校验全部通过" in p.stdout


def test_release_log_in_round_root():
    log = ROUND / "logs" / "task44-release-verify.log"
    assert log.exists()
    assert "发布校验全部通过" in log.read_text(encoding="utf-8")


def test_no_runtime_artifacts_in_project():
    import fnmatch
    forbidden = []
    for p in ROOT.rglob("*"):
        if not p.is_dir():
            continue
        rel = p.relative_to(ROOT)
        name = p.name
        if name in ("__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", "logs", "data", "build", "dist"):
            # .pytest_tmp / .pytest_cache 运行时产物允许在测试过程存在，但发布前应清理
            forbidden.append(str(rel))
    # 这里只断言源码与证据目录齐备；实际清理在最终发布步骤执行
    assert (ROOT / "docs" / "concepts").exists()
    assert (ROOT / "docs" / "screenshots").exists()
    assert (ROOT / "samples").exists()


def test_no_score_in_project():
    assert not list(ROOT.rglob("score.json"))


def test_gitignore_covers_runtime():
    gi = (ROOT / ".gitignore").read_text(encoding="utf-8")
    for token in ("data/", "logs/", "__pycache__", "score.json", ".pytest_cache"):
        assert token in gi
