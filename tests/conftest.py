"""共享 pytest fixtures：内存库、配置注入、协议替身工厂、Qt 离屏 app。"""
from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

from dmchange.ledger.db import connect, init_db


@pytest.fixture(scope="module")
def qapp():
    """离屏 QApplication，供 UI 测试复用；套用设计令牌，渲染结果与真实运行一致。"""
    try:
        from PySide6.QtWidgets import QApplication
    except ImportError:
        pytest.skip("PySide6 不可用")
    app = QApplication.instance() or QApplication([])
    from dmchange.ui.theme import apply_theme
    apply_theme(app, dark=False)
    yield app


@pytest.fixture()
def conn():
    c = connect(None)
    init_db(c)
    yield c
    c.close()


@pytest.fixture()
def full_env():
    return {
        "MDM_BASE_URL": "https://mdm.example.internal",
        "MDM_TOKEN": "mdm-secret-token-0001",
        "MODEL_BASE_URL": "https://llm.example.internal",
        "MODEL_API_KEY": "sk-model-secret-0002",
        "MODEL_NAME": "hospital-qwen",
        "MODEL_TIMEOUT": "30",
        "ASR_MODE": "local",
        "ASR_BASE_URL": "",
        "ASR_API_KEY": "",
    }
