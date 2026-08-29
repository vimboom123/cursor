from pathlib import Path

from fastapi.testclient import TestClient

from dykb.web import create_app


def test_web_seed_search_ask_and_ingest(tmp_path: Path) -> None:
    app = create_app(tmp_path)
    with TestClient(app) as client:
        home = client.get("/")
        assert home.status_code == 200
        assert "口播库" in home.text
        assert "抖音口播怎么建成知识库" in home.text

        search = client.get("/search", params={"q": "知识卡片"})
        assert search.status_code == 200
        assert "知识卡片" in search.text

        asked = client.get("/ask", params={"q": "抖音视频怎么建立知识库"})
        assert asked.status_code == 200
        assert "口播" in asked.text

        ingest_page = client.get("/ingest")
        assert ingest_page.status_code == 200
        posted = client.post(
            "/ingest",
            data={
                "title": "网页入库测试",
                "transcript": "第一点，网页也可以只贴文案入库。知识卡片是指可检索的句子。",
                "author": "web",
                "source_url": "https://www.douyin.com/video/999",
                "tags": "测试",
                "collection": "网页",
                "notes": "",
            },
            follow_redirects=False,
        )
        assert posted.status_code == 303
        loc = posted.headers["location"]
        assert loc.startswith("/videos/")
        detail = client.get(loc)
        assert detail.status_code == 200
        assert "网页入库测试" in detail.text
        assert "999" in detail.text

        api = client.get("/api/ask", params={"q": "什么是知识卡片"})
        assert api.status_code == 200
        body = api.json()
        assert body["citations"]
