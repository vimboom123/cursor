from dykb.chunk import segments_from_plain, segments_from_timed
from dykb.textutil import chunk_sentences, fts_query, parse_srt, split_sentences


def test_split_and_chunk_chinese() -> None:
    text = "先入库。再切片。然后检索。"
    sents = split_sentences(text)
    assert sents == ["先入库。", "再切片。", "然后检索。"]
    chunks = chunk_sentences(sents, max_chars=6)
    assert chunks[0] == "先入库。"


def test_plain_segments_get_timestamps() -> None:
    segs = segments_from_plain("v1", "第一句。第二句。", duration_ms=10000)
    assert len(segs) >= 1
    assert segs[0].start_ms == 0
    assert segs[-1].end_ms == 10000


def test_parse_srt_and_timed_segments() -> None:
    srt = """1
00:00:00,000 --> 00:00:01,200
你好世界。

2
00:00:01,200 --> 00:00:03,000
第二句。
"""
    items = parse_srt(srt)
    assert items[0] == (0, 1200, "你好世界。")
    segs = segments_from_timed("v1", items)
    assert segs[1].start_ms == 1200
    assert segs[1].text == "第二句。"


def test_fts_query_quotes_tokens() -> None:
    q = fts_query("知识库")
    assert '"' in q
