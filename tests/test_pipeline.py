from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from awcollector.audit import AuditLog
from awcollector.models import FieldSpec, Permit, Step, TaskSpec
from awcollector.ocr import ScriptedOCREngine
from awcollector.permit import PermitError
from awcollector.pipeline import run_task, session_from_html_file, write_record

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "demo_gov_list.html"


def make_permit(**overrides) -> Permit:
    data = {
        "permit_id": "P-1",
        "operator": "tester",
        "organization": "demo",
        "purpose": "unit test",
        "allowed_url_prefixes": ["file://"],
        "expires_at": datetime.now(timezone.utc) + timedelta(days=1),
        "read_only": True,
    }
    data.update(overrides)
    return Permit.model_validate(data)


def make_task() -> TaskSpec:
    return TaskSpec(
        name="demo_gov_list",
        html_file=str(FIXTURE),
        steps=[
            Step(action="wait", selector="table.matter-list"),
            Step(
                action="extract",
                fields=[
                    FieldSpec(name="page_title", strategy="css", selector="h1.page-title"),
                    FieldSpec(name="matters", strategy="table", selector="table.matter-list"),
                    FieldSpec(
                        name="scan_text",
                        strategy="ocr_selector",
                        selector="img.scan-doc",
                        required=False,
                    ),
                ],
            ),
        ],
    )


def test_html_pipeline_collects_table(tmp_path: Path) -> None:
    permit = make_permit()
    task = make_task()
    session = session_from_html_file(FIXTURE)
    audit = AuditLog(tmp_path / "audit.jsonl")
    ocr = ScriptedOCREngine("许可编号 DEMO-2026-001")
    record = run_task(permit, task, session, ocr=ocr, audit=audit)
    path = write_record(record, tmp_path)

    assert record.permit_id == "P-1"
    assert record.data["page_title"] == "办事事项查询结果"
    assert len(record.data["matters"]) == 3
    assert record.ocr_used is True
    assert path.exists()
    assert "task_done" in (tmp_path / "audit.jsonl").read_text(encoding="utf-8")


def test_pipeline_rejects_out_of_scope_start() -> None:
    permit = make_permit()
    task = make_task()
    task.start_url = "https://not-allowed.example/list"
    session = session_from_html_file(FIXTURE, url=task.start_url)
    with pytest.raises(PermitError):
        run_task(permit, task, session)
