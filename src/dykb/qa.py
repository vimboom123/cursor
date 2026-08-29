from __future__ import annotations

from dykb.models import Answer, SearchHit
from dykb.store import Store
from dykb.textutil import format_ts, tokenize

_HOW = ("怎么", "如何", "怎样", "步骤", "方法")
_WHAT = ("什么是", "是什么", "啥是", "定义")


def ask(store: Store, question: str, limit: int = 8) -> Answer:
    question = (question or "").strip()
    if not question:
        return Answer(question=question, text="请先提出一个问题。")

    hits = store.search(question, limit=limit)
    if not hits:
        return Answer(
            question=question,
            text="知识库里还没有相关口播。把已授权的视频或文案入库后再问一次。",
        )

    preferred = _prefer(question, hits)
    lines = [f"根据已入库的 {len({h.video_id for h in preferred})} 条口播："]
    seen_text: set[str] = set()
    cited: list[SearchHit] = []
    for hit in preferred:
        key = hit.text[:40]
        if key in seen_text:
            continue
        seen_text.add(key)
        cited.append(hit)
        ts = format_ts(hit.start_ms)
        snippet = hit.text if len(hit.text) <= 180 else hit.text[:177] + "…"
        lines.append(f"- 《{hit.title}》{ts}：{snippet}")
        if len(cited) >= 4:
            break
    return Answer(question=question, text="\n".join(lines), citations=cited)


def _prefer(question: str, hits: list[SearchHit]) -> list[SearchHit]:
    qtoks = set(tokenize(question).split())
    want_how = any(k in question for k in _HOW)
    want_what = any(k in question for k in _WHAT)

    def rank(hit: SearchHit) -> tuple[int, int, float]:
        title_overlap = len(qtoks & set(tokenize(hit.title).split()))
        kind_bonus = 0
        if want_what and ("【term】" in hit.text or "是指" in hit.text or "叫做" in hit.text):
            kind_bonus = 1
        if want_how and ("【step】" in hit.text or "第一点" in hit.text or "第一步" in hit.text):
            kind_bonus = 1
        return (-title_overlap, -kind_bonus, hit.score)

    return sorted(hits, key=rank)


_HOW = ("怎么", "如何", "怎样", "步骤", "方法")
_WHAT = ("什么是", "是什么", "啥是", "定义")


def ask(store: Store, question: str, limit: int = 8) -> Answer:
    question = (question or "").strip()
    if not question:
        return Answer(question=question, text="请先提出一个问题。")

    hits = store.search(question, limit=limit)
    if not hits:
        return Answer(
            question=question,
            text="知识库里还没有相关口播。把已授权的视频或文案入库后再问一次。",
        )

    preferred = _prefer(question, hits)
    lines = [f"根据已入库的 {len({h.video_id for h in preferred})} 条口播："]
    seen_text: set[str] = set()
    cited: list[SearchHit] = []
    for hit in preferred:
        key = hit.text[:40]
        if key in seen_text:
            continue
        seen_text.add(key)
        cited.append(hit)
        ts = format_ts(hit.start_ms)
        snippet = hit.text if len(hit.text) <= 180 else hit.text[:177] + "…"
        lines.append(f"- 《{hit.title}》{ts}：{snippet}")
        if len(cited) >= 4:
            break
    return Answer(question=question, text="\n".join(lines), citations=cited)


def _prefer(question: str, hits: list[SearchHit]) -> list[SearchHit]:
    if any(k in question for k in _HOW):
        steps = [h for h in hits if "step" in h.text or "【step】" in h.text or "首先" in h.text or "第" in h.text]
        if steps:
            return steps + [h for h in hits if h not in steps]
    if any(k in question for k in _WHAT):
        terms = [h for h in hits if "【term】" in h.text or "是指" in h.text or "叫做" in h.text]
        if terms:
            return terms + [h for h in hits if h not in terms]
    return hits
