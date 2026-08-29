from __future__ import annotations

from dykb.models import Segment
from dykb.textutil import chunk_sentences, split_sentences


def segments_from_plain(
    video_id: str,
    text: str,
    duration_ms: int = 0,
    source: str = "manual",
) -> list[Segment]:
    sentences = split_sentences(text)
    chunks = chunk_sentences(sentences)
    if not chunks:
        return []
    duration_ms = max(duration_ms, len(chunks) * 4000)
    step = duration_ms / len(chunks)
    out: list[Segment] = []
    for i, chunk in enumerate(chunks):
        start = int(i * step)
        end = int(min(duration_ms, (i + 1) * step))
        out.append(
            Segment(
                id=f"{video_id}-s{i+1:03d}",
                video_id=video_id,
                start_ms=start,
                end_ms=end,
                text=chunk,
                source=source,
            )
        )
    return out


def segments_from_timed(
    video_id: str,
    items: list[tuple[int, int, str]],
    source: str = "srt",
) -> list[Segment]:
    out: list[Segment] = []
    for i, (start, end, text) in enumerate(items):
        if not text.strip():
            continue
        out.append(
            Segment(
                id=f"{video_id}-s{i+1:03d}",
                video_id=video_id,
                start_ms=start,
                end_ms=max(end, start),
                text=text.strip(),
                source=source,
            )
        )
    return out
