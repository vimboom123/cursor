from __future__ import annotations

from pathlib import Path

from dykb.chunk import segments_from_plain
from dykb.douyin import is_douyin_share_url, parse_source_url
from dykb.errors import DouyinLinkError, IngestError
from dykb.fetch import fetch_user_file
from dykb.knowledge import extract_cards, summarize
from dykb.media import extract_wav, probe_duration_ms
from dykb.models import Segment, VideoRecord
from dykb.store import Store, file_sha256, new_id, now_iso
from dykb.textutil import parse_srt

__all__ = ["IngestError", "DouyinLinkError", "ingest"]


def ingest(
    store: Store,
    *,
    title: str,
    transcript: str = "",
    video_path: Path | None = None,
    author: str = "",
    source_url: str = "",
    file_url: str = "",
    tags: list[str] | None = None,
    notes: str = "",
    collection: str = "默认合集",
    asr: object | None = None,
    allow_private_urls: bool = False,
) -> VideoRecord:
    title = (title or "").strip()
    transcript = (transcript or "").strip()
    file_url = (file_url or "").strip()
    if not title:
        raise IngestError("标题不能为空")

    if file_url:
        fetched = fetch_user_file(
            file_url,
            store.data_dir / "uploads",
            allow_private=allow_private_urls,
        )
        if fetched.kind == "transcript":
            transcript = transcript or fetched.text
        else:
            video_path = video_path or fetched.path

    if not transcript and video_path is None:
        if is_douyin_share_url(source_url) or is_douyin_share_url(file_url):
            raise DouyinLinkError(source_url or file_url)
        raise IngestError("需要口播文案，或上传已授权的视频文件")

    sha = file_sha256(video_path) if video_path else ""
    if sha:
        existing = store.find_by_hash(sha)
        if existing:
            return existing

    video_id = new_id()
    meta = parse_source_url(source_url)
    duration_ms = 0
    saved = ""
    if video_path is not None:
        dest = store.save_media(video_path, video_id)
        saved = str(dest)
        try:
            duration_ms = probe_duration_ms(dest)
        except Exception:
            duration_ms = 0

    segments: list[Segment] = []
    if transcript:
        if "-->" in transcript:
            timed = parse_srt(transcript)
            if timed:
                from dykb.chunk import segments_from_timed

                segments = segments_from_timed(video_id, timed, source="srt")
                if not duration_ms and timed:
                    duration_ms = timed[-1][1]
        if not segments:
            segments = segments_from_plain(video_id, transcript, duration_ms, source="manual")
    elif asr is not None and video_path is not None:
        wav = store.data_dir / "tmp" / f"{video_id}.wav"
        extract_wav(Path(saved), wav)
        segments = asr.transcribe(wav, video_id, duration_ms)  # type: ignore[attr-defined]
        wav.unlink(missing_ok=True)
    else:
        raise IngestError(
            "没有文案。请粘贴口播稿/SRT，或安装 faster-whisper 后对已授权视频做转写。"
        )

    if not segments:
        raise IngestError("没有抽到可用文本")

    if not duration_ms:
        duration_ms = max(seg.end_ms for seg in segments)

    cards = extract_cards(video_id, segments)
    record = VideoRecord(
        id=video_id,
        title=title,
        author=author.strip(),
        source_url=meta["source_url"],
        douyin_id=meta["douyin_id"],
        tags=tags or [],
        video_path=saved,
        duration_ms=duration_ms,
        sha256=sha,
        summary=summarize(title, segments, cards),
        created_at=now_iso(),
        notes=notes.strip(),
        collection=collection.strip() or "默认合集",
    )
    store.upsert_video(record, segments, cards)
    return record
