from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

from dykb.models import KnowledgeCard, SearchHit, Segment, VideoRecord
from dykb.textutil import fts_query, tokenize

SCHEMA = """
CREATE TABLE IF NOT EXISTS videos (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    author TEXT DEFAULT '',
    source_url TEXT DEFAULT '',
    douyin_id TEXT DEFAULT '',
    tags TEXT DEFAULT '[]',
    video_path TEXT DEFAULT '',
    duration_ms INTEGER DEFAULT 0,
    sha256 TEXT DEFAULT '',
    summary TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    notes TEXT DEFAULT '',
    collection TEXT DEFAULT '默认合集'
);

CREATE TABLE IF NOT EXISTS segments (
    id TEXT PRIMARY KEY,
    video_id TEXT NOT NULL,
    start_ms INTEGER DEFAULT 0,
    end_ms INTEGER DEFAULT 0,
    text TEXT NOT NULL,
    source TEXT DEFAULT 'manual',
    FOREIGN KEY(video_id) REFERENCES videos(id)
);

CREATE TABLE IF NOT EXISTS cards (
    id TEXT PRIMARY KEY,
    video_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    start_ms INTEGER DEFAULT 0,
    FOREIGN KEY(video_id) REFERENCES videos(id)
);

CREATE VIRTUAL TABLE IF NOT EXISTS segment_fts USING fts5(
    fts_text,
    video_id UNINDEXED,
    segment_id UNINDEXED
);

CREATE VIRTUAL TABLE IF NOT EXISTS card_fts USING fts5(
    fts_text,
    video_id UNINDEXED,
    card_id UNINDEXED
);
"""


