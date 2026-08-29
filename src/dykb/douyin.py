"""解析抖音分享链接，只提取可引用的编号，不下载、不跟跳。"""

from __future__ import annotations

import re
from urllib.parse import urlparse

_VIDEO_ID = re.compile(r"/(?:video|note|share/video)/(\d+)")
_SHORT = re.compile(r"^[A-Za-z0-9._-]+$")


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
    host = (parsed.netloc or "").lower()
    path = parsed.path or ""

    allowed = (
        "douyin.com",
        "iesdouyin.com",
        "douyinvod.com",
    )
    if not any(host == d or host.endswith("." + d) for d in allowed):
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
