"""单一 ModelGateway：OpenAI-compatible 结构化契约、超时/错误分类、审计元数据。

业务层只调用本模块，不 import 厂商 SDK。配置全部来自 config.py。
错误分类：timeout / http_4xx / http_5xx / schema_invalid / parse_error。
本地协议替身只在 tests/（通过 http_client 注入）。
"""
from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from ..config import Config
from ..domain.errors import Http4xx, Http5xx, ParseError, SchemaInvalid, TimeoutError_
from .schema import SYSTEM_PROMPT, validate_extraction


@dataclass
class CallMeta:
    model: str
    duration_ms: int
    request_bytes: int
    timed_out: bool
    request_id: str
    error_class: Optional[str] = None


@dataclass
class GatewayResponse:
    raw: dict[str, Any]
    meta: CallMeta


class ModelGateway:
    """单一模型网关；可替换（http_client 注入协议替身，仅测试）。"""

    def __init__(self, cfg: Config, *, http_client: Any = None, on_meta=None):
        self.cfg = cfg
        self._client = http_client
        self.on_meta = on_meta or (lambda _: None)
        self.call_count = 0

    def _build_request(self, user_prompt: str) -> dict[str, Any]:
        return {
            "model": self.cfg.model_name,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            "response_format": {"type": "json_object"},
        }

    def call(self, user_prompt: str, *, validate: bool = True) -> GatewayResponse:
        """POST /v1/chat/completions，解析 + Schema 校验 + 审计元数据。"""
        import httpx

        body = self._build_request(user_prompt)
        raw_body = json.dumps(body, ensure_ascii=False)
        url = self.cfg.model_base_url.rstrip("/") + "/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.cfg.model_api_key}",
            "Content-Type": "application/json",
        }
        req_id = uuid.uuid4().hex
        t0 = time.time()
        self.call_count += 1
        timed_out = False
        error_class = None
        try:
            client = self._client or httpx.Client(timeout=self.cfg.model_timeout)
            resp = client.post(url, json=body, headers=headers)
        except Exception as exc:  # httpx.TimeoutException 等
            timed_out = "timeout" in type(exc).__name__.lower() or "timed out" in str(exc).lower()
            error_class = "timeout" if timed_out else "parse_error"
            meta = CallMeta(self.cfg.model_name, int((time.time() - t0) * 1000),
                            len(raw_body.encode()), timed_out, req_id, error_class)
            self.on_meta(meta)
            if timed_out:
                raise TimeoutError_(f"模型调用超时（>{self.cfg.model_timeout}s）") from exc
            raise ParseError(f"模型调用失败：{exc}") from exc

        duration = int((time.time() - t0) * 1000)
        if resp.status_code >= 500:
            error_class = "http_5xx"
            self.on_meta(CallMeta(self.cfg.model_name, duration, len(raw_body.encode()), False, req_id, error_class))
            raise Http5xx(f"模型服务 5xx：{resp.status_code}")
        if resp.status_code >= 400:
            error_class = "http_4xx"
            self.on_meta(CallMeta(self.cfg.model_name, duration, len(raw_body.encode()), False, req_id, error_class))
            raise Http4xx(f"模型服务 4xx：{resp.status_code}")
        try:
            payload = resp.json()
            content = payload["choices"][0]["message"]["content"]
            parsed = json.loads(content) if isinstance(content, str) else content
        except (KeyError, IndexError, ValueError, TypeError) as exc:
            error_class = "parse_error"
            self.on_meta(CallMeta(self.cfg.model_name, duration, len(raw_body.encode()), False, req_id, error_class))
            raise ParseError(f"模型返回不可解析：{exc}") from exc

        if validate:
            try:
                validate_extraction(parsed)
            except SchemaInvalid:
                error_class = "schema_invalid"
                self.on_meta(CallMeta(self.cfg.model_name, duration, len(raw_body.encode()), False, req_id, error_class))
                raise
        self.on_meta(CallMeta(self.cfg.model_name, duration, len(raw_body.encode()), False, req_id, None))
        return GatewayResponse(parsed, CallMeta(
            self.cfg.model_name, duration, len(raw_body.encode()), False, req_id, None,
        ))
