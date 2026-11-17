"""T14：运维 CLI 四子命令（selftest / doctor / sync-dictionary / export）。

覆盖：子命令注册、selftest 打印可核对条目、doctor 自检清单、
export 产出含依据原话与毫秒区间的 BOM CSV、无命令打印帮助、sync 走正式协议路径。
"""
from __future__ import annotations

from dmchange import cli


def test_four_subcommands_registered():
    p = cli.build_parser()
    for name, fn in (
        ("selftest", cli.selftest),
        ("doctor", cli.doctor),
        ("sync-dictionary", cli.sync_dictionary),
        ("export", cli.export),
    ):
        args = p.parse_args([name])
        assert args.func is fn


def test_no_command_prints_help(capsys):
    assert cli.main([]) == 0
    out = capsys.readouterr().out
    assert "usage:" in out
    assert "selftest" in out


def test_selftest_prints_item(capsys):
    rc = cli.main(["selftest", "--case", "samples/scenarios/case_001.json"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "可核对条目行" in out
    assert "药品码:" in out and "字段名:" in out
    assert "现值:" in out and "应为值:" in out
    assert "依据:" in out and "ms]" in out


def test_doctor_lists_checks(capsys):
    rc = cli.main(["doctor"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "自检清单" in out
    assert "依赖包" in out and "环境变量" in out
    for key in ("MDM_BASE_URL", "MODEL_API_KEY", "ASR_MODE"):
        assert key in out


def test_sync_dictionary_uses_formal_path(capsys, monkeypatch):
    # 凭据位注入，避免 ConfigError；命令本身不联网，只打印正式协议路径。
    for k, v in {
        "MDM_BASE_URL": "https://mdm.example.internal",
        "MDM_TOKEN": "dummy-for-cli-test",
        "MODEL_BASE_URL": "https://model.example.internal/v1",
        "MODEL_API_KEY": "dummy-for-cli-test",
        "MODEL_NAME": "test-model",
        "MODEL_TIMEOUT": "30",
        "ASR_MODE": "local",
    }.items():
        monkeypatch.setenv(k, v)
    rc = cli.main(["sync-dictionary"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "/api/v1/drug-dictionary" in out


def test_export_csv_has_evidence_and_ms(tmp_path, capsys):
    out = tmp_path / "out.csv"
    rc = cli.main(["export", "--out", str(out)])
    assert rc == 0
    assert "已导出" in capsys.readouterr().out
    text = out.read_text(encoding="utf-8")
    assert text.startswith("\ufeff"), "CSV 需带 UTF-8 BOM"
    header = text.splitlines()[0]
    for col in ("药品码", "字段名", "依据原话", "起始毫秒", "结束毫秒"):
        assert col in header
    assert len(text.splitlines()) >= 2


def test_readme_within_line_cap():
    root = cli._project_root()
    lines = (root / "README.md").read_text(encoding="utf-8").splitlines()
    assert len(lines) <= 350