class Store:
    def __init__(self, data_dir: Path) -> None:
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.media_dir = self.data_dir / "media"
        self.media_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.data_dir / "knowledge.db"
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)

    def close(self) -> None:
        self.conn.close()

    def stats(self) -> dict[str, int]:
        cur = self.conn
        videos = cur.execute("SELECT COUNT(*) FROM videos").fetchone()[0]
        segs = cur.execute("SELECT COUNT(*) FROM segments").fetchone()[0]
        cards = cur.execute("SELECT COUNT(*) FROM cards").fetchone()[0]
        duration = cur.execute("SELECT COALESCE(SUM(duration_ms),0) FROM videos").fetchone()[0]
        return {
            "videos": videos,
            "segments": segs,
            "cards": cards,
            "duration_ms": duration,
        }

    def list_videos(self) -> list[VideoRecord]:
        rows = self.conn.execute(
            "SELECT * FROM videos ORDER BY created_at DESC"
        ).fetchall()
        return [self._video(r) for r in rows]

    def get_video(self, video_id: str) -> VideoRecord | None:
        row = self.conn.execute(
            "SELECT * FROM videos WHERE id = ?", (video_id,)
        ).fetchone()
        return self._video(row) if row else None

    def find_by_hash(self, sha256: str) -> VideoRecord | None:
        if not sha256:
            return None
        row = self.conn.execute(
            "SELECT * FROM videos WHERE sha256 = ?", (sha256,)
        ).fetchone()
        return self._video(row) if row else None

    def segments_for(self, video_id: str) -> list[Segment]:
        rows = self.conn.execute(
            "SELECT * FROM segments WHERE video_id = ? ORDER BY start_ms, id",
            (video_id,),
        ).fetchall()
        return [self._segment(r) for r in rows]

    def cards_for(self, video_id: str) -> list[KnowledgeCard]:
        rows = self.conn.execute(
            "SELECT * FROM cards WHERE video_id = ? ORDER BY start_ms, id",
            (video_id,),
        ).fetchall()
        return [self._card(r) for r in rows]

    def all_cards(self, limit: int = 80) -> list[tuple[KnowledgeCard, str]]:
        rows = self.conn.execute(
            """
            SELECT c.*, v.title AS video_title
            FROM cards c JOIN videos v ON v.id = c.video_id
            ORDER BY v.created_at DESC, c.start_ms
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [(self._card(r), r["video_title"]) for r in rows]

    def collections(self) -> list[str]:
        rows = self.conn.execute(
            "SELECT DISTINCT collection FROM videos ORDER BY collection"
        ).fetchall()
        names = [r[0] or "默认合集" for r in rows]
        return names or ["默认合集"]

    def save_media(self, src: Path, video_id: str) -> Path:
        dest = self.media_dir / f"{video_id}{src.suffix.lower() or '.mp4'}"
        shutil.copy2(src, dest)
        return dest

    def upsert_video(
        self,
        video: VideoRecord,
        segments: list[Segment],
        cards: list[KnowledgeCard],
    ) -> VideoRecord:
        self.conn.execute("DELETE FROM segment_fts WHERE video_id = ?", (video.id,))
        self.conn.execute("DELETE FROM card_fts WHERE video_id = ?", (video.id,))
        self.conn.execute("DELETE FROM segments WHERE video_id = ?", (video.id,))
        self.conn.execute("DELETE FROM cards WHERE video_id = ?", (video.id,))
        self.conn.execute("DELETE FROM videos WHERE id = ?", (video.id,))
        self.conn.execute(
            """
            INSERT INTO videos (
                id, title, author, source_url, douyin_id, tags, video_path,
                duration_ms, sha256, summary, created_at, notes, collection
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                video.id,
                video.title,
                video.author,
                video.source_url,
                video.douyin_id,
                json.dumps(video.tags, ensure_ascii=False),
                video.video_path,
                video.duration_ms,
                video.sha256,
                video.summary,
                video.created_at,
                video.notes,
                video.collection or "默认合集",
            ),
        )
        for seg in segments:
            self.conn.execute(
                """
                INSERT INTO segments (id, video_id, start_ms, end_ms, text, source)
                VALUES (?,?,?,?,?,?)
                """,
                (seg.id, seg.video_id, seg.start_ms, seg.end_ms, seg.text, seg.source),
            )
            self.conn.execute(
                "INSERT INTO segment_fts (fts_text, video_id, segment_id) VALUES (?,?,?)",
                (tokenize(seg.text), seg.video_id, seg.id),
            )
        for card in cards:
            self.conn.execute(
                """
                INSERT INTO cards (id, video_id, kind, title, body, start_ms)
                VALUES (?,?,?,?,?,?)
                """,
                (card.id, card.video_id, card.kind, card.title, card.body, card.start_ms),
            )
            self.conn.execute(
                "INSERT INTO card_fts (fts_text, video_id, card_id) VALUES (?,?,?)",
                (tokenize(f"{card.title} {card.body}"), card.video_id, card.id),
            )
        self.conn.commit()
        return video

    def search(self, query: str, limit: int = 12) -> list[SearchHit]:
        match = fts_query(query)
        if not match:
            return []
        hits: dict[str, SearchHit] = {}
        try:
            seg_rows = self.conn.execute(
                """
                SELECT s.*, v.title AS title,
                       bm25(segment_fts) AS rank
                FROM segment_fts
                JOIN segments s ON s.id = segment_fts.segment_id
                JOIN videos v ON v.id = s.video_id
                WHERE segment_fts MATCH ?
                ORDER BY rank
                LIMIT ?
                """,
                (match, limit),
            ).fetchall()
        except sqlite3.OperationalError:
            seg_rows = []
        for row in seg_rows:
            hit = SearchHit(
                video_id=row["video_id"],
                title=row["title"],
                segment_id=row["id"],
                start_ms=row["start_ms"],
                end_ms=row["end_ms"],
                text=row["text"],
                source=row["source"],
                score=float(row["rank"] or 0),
                kind="segment",
            )
            hits[f"s:{hit.segment_id}"] = hit

        try:
            card_rows = self.conn.execute(
                """
                SELECT c.id, c.video_id, c.kind, c.body, c.start_ms,
                       v.title AS video_title,
                       bm25(card_fts) AS rank
                FROM card_fts
                JOIN cards c ON c.id = card_fts.card_id
                JOIN videos v ON v.id = c.video_id
                WHERE card_fts MATCH ?
                ORDER BY rank
                LIMIT ?
                """,
                (match, limit),
            ).fetchall()
        except sqlite3.OperationalError:
            card_rows = []
        for row in card_rows:
            hit = SearchHit(
                video_id=row["video_id"],
                title=row["video_title"],
                segment_id=row["id"],
                start_ms=row["start_ms"],
                end_ms=row["start_ms"],
                text=f"【{row['kind']}】{row['body']}",
                source="card",
                score=float(row["rank"] or 0) - 0.4,
                kind="card",
            )
            hits[f"c:{hit.segment_id}"] = hit

        ranked = sorted(hits.values(), key=lambda h: h.score)
        return ranked[:limit]

    def _video(self, row: sqlite3.Row) -> VideoRecord:
        tags = row["tags"] or "[]"
        try:
            parsed = json.loads(tags)
        except json.JSONDecodeError:
            parsed = []
        return VideoRecord(
            id=row["id"],
            title=row["title"],
            author=row["author"] or "",
            source_url=row["source_url"] or "",
            douyin_id=row["douyin_id"] or "",
            tags=parsed,
            video_path=row["video_path"] or "",
            duration_ms=row["duration_ms"] or 0,
            sha256=row["sha256"] or "",
            summary=row["summary"] or "",
            created_at=row["created_at"],
            notes=row["notes"] or "",
            collection=row["collection"] or "默认合集",
        )

    def _segment(self, row: sqlite3.Row) -> Segment:
        return Segment(
            id=row["id"],
            video_id=row["video_id"],
            start_ms=row["start_ms"],
            end_ms=row["end_ms"],
            text=row["text"],
            source=row["source"],
        )

    def _card(self, row: sqlite3.Row) -> KnowledgeCard:
        return KnowledgeCard(
            id=row["id"],
            video_id=row["video_id"],
            kind=row["kind"],
            title=row["title"],
            body=row["body"],
            start_ms=row["start_ms"],
        )


def new_id() -> str:
    return uuid.uuid4().hex[:12]


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()
