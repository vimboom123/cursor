"""解析抖音分享链接，只提取可引用的编号，不下载、不跟跳。"""

from __future__ import annotations

import re
from urllib.parse import urlparse

_VIDEO_ID = re.compile(r"/(?:video|note|share/video)/(\d+)")
_SHORT = re.compile(r"^[A-Za-z0-9._-]+$")

DOUYIN_HOST_SUFFIXES = (
    "douyin.com",
    "iesdouyin.com",
    "douyinvod.com",
    "byteimg.com",
    "bytedance.com",
    "tiktok.com",
    "tiktokcdn.com",
    "tiktokv.com",
)


def hostname(url_or_host: str) -> str:
    raw = (url_or_host or "").strip()
    if "://" in raw:
        return (urlparse(raw).hostname or "").lower()
    return raw.split("/")[0].split(":")[0].lower()


def is_douyin_host(host: str) -> bool:
    host = (host or "").lower()
    return any(host == suffix or host.endswith("." + suffix) for suffix in DOUYIN_HOST_SUFFIXES)


def is_douyin_share_url(url: str) -> bool:
    host = hostname(url)
    return bool(host) and is_douyin_host(host)


def parse_source_url(url: str) -> dict[str, str]:
    """把创作者自己粘贴的分享链接拆成引用字段。

    只做本地字符串解析。不会请求抖音服务器，也不会去水印下载。
    """
    raw = (url or "").strip()
    if not raw:
        return {"source_url": "", "douyin_id": "", "kind": ""}

    if not re.match(r"^https?://", raw, re.I):
        raw = "https://" + raw

    parsed = urlparse(raw)
    host = hostname(raw)
    path = parsed.path or ""

    if not is_douyin_host(host):
        return {"source_url": url.strip(), "douyin_id": "", "kind": "external"}

    match = _VIDEO_ID.search(path)
    if match:
        return {
            "source_url": url.strip(),
            "douyin_id": match.group(1),
            "kind": "video",
        }

    if host.startswith("v.") or host == "v.douyin.com":
        slug = path.strip("/").split("/")[0] if path.strip("/") else ""
        if slug and _SHORT.match(slug):
            return {
                "source_url": url.strip(),
                "douyin_id": slug,
                "kind": "short",
            }

    return {"source_url": url.strip(), "douyin_id": "", "kind": "page"}
