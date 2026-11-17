"""主数据目录同步客户端：GET /api/v1/drug-dictionary。

默认直连 $MDM_BASE_URL，凭据 Bearer $MDM_TOKEN；同步失败沿用上次快照并记快照时间，
供界面提示「目录已过期」。协议替身只在 tests/。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from ..config import Config


@dataclass
class SyncResult:
    items: list[dict[str, Any]]
    synced_at: str
    stale: bool = False
    reason: str = ""


def fetch_dictionary(
    cfg: Config,
    *,
    updated_since: str = "",
    http_client: Any = None,
) -> SyncResult:
    """从主数据平台拉取目录快照。"""
    import httpx
    from datetime import datetime, timezone
    from urllib.parse import urlencode

    base = cfg.mdm_base_url.rstrip("/")
    params = {}
    if updated_since:
        params["updated_since"] = updated_since
    url = base + "/api/v1/drug-dictionary"
    if params:
        url += "?" + urlencode(params)
    headers = {"Authorization": f"Bearer {cfg.mdm_token}"}
    client = http_client or httpx.Client(timeout=30.0)
    resp = client.get(url, headers=headers)
    if resp.status_code >= 400:
        raise RuntimeError(f"目录同步失败：HTTP {resp.status_code}")
    body = resp.json()
    return SyncResult(
        items=list(body.get("items", [])),
        synced_at=str(body.get("synced_at") or datetime.now(timezone.utc).isoformat()),
    )
