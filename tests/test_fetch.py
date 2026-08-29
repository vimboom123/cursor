from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

import pytest

from dykb.errors import DouyinLinkError, FetchError
from dykb.fetch import fetch_user_file


def _serve(root: Path) -> ThreadingHTTPServer:
    directory = str(root)

    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=directory, **kwargs)

        def log_message(self, format: str, *args: object) -> None:
            return

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    return httpd


def test_douyin_share_is_refused_without_network(tmp_path: Path) -> None:
    with pytest.raises(DouyinLinkError) as exc:
        fetch_user_file("https://v.douyin.com/AbC123xy/", tmp_path)
    assert "拿不到口播" in str(exc.value)


def test_douyin_vod_is_refused(tmp_path: Path) -> None:
    with pytest.raises(DouyinLinkError):
        fetch_user_file("https://v3-web.douyinvod.com/foo.mp4", tmp_path)


def test_loopback_blocked_by_default(tmp_path: Path) -> None:
    with pytest.raises(FetchError) as exc:
        fetch_user_file("http://127.0.0.1:9/talk.srt", tmp_path)
    assert "内网" in str(exc.value)


def test_fetches_self_hosted_srt(tmp_path: Path) -> None:
    root = tmp_path / "www"
    root.mkdir()
    (root / "talk.srt").write_text(
        "00:00:00,000 --> 00:00:01,000\n知识卡片是指可检索的句子。\n",
        encoding="utf-8",
    )
    httpd = _serve(root)
    try:
        url = f"http://127.0.0.1:{httpd.server_address[1]}/talk.srt"
        fetched = fetch_user_file(url, tmp_path / "out", allow_private=True)
        assert fetched.kind == "transcript"
        assert "知识卡片" in fetched.text
    finally:
        httpd.shutdown()


def test_html_page_is_not_transcript(tmp_path: Path) -> None:
    root = tmp_path / "www"
    root.mkdir()
    (root / "page.html").write_text("<html><body>not a script</body></html>", encoding="utf-8")
    httpd = _serve(root)
    try:
        url = f"http://127.0.0.1:{httpd.server_address[1]}/page.html"
        with pytest.raises(FetchError) as exc:
            fetch_user_file(url, tmp_path / "out", allow_private=True)
        assert "直链" in str(exc.value) or "网页" in str(exc.value)
    finally:
        httpd.shutdown()


def test_ingest_uses_self_hosted_txt(tmp_path: Path) -> None:
    from dykb.pipeline import ingest
    from dykb.store import Store

    root = tmp_path / "www"
    root.mkdir()
    (root / "talk.txt").write_text(
        "第一点，文件直链可以入库。知识卡片是指可检索的句子。\n",
        encoding="utf-8",
    )
    httpd = _serve(root)
    store = Store(tmp_path / "kb")
    try:
        url = f"http://127.0.0.1:{httpd.server_address[1]}/talk.txt"
        record = ingest(
            store,
            title="直链口播",
            file_url=url,
            allow_private_urls=True,
        )
        assert store.segments_for(record.id)
        assert any("直链" in s.text for s in store.segments_for(record.id))
    finally:
        store.close()
        httpd.shutdown()
