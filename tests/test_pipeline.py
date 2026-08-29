from pathlib import Path

from dykb.pipeline import IngestError, ingest
from dykb.qa import ask
from dykb.seed import seed_examples
from dykb.store import Store
import pytest


def test_ingest_transcript_search_and_ask(tmp_path: Path) -> None:
    store = Store(tmp_path)
    record = ingest(
        store,
        title="测试口播",
        transcript="知识卡片是指可独立阅读的观点。第一点，只入库已授权素材。记住：先检索再追问。",
        author="tester",
        source_url="https://www.douyin.com/video/111",
        tags=["方法"],
        collection="实验",
    )
    assert record.douyin_id == "111"
    assert store.cards_for(record.id)
    hits = store.search("知识卡片")
    assert hits
    assert any("知识卡片" in h.text for h in hits)
    answer = ask(store, "什么是知识卡片")
    assert "知识卡片" in answer.text
    assert answer.citations
    store.close()


def test_ingest_requires_text(tmp_path: Path) -> None:
    store = Store(tmp_path)
    with pytest.raises(IngestError):
        ingest(store, title="空")
    store.close()


def test_seed_is_idempotent(tmp_path: Path) -> None:
    store = Store(tmp_path)
    assert seed_examples(store) == 3
    assert seed_examples(store) == 0
    assert store.stats()["videos"] == 3
    hits = store.search("复盘")
    assert hits
    store.close()


def test_duplicate_video_file_skipped(tmp_path: Path) -> None:
    store = Store(tmp_path)
    video = tmp_path / "clip.mp4"
    video.write_bytes(b"fake-mp4-bytes")
    first = ingest(store, title="一次", transcript="只入库一次。", video_path=video)
    second = ingest(store, title="二次", transcript="重复文件。", video_path=video)
    assert first.id == second.id
    assert store.stats()["videos"] == 1
    store.close()
