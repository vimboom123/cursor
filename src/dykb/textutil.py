from __future__ import annotations

import re

import jieba

_SENT_SPLIT = re.compile(r"(?<=[。！？!?；;\n])")
_WS = re.compile(r"\s+")


def normalize(text: str) -> str:
    return _WS.sub(" ", (text or "").replace("\ufeff", "")).strip()


def tokenize(text: str) -> str:
    cleaned = normalize(text)
    if not cleaned:
        return ""
    words = jieba.lcut(cleaned)
    return " ".join(w.strip() for w in words if w.strip() and not w.isspace())


def fts_query(text: str) -> str:
    quoted = []
    for token in tokenize(text).split():
        token = token.replace('"', "")
        if token:
            quoted.append(f'"{token}"')
    return " OR ".join(quoted)


def split_sentences(text: str) -> list[str]:
    text = (text or "").strip()
    if not text:
        return []
    parts = [p.strip() for p in _SENT_SPLIT.split(text)]
    return [p for p in parts if p]


def chunk_sentences(sentences: list[str], max_chars: int = 160) -> list[str]:
    chunks: list[str] = []
    buf: list[str] = []
    size = 0
    for sent in sentences:
        if buf and size + len(sent) > max_chars:
            chunks.append("".join(buf))
            buf, size = [], 0
        buf.append(sent)
        size += len(sent)
    if buf:
        chunks.append("".join(buf))
    return chunks


def parse_srt(content: str) -> list[tuple[int, int, str]]:
    """返回 (start_ms, end_ms, text) 列表。"""
    blocks = re.split(r"\n\s*\n", content.replace("\r\n", "\n").strip())
    items: list[tuple[int, int, str]] = []
    time_re = re.compile(
        r"(\d{1,2}):(\d{2}):(\d{2})[,.](\d{1,3})\s*-->\s*"
        r"(\d{1,2}):(\d{2}):(\d{2})[,.](\d{1,3})"
    )
    for block in blocks:
        lines = [ln.strip() for ln in block.split("\n") if ln.strip()]
        if not lines:
            continue
        time_line = lines[0] if "-->" in lines[0] else (lines[1] if len(lines) > 1 else "")
        match = time_re.search(time_line)
        if not match:
            continue
        text_lines = lines[2:] if "-->" in lines[1] else lines[1:]
        text = normalize(" ".join(text_lines))
        if not text:
            continue
        items.append((_hms_ms(match, 1), _hms_ms(match, 5), text))
    return items


def _hms_ms(match: re.Match[str], start: int) -> int:
    h, m, s, frac = (int(match.group(i)) for i in range(start, start + 4))
    frac_s = match.group(start + 3)
    ms = int(frac_s.ljust(3, "0")[:3])
    return ((h * 60 + m) * 60 + s) * 1000 + ms


def format_ts(ms: int) -> str:
    ms = max(0, int(ms))
    s, _ = divmod(ms, 1000)
    m, s = divmod(s, 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h:d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"
