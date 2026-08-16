from pathlib import Path

from awcollector.cli import main

ROOT = Path(__file__).resolve().parents[1]


def test_check_permit_and_html_run(tmp_path: Path, capsys, monkeypatch) -> None:
    monkeypatch.chdir(ROOT)
    permit = ROOT / "configs" / "permit.example.json"
    task = ROOT / "configs" / "tasks" / "demo_gov_list.yaml"
    assert main(["check-permit", "--permit", str(permit)]) == 0

    code = main(
        [
            "run",
            "--permit",
            str(permit),
            "--task",
            str(task),
            "--out",
            str(tmp_path),
            "--mode",
            "html",
            "--ocr-text",
            "许可编号 DEMO-2026-001",
        ]
    )
    assert code == 0
    output = capsys.readouterr().out
    assert "采集完成" in output
    assert (tmp_path / "demo_gov_list.json").exists()
    assert (tmp_path / "audit.jsonl").exists()
