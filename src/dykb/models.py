from __future__ import annotations

from pydantic import BaseModel, Field


class Segment(BaseModel):
    id: str
    video_id: str
    start_ms: int = 0
    end_ms: int = 0
    text: str
    source: str = "manual"  # speech / srt / ocr / manual / seed


class KnowledgeCard(BaseModel):
    id: str
    video_id: str
    kind: str  # point / step / quote / term / warning
    title: str
    body: str
    start_ms: int = 0


class VideoRecord(BaseModel):
    id: str
    title: str
    author: str = ""
    source_url: str = ""
    douyin_id: str = ""
    tags: list[str] = Field(default_factory=list)
    video_path: str = ""
    duration_ms: int = 0
    sha256: str = ""
    summary: str = ""
    created_at: str = ""
    notes: str = ""
    collection: str = "默认合集"


class SearchHit(BaseModel):
    video_id: str
    title: str
    segment_id: str
    start_ms: int
    end_ms: int
    text: str
    source: str
    score: float = 0.0
    kind: str = "segment"  # segment / card


class Answer(BaseModel):
    question: str
    text: str
    citations: list[SearchHit] = Field(default_factory=list)
