from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from awcollector.models import Permit


class PermitError(RuntimeError):
    """许可不存在、过期或不在授权范围内。"""


def load_permit(path: str | Path) -> Permit:
    raw = Path(path).read_text(encoding="utf-8")
    return Permit.model_validate(json.loads(raw))


def assert_permit_active(permit: Permit, now: datetime | None = None) -> None:
    current = now or datetime.now(timezone.utc)
    expires = permit.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    if current > expires:
        raise PermitError(f"许可 {permit.permit_id} 已于 {permit.expires_at.isoformat()} 过期")


def assert_url_allowed(permit: Permit, url: str) -> None:
    if url.startswith("file:"):
        candidate = url
    else:
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            raise PermitError(f"无法解析待采集地址: {url}")
        candidate = url
    if not any(candidate.startswith(prefix) for prefix in permit.allowed_url_prefixes):
        raise PermitError(
            f"地址不在许可范围: {url}；允许前缀: {permit.allowed_url_prefixes}"
        )


def assert_task_allowed(permit: Permit, allow_write: bool) -> None:
    if allow_write and permit.read_only:
        raise PermitError("许可为只读，禁止回写或改数类操作")
