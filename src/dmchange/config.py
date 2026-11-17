"""配置加载：九个环境变量，零硬编码密钥。

所有外部端点只从环境变量读取；缺省不回落到本地替身地址，而是给出明确报错。
演示替身只在 tests/ 数据层，产品配置面永远指向真实端点形态。
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Mapping, Optional

# 九个凭据/端点位（变量名集中，便于审计与文档对齐）
ENV_KEYS = (
    "MDM_BASE_URL",
    "MDM_TOKEN",
    "MODEL_BASE_URL",
    "MODEL_API_KEY",
    "MODEL_NAME",
    "MODEL_TIMEOUT",
    "ASR_MODE",
    "ASR_BASE_URL",
    "ASR_API_KEY",
)

# 出站路径必须有值的六项核心凭据/端点；ASR_MODE 有默认值 local，
# ASR_BASE_URL / ASR_API_KEY 仅在 openai-compatible 模式下强制。
CORE_REQUIRED = (
    "MDM_BASE_URL", "MDM_TOKEN", "MODEL_BASE_URL",
    "MODEL_API_KEY", "MODEL_NAME", "MODEL_TIMEOUT",
)


class ConfigError(RuntimeError):
    """配置缺失或非法。"""


@dataclass(frozen=True)
class Config:
    mdm_base_url: str
    mdm_token: str
    model_base_url: str
    model_api_key: str
    model_name: str
    model_timeout: float
    asr_mode: str
    asr_base_url: str
    asr_api_key: str

    def masked(self) -> dict[str, object]:
        """脱敏视图，供日志与运行摘要使用。"""
        return {
            "mdm_base_url": self.mdm_base_url or "(unset)",
            "mdm_token": _mask(self.mdm_token),
            "model_base_url": self.model_base_url or "(unset)",
            "model_api_key": _mask(self.model_api_key),
            "model_name": self.model_name or "(unset)",
            "model_timeout": self.model_timeout,
            "asr_mode": self.asr_mode,
            "asr_base_url": self.asr_base_url or "(unset)",
            "asr_api_key": _mask(self.asr_api_key),
        }


def _mask(value: str) -> str:
    if not value:
        return "(unset)"
    if len(value) <= 4:
        return "*" * len(value)
    return value[:2] + "*" * (len(value) - 4) + value[-2:]


def load_config(
    env: Optional[Mapping[str, str]] = None,
    *,
    require: Optional[tuple[str, ...]] = None,
) -> Config:
    """从环境变量（默认 os.environ）读取配置。

    Args:
        env: 可注入的映射，便于测试；None 时用 os.environ。
        require: 需要强制非空的环境变量名元组。默认强制六项核心凭据/端点，
            保证「缺项给明确报错」；ASR_BASE_URL/ASR_API_KEY 仅在兼容模式下强制。
            离线 selftest 可传 () 以允许凭据位为空，但产品出站路径必须强制。
    """
    source = os.environ if env is None else env
    values = {k: (source.get(k, "") or "").strip() for k in ENV_KEYS}

    keys_to_require = CORE_REQUIRED if require is None else require
    missing = [k for k in keys_to_require if not values.get(k)]
    if missing:
        raise ConfigError(
            "缺少必需的环境变量：" + "、".join(missing) + "。请在 .env.example 中查看配置位说明，"
            "端点必须指向真实服务地址，不得回落到本地替身。"
        )

    timeout_raw = values["MODEL_TIMEOUT"] or "30"
    try:
        timeout = float(timeout_raw)
    except ValueError as exc:
        raise ConfigError(f"MODEL_TIMEOUT 必须为数值，实际为 {timeout_raw!r}") from exc
    if timeout <= 0:
        raise ConfigError("MODEL_TIMEOUT 必须大于 0")

    asr_mode = values["ASR_MODE"] or "local"
    if asr_mode not in ("local", "openai-compatible"):
        raise ConfigError(
            f"ASR_MODE 取值非法：{asr_mode!r}，允许 local / openai-compatible"
        )
    if asr_mode == "openai-compatible" and not values["ASR_BASE_URL"]:
        raise ConfigError("ASR_MODE=openai-compatible 时必须设置 ASR_BASE_URL")

    return Config(
        mdm_base_url=values["MDM_BASE_URL"],
        mdm_token=values["MDM_TOKEN"],
        model_base_url=values["MODEL_BASE_URL"],
        model_api_key=values["MODEL_API_KEY"],
        model_name=values["MODEL_NAME"],
        model_timeout=timeout,
        asr_mode=asr_mode,
        asr_base_url=values["ASR_BASE_URL"],
        asr_api_key=values["ASR_API_KEY"],
    )


# 模块级单例缓存：配置一旦载入不再随环境漂移；测试用 reload_config 显式刷新
_CONFIG: Optional[Config] = None


def get_config(**kwargs) -> Config:
    global _CONFIG
    if _CONFIG is None:
        _CONFIG = load_config(**kwargs)
    return _CONFIG


def reload_config(**kwargs) -> Config:
    global _CONFIG
    _CONFIG = load_config(**kwargs)
    return _CONFIG
