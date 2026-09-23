"""转写适配器。默认读用户提供的文案/字幕；本机装了 faster-whisper 才走语音识别。"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from dykb.chunk import segments_from_plain, segments_from_timed
from dykb.models import Segment
from dykb.textutil import parse_srt


class AsrEngine(Protocol):
    def transcribe(self, audio_path: Path, video_id: str, duration_ms: int) -> list[Segment]:
        ...


class TranscriptAsr:
    def __init__(self, text: str, kind: str = "manual") -> None:
        self.text = text
        self.kind = kind

    def transcribe(self, audio_path: Path, video_id: str, duration_ms: int) -> list[Segment]:
        if self.kind == "srt" or "-->" in self.text:
            timed = parse_srt(self.text)
            if timed:
                return segments_from_timed(video_id, timed, source="srt")
        return segments_from_plain(video_id, self.text, duration_ms, source=self.kind)


class WhisperAsr:
    def __init__(self, model_size: str = "tiny") -> None:
        self.model_size = model_size
        self._model = None

    def transcribe(self, audio_path: Path, video_id: str, duration_ms: int) -> list[Segment]:
        try:
            from faster_whisper import WhisperModel
        except ImportError as exc:
            raise RuntimeError("未安装 faster-whisper。请 pip install 'dykb[asr]'") from exc
        if self._model is None:
            self._model = WhisperModel(self.model_size, device="cpu", compute_type="int8")
        segments, _info = self._model.transcribe(str(audio_path), language="zh")
        items: list[tuple[int, int, str]] = []
        for seg in segments:
            start = int((seg.start or 0) * 1000)
            end = int((seg.end or 0) * 1000)
            text = (seg.text or "").strip()
            if text:
                items.append((start, end, text))
        if not items:
            return []
        return segments_from_timed(video_id, items, source="speech")
