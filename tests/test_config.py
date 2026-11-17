"""T2：九个环境变量读取与缺项报错，零硬编码密钥。"""
import pytest

from dmchange.config import ENV_KEYS, ConfigError, load_config


def test_load_all_nine(full_env):
    cfg = load_config(full_env)
    assert cfg.mdm_base_url == full_env["MDM_BASE_URL"]
    assert cfg.mdm_token == full_env["MDM_TOKEN"]
    assert cfg.model_name == full_env["MODEL_NAME"]
    assert cfg.model_timeout == 30.0
    assert cfg.asr_mode == "local"
    assert len(ENV_KEYS) == 9


def test_missing_reports_key(full_env):
    env = dict(full_env)
    del env["MDM_TOKEN"]
    with pytest.raises(ConfigError) as e:
        load_config(env)
    assert "MDM_TOKEN" in str(e.value)


def test_subset_require(full_env):
    """离线 selftest 可只强制部分键。"""
    env = {k: full_env[k] for k in ("MDM_BASE_URL", "MODEL_BASE_URL")}
    cfg = load_config(env, require=("MDM_BASE_URL", "MODEL_BASE_URL"))
    assert cfg.mdm_base_url == full_env["MDM_BASE_URL"]


def test_bad_timeout(full_env):
    env = dict(full_env)
    env["MODEL_TIMEOUT"] = "not-a-number"
    with pytest.raises(ConfigError) as e:
        load_config(env)
    assert "MODEL_TIMEOUT" in str(e.value)


def test_bad_asr_mode(full_env):
    env = dict(full_env)
    env["ASR_MODE"] = "unknown"
    with pytest.raises(ConfigError):
        load_config(env)


def test_no_hardcoded_secret_literal():
    """config.py 不含任何形如 sk-/Bearer 具体串的硬编码密钥。"""
    import inspect
    from dmchange import config

    src = inspect.getsource(config)
    assert "sk-" not in src
    assert "Bearer " not in src
