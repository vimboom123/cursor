"""从口播文本里抽出可独立阅读的知识卡片。"""

from __future__ import annotations

import re
import uuid

from dykb.models import KnowledgeCard, Segment
from dykb.textutil import split_sentences

_STEP_HEAD = re.compile(
    r"^(?:第[一二三四五六七八九十百\d]+[点步条项]|[（(]?\d+[）).、．]|首先|其次|然后|接着|最后|另外)"
)
_TERM = re.compile(r"(.+?)(?:是指|指的是|叫做|称为|也就是)(.+)")
_QUOTE = re.compile(r"[「“\"]([^」”\"]{6,80})[」”\"]")
_WARN = re.compile(r"(注意|记住|千万不要|不要|切忌|重点是)")


def extract_cards(video_id: str, segments: list[Segment]) -> list[KnowledgeCard]:
    cards: list[KnowledgeCard] = []
    seen: set[str] = set()

    for seg in segments:
        for sent in split_sentences(seg.text):
            sent = sent.strip()
            if len(sent) < 6:
                continue
            kind, title, body = _classify(sent)
            key = f"{kind}:{body}"
            if key in seen:
                continue
            seen.add(key)
            cards.append(
                KnowledgeCard(
                    id=uuid.uuid4().hex[:12],
                    video_id=video_id,
                    kind=kind,
                    title=title,
                    body=body,
                    start_ms=seg.start_ms,
                )
            )

    return cards[:40]


def _classify(sent: str) -> tuple[str, str, str]:
    term = _TERM.search(sent)
    if term and 2 <= len(term.group(1)) <= 24:
        name = term.group(1).strip(" ，,：:")
        return "term", name, sent

    if _STEP_HEAD.search(sent):
        return "step", _clip(sent, 18), sent

    quote = _QUOTE.search(sent)
    if quote:
        q = quote.group(1)
        return "quote", _clip(q, 18), q

    if _WARN.search(sent):
        return "warning", _clip(sent, 18), sent

    if 12 <= len(sent) <= 80:
        return "point", _clip(sent, 18), sent

    return "point", _clip(sent, 18), sent


def _clip(text: str, n: int) -> str:
    text = re.sub(r"\s+", "", text)
    return text if len(text) <= n else text[: n - 1] + "…"


def summarize(title: str, segments: list[Segment], cards: list[KnowledgeCard]) -> str:
    if cards:
        heads = "；".join(c.title for c in cards[:4])
        return f"《{title}》要点：{heads}"
    if segments:
        first = segments[0].text
        return first if len(first) <= 120 else first[:117] + "…"
    return title
