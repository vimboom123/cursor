"""只拉取用户自己托管的文案/媒体直链。拒绝抖音域名和内网地址。"""

from __future__ import annotations

import ipaddress
import socket
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

from dykb.douyin import is_douyin_share_url
from dykb.errors import DouyinLinkError, FetchError

TEXT_EXT = {".txt", ".srt", ".vtt"}
MEDIA_EXT = {".mp4", ".mov", ".m4v", ".webm", ".wav", ".m4a", ".mp3"}
TEXT_TYPES = {
    "text/plain",
    "text/srt",
    "text/vtt",
    "application/x-subrip",
}
MEDIA_TYPES = {
    "video/mp4",
    "video/quicktime",
    "video/webm",
    "audio/mpeg",
    "audio/mp4",
    "audio/wav",
    "audio/x-wav",
    "audio/webm",
}
MAX_TEXT = 2_000_000
MAX_MEDIA = 80_000_000


@dataclass
class FetchedFile:
    kind: str  # transcript | media
    path: Path
    text: str = ""


def fetch_user_file(
    url: str,
    dest_dir: Path,
    *,
    allow_private: bool = False,
) -> FetchedFile:
    raw = (url or "").strip()
    if not raw:
        raise FetchError("文件链接为空")
    if is_douyin_share_url(raw):
        raise DouyinLinkError(raw)
    _assert_public_http_url(raw, allow_private=allow_private)

    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    opener = build_opener(_GuardedRedirects(allow_private=allow_private))
    request = Request(
        raw,
        headers={"User-Agent": "dykb/0.1 (authorized self-hosted ingest)"},
        method="GET",
    )
    try:
        with opener.open(request, timeout=20) as resp:
            final_url = resp.geturl()
            _assert_public_http_url(final_url, allow_private=allow_private)
            content_type = (resp.headers.get("Content-Type") or "").split(";")[0].strip().lower()
            data = resp.read(MAX_MEDIA + 1)
    except DouyinLinkError:
        raise
    except FetchError:
        raise
    except Exception as exc:
        raise FetchError(f"无法读取文件链接：{exc}") from exc

    if len(data) > MAX_MEDIA:
        raise FetchError("文件过大")
    kind = _classify(final_url, content_type, data)
    suffix = Path(urlparse(final_url).path).suffix.lower() or (".txt" if kind == "transcript" else ".mp4")
    path = dest_dir / f"fetched{suffix}"
    path.write_bytes(data)
    if kind == "transcript":
        if len(data) > MAX_TEXT:
            raise FetchError("文案文件过大")
        text = data.decode("utf-8", errors="replace").strip()
        if not text:
            raise FetchError("文件链接里没有文本")
        return FetchedFile(kind="transcript", path=path, text=text)
    return FetchedFile(kind="media", path=path)


def _classify(url: str, content_type: str, data: bytes) -> str:
    suffix = Path(urlparse(url).path).suffix.lower()
    if suffix in TEXT_EXT:
        return "transcript"
    if suffix in MEDIA_EXT:
        return "media"
    if content_type in TEXT_TYPES and not data[:64].lstrip().lower().startswith(b"<!doctype html") and not data[:64].lstrip().lower().startswith(b"<html"):
        # octet-stream with HTML is still a page
        if b"<html" in data[:200].lower():
            raise FetchError("这是网页，不是口播文件。请用 .srt / .txt / .mp4 直链")
        return "transcript"
    if content_type in MEDIA_TYPES:
        return "media"
    raise FetchError("这不是可入库的文案或视频直链。请用 .srt / .txt / .mp4，不要贴抖音分享页")


def _assert_public_http_url(url: str, *, allow_private: bool) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise FetchError("只接受 http/https 文件链接")
    if is_douyin_share_url(url):
        raise DouyinLinkError(url)
    host = parsed.hostname or ""
    if not host:
        raise FetchError("链接没有主机名")
    if allow_private:
        return
    try:
        infos = socket.getaddrinfo(host, parsed.port or 80, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise FetchError(f"无法解析主机：{host}") from exc
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if _is_private(ip):
            raise FetchError("拒绝访问内网或本机地址")


def _is_private(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    return bool(
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


class _GuardedRedirects(HTTPRedirectHandler):
    def __init__(self, allow_private: bool = False) -> None:
        super().__init__()
        self.allow_private = allow_private

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
        _assert_public_http_url(newurl, allow_private=self.allow_private)
        return super().redirect_request(req, fp, code, msg, headers, newurl)
