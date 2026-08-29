from dykb.douyin import is_douyin_share_url, parse_source_url


def test_parses_video_id() -> None:
    meta = parse_source_url("https://www.douyin.com/video/7123456789012345678")
    assert meta["douyin_id"] == "7123456789012345678"
    assert meta["kind"] == "video"


def test_parses_short_link_without_fetching() -> None:
    meta = parse_source_url("https://v.douyin.com/AbC123xy/")
    assert meta["kind"] == "short"
    assert meta["douyin_id"] == "AbC123xy"


def test_non_douyin_kept_as_external() -> None:
    meta = parse_source_url("https://example.com/watch/1")
    assert meta["kind"] == "external"
    assert meta["douyin_id"] == ""


def test_empty() -> None:
    assert parse_source_url("")["source_url"] == ""


def test_detects_share_hosts() -> None:
    assert is_douyin_share_url("https://v.douyin.com/AbC123xy/")
    assert is_douyin_share_url("https://www.douyin.com/video/1")
    assert is_douyin_share_url("https://v3-web.douyinvod.com/x.mp4")
    assert not is_douyin_share_url("https://files.example.com/talk.srt")

