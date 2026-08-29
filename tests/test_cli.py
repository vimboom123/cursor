from pathlib import Path

from dykb.cli import main
from dykb.store import Store


def test_cli_seed_search_ask(tmp_path: Path, capsys) -> None:
    data = str(tmp_path)
    assert main(["--data", data, "init"]) == 0
    assert main(["--data", data, "seed"]) == 0
    assert main(["--data", data, "search", "知识卡片"]) == 0
    out = capsys.readouterr().out
    assert "知识卡片" in out
    assert main(["--data", data, "ask", "抖音视频怎么建立知识库"]) == 0
    assert main(["--data", data, "list"]) == 0
    listed = capsys.readouterr().out
    assert "口播" in listed or "复盘" in listed
    store = Store(tmp_path)
    vid = store.list_videos()[0].id
    store.close()
    assert main(["--data", data, "show", vid]) == 0


def test_cli_ingest_from_file(tmp_path: Path) -> None:
    data = str(tmp_path)
    transcript = Path(__file__).resolve().parents[1] / "fixtures" / "sample.txt"
    assert (
        main(
            [
                "--data",
                data,
                "ingest",
                "--title",
                "夹具口播",
                "--transcript",
                str(transcript),
                "--url",
                "https://v.douyin.com/Hello12/",
            ]
        )
        == 0
    )
    store = Store(tmp_path)
    video = store.list_videos()[0]
    assert video.douyin_id == "Hello12"
    store.close()
