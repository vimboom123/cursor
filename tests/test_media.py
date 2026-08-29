from pathlib import Path

import pytest

from dykb.media import extract_wav, have_ffmpeg, probe_duration_ms
from dykb.pipeline import ingest
from dykb.store import Store


def _tiny_mp4(path: Path) -> Path:
    import subprocess

    result = subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=c=black:s=160x120:d=1",
            "-f",
            "lavfi",
            "-i",
            "anullsrc=r=16000:cl=mono",
            "-shortest",
            "-c:v",
            "libx264",
            "-c:a",
            "aac",
            "-t",
            "1",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        pytest.skip(result.stderr[-400:])
    return path


@pytest.mark.skipif(not have_ffmpeg(), reason="ffmpeg not installed")
def test_probe_and_extract_wav(tmp_path: Path) -> None:
    mp4 = _tiny_mp4(tmp_path / "a.mp4")
    duration = probe_duration_ms(mp4)
    assert 500 <= duration <= 2000
    wav = extract_wav(mp4, tmp_path / "a.wav")
    assert wav.exists() and wav.stat().st_size > 0


@pytest.mark.skipif(not have_ffmpeg(), reason="ffmpeg not installed")
def test_ingest_real_mp4_with_sidecar_transcript(tmp_path: Path) -> None:
    store = Store(tmp_path)
    mp4 = _tiny_mp4(tmp_path / "talk.mp4")
    record = ingest(
        store,
        title="带视频的口播",
        transcript="这是一条已授权的本地视频。第一点，音轨可以后补转写。",
        video_path=mp4,
    )
    assert Path(record.video_path).exists()
    assert record.duration_ms >= 500
    store.close()
