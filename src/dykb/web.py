from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import quote

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from dykb.pipeline import IngestError, ingest
from dykb.qa import ask
from dykb.seed import seed_examples
from dykb.store import Store
from dykb.textutil import format_ts

ROOT = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(ROOT / "templates"))
templates.env.filters["ts"] = format_ts

KIND_LABEL = {
    "point": "观点",
    "step": "步骤",
    "quote": "金句",
    "term": "术语",
    "warning": "注意",
}


def create_app(data_dir: Path) -> FastAPI:
    data_dir = Path(data_dir)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        store = Store(data_dir)
        seed_examples(store)
        app.state.store = store
        try:
            yield
        finally:
            store.close()

    app = FastAPI(title="口播库", lifespan=lifespan)
    app.mount("/static", StaticFiles(directory=str(ROOT / "static")), name="static")

    def store() -> Store:
        return app.state.store

    @app.get("/", response_class=HTMLResponse)
    async def home(request: Request):
        s = store()
        return templates.TemplateResponse(
            request,
            "index.html",
            {
                "stats": s.stats(),
                "videos": s.list_videos(),
                "cards": s.all_cards(24),
                "kind_label": KIND_LABEL,
                "nav": "home",
            },
        )

    @app.get("/ingest", response_class=HTMLResponse)
    async def ingest_page(request: Request, error: str = "", ok: str = ""):
        return templates.TemplateResponse(
            request,
            "ingest.html",
            {
                "nav": "ingest",
                "error": error,
                "ok": ok,
                "collections": store().collections(),
            },
        )

    @app.post("/ingest")
    async def ingest_submit(
        title: str = Form(...),
        transcript: str = Form(""),
        author: str = Form(""),
        source_url: str = Form(""),
        tags: str = Form(""),
        collection: str = Form("默认合集"),
        notes: str = Form(""),
        video: UploadFile | None = File(None),
        transcript_file: UploadFile | None = File(None),
    ):
        s = store()
        text = transcript
        if transcript_file and transcript_file.filename:
            raw = await transcript_file.read()
            text = text or raw.decode("utf-8", errors="replace")
        video_path = None
        if video and video.filename:
            suffix = Path(video.filename).suffix.lower()
            if suffix not in {".mp4", ".mov", ".m4v", ".webm"}:
                return RedirectResponse(
                    "/ingest?error=" + quote("只接受常见视频文件（mp4/mov/webm）"),
                    status_code=303,
                )
            dest = s.data_dir / "uploads"
            dest.mkdir(exist_ok=True)
            video_path = dest / Path(video.filename).name
            video_path.write_bytes(await video.read())
        try:
            record = ingest(
                s,
                title=title,
                transcript=text,
                video_path=video_path,
                author=author,
                source_url=source_url,
                tags=[t.strip() for t in tags.split(",") if t.strip()],
                notes=notes,
                collection=collection,
            )
        except IngestError as exc:
            return RedirectResponse("/ingest?error=" + quote(str(exc)), status_code=303)
        return RedirectResponse(f"/videos/{record.id}", status_code=303)

    @app.get("/videos/{video_id}", response_class=HTMLResponse)
    async def video_page(request: Request, video_id: str):
        s = store()
        video = s.get_video(video_id)
        if not video:
            raise HTTPException(404, "未找到该条口播")
        return templates.TemplateResponse(
            request,
            "video.html",
            {
                "nav": "home",
                "video": video,
                "segments": s.segments_for(video_id),
                "cards": s.cards_for(video_id),
                "kind_label": KIND_LABEL,
            },
        )

    @app.get("/search", response_class=HTMLResponse)
    async def search_page(request: Request, q: str = ""):
        hits = store().search(q) if q.strip() else []
        return templates.TemplateResponse(
            request,
            "search.html",
            {"nav": "search", "q": q, "hits": hits},
        )

    @app.get("/ask", response_class=HTMLResponse)
    async def ask_page(request: Request, q: str = ""):
        answer = ask(store(), q) if q.strip() else None
        return templates.TemplateResponse(
            request,
            "ask.html",
            {"nav": "ask", "q": q, "answer": answer},
        )

    @app.get("/api/search")
    async def api_search(q: str, limit: int = 12):
        hits = store().search(q, limit=limit)
        return JSONResponse([h.model_dump() for h in hits])

    @app.get("/api/ask")
    async def api_ask(q: str):
        return JSONResponse(ask(store(), q).model_dump())

    @app.get("/api/stats")
    async def api_stats():
        return JSONResponse(store().stats())

    return app


def serve(data_dir: Path, host: str = "127.0.0.1", port: int = 8000) -> None:
    import uvicorn

    uvicorn.run(create_app(data_dir), host=host, port=port, log_level="info")
