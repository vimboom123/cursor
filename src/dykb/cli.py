from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from dykb.errors import IngestError
from dykb.pipeline import ingest
from dykb.qa import ask
from dykb.seed import seed_examples
from dykb.store import Store
from dykb.textutil import format_ts


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="dykb",
        description="口播库：把已授权的抖音短视频建成可检索知识库",
    )
    parser.add_argument(
        "--data",
        default="data",
        help="知识库目录（默认 ./data）",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("init", help="初始化空知识库")

    p_seed = sub.add_parser("seed", help="写入三条方法示例口播")
    p_seed.add_argument("--force", action="store_true")

    p_ing = sub.add_parser("ingest", help="入库一条已授权视频或口播文案")
    p_ing.add_argument("video", nargs="?", help="本地视频文件（自己导出/保存的）")
    p_ing.add_argument("--title", required=True)
    p_ing.add_argument("--transcript", help="口播稿或 .srt 文件路径")
    p_ing.add_argument("--text", help="直接传入口播文本")
    p_ing.add_argument("--author", default="")
    p_ing.add_argument("--url", default="", help="仅作引用的抖音分享链接，不会下载")
    p_ing.add_argument(
        "--from-url",
        dest="file_url",
        default="",
        help="你自己托管的 .srt/.txt/.mp4 直链；拒绝抖音分享链接",
    )
    p_ing.add_argument("--tags", default="", help="逗号分隔")
    p_ing.add_argument("--collection", default="默认合集")
    p_ing.add_argument("--notes", default="")

    p_search = sub.add_parser("search", help="检索知识库")
    p_search.add_argument("query")
    p_search.add_argument("--limit", type=int, default=8)

    p_ask = sub.add_parser("ask", help="按口播原句追问")
    p_ask.add_argument("question")

    sub.add_parser("list", help="列出已入库视频")

    p_show = sub.add_parser("show", help="查看一条视频的切片和卡片")
    p_show.add_argument("video_id")

    p_serve = sub.add_parser("serve", help="打开本地知识库网页")
    p_serve.add_argument("--host", default="127.0.0.1")
    p_serve.add_argument("--port", type=int, default=8000)

    args = parser.parse_args(argv)
    store = Store(Path(args.data))
    try:
        if args.cmd == "init":
            print(f"知识库已就绪：{store.db_path}")
            return 0
        if args.cmd == "seed":
            n = seed_examples(store)
            print(f"写入 {n} 条示例口播")
            return 0
        if args.cmd == "ingest":
            return _ingest(store, args)
        if args.cmd == "search":
            hits = store.search(args.query, limit=args.limit)
            print(json.dumps([h.model_dump() for h in hits], ensure_ascii=False, indent=2))
            return 0
        if args.cmd == "ask":
            answer = ask(store, args.question)
            print(answer.text)
            return 0
        if args.cmd == "list":
            for v in store.list_videos():
                print(f"{v.id}\t{v.title}\t{format_ts(v.duration_ms)}\t{v.collection}")
            return 0
        if args.cmd == "show":
            return _show(store, args.video_id)
        if args.cmd == "serve":
            from dykb.web import serve

            serve(Path(args.data), host=args.host, port=args.port)
            return 0
        parser.error("unknown command")
        return 2
    finally:
        store.close()


def _read_transcript(args: argparse.Namespace) -> str:
    if args.text:
        return args.text
    if args.transcript:
        path = Path(args.transcript)
        return path.read_text(encoding="utf-8")
    video = Path(args.video) if args.video else None
    if video:
        for ext in (".srt", ".vtt", ".txt"):
            side = video.with_suffix(ext)
            if side.exists():
                return side.read_text(encoding="utf-8")
    return ""


def _ingest(store: Store, args: argparse.Namespace) -> int:
    try:
        record = ingest(
            store,
            title=args.title,
            transcript=_read_transcript(args),
            video_path=Path(args.video) if args.video else None,
            author=args.author,
            source_url=args.url,
            file_url=getattr(args, "file_url", ""),
            tags=[t.strip() for t in args.tags.split(",") if t.strip()],
            notes=args.notes,
            collection=args.collection,
        )
    except (IngestError, FileNotFoundError) as exc:
        print(f"入库失败：{exc}", file=sys.stderr)
        return 1
    print(f"已入库 {record.id} 《{record.title}》 切片 {len(store.segments_for(record.id))} 卡片 {len(store.cards_for(record.id))}")
    return 0


def _show(store: Store, video_id: str) -> int:
    video = store.get_video(video_id)
    if not video:
        print("未找到该视频", file=sys.stderr)
        return 1
    print(json.dumps(video.model_dump(), ensure_ascii=False, indent=2))
    print("--- 卡片 ---")
    for card in store.cards_for(video_id):
        print(f"[{card.kind}] {card.body}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
