from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from awcollector.audit import AuditLog
from awcollector.browser import BrowserSession, HtmlFileSession
from awcollector.extract_dom import extract_fields
from awcollector.models import ExtractedRecord, FieldSpec, Permit, Step, TaskSpec
from awcollector.ocr import OCREngine
from awcollector.permit import assert_permit_active, assert_task_allowed, assert_url_allowed


class PipelineError(RuntimeError):
    """采集流水线失败。"""


def resolve_start(task: TaskSpec) -> str:
    if task.start_url:
        return task.start_url
    if task.html_file:
        return Path(task.html_file).resolve().as_uri()
    return ""


def _source_url(session: BrowserSession, task: TaskSpec) -> str:
    current = session.current_url()
    if current:
        return current
    return resolve_start(task)


def _run_ocr_fields(
    session: BrowserSession,
    fields: list[FieldSpec],
    ocr: OCREngine | None,
) -> tuple[dict[str, Any], bool]:
    ocr_fields = [field for field in fields if field.strategy.startswith("ocr_")]
    if not ocr_fields:
        return {}, False
    if ocr is None:
        raise PipelineError("任务包含 OCR 字段，但未提供 OCR 引擎")

    data: dict[str, Any] = {}
    for field in ocr_fields:
        image = b""
        if field.strategy == "ocr_selector":
            image = session.screenshot_bytes(field.selector)
        elif field.strategy == "ocr_region":
            image = session.screenshot_bytes(None)
        text = ocr.recognize(image) if image else ""
        if field.required and not text:
            raise PipelineError(f"OCR 字段 {field.name} 无识别结果")
        data[field.name] = text
    return data, True


def run_step(
    step: Step,
    session: BrowserSession,
    permit: Permit,
    ocr: OCREngine | None,
) -> dict[str, Any]:
    if step.action == "goto":
        if not step.url:
            raise PipelineError("goto 步骤缺少 url")
        assert_url_allowed(permit, step.url)
        session.goto(step.url, timeout_ms=step.timeout_ms)
        return {}
    if step.action == "click":
        if not step.selector:
            raise PipelineError("click 步骤缺少 selector")
        session.click(step.selector, timeout_ms=step.timeout_ms)
        return {}
    if step.action == "fill":
        if not step.selector or step.value is None:
            raise PipelineError("fill 步骤缺少 selector 或 value")
        session.fill(step.selector, step.value, timeout_ms=step.timeout_ms)
        return {}
    if step.action == "wait":
        if not step.selector:
            raise PipelineError("wait 步骤缺少 selector")
        session.wait(step.selector, timeout_ms=step.timeout_ms)
        return {}
    if step.action == "screenshot":
        session.screenshot_bytes(step.selector)
        return {}
    if step.action == "extract":
        html = session.content()
        data = extract_fields(html, step.fields)
        ocr_data, _ = _run_ocr_fields(session, step.fields, ocr)
        data.update(ocr_data)
        return data
    if step.action == "paginate":
        merged: list[Any] = []
        pages = max(1, step.max_pages)
        for index in range(pages):
            html = session.content()
            page_data = extract_fields(html, step.fields)
            ocr_data, _ = _run_ocr_fields(session, step.fields, ocr)
            page_data.update(ocr_data)
            for value in page_data.values():
                if isinstance(value, list):
                    merged.extend(value)
            if index + 1 >= pages or not step.next_selector:
                break
            session.click(step.next_selector, timeout_ms=step.timeout_ms)
        return {"pages": merged}
    raise PipelineError(f"未知步骤: {step.action}")


def run_task(
    permit: Permit,
    task: TaskSpec,
    session: BrowserSession,
    ocr: OCREngine | None = None,
    audit: AuditLog | None = None,
) -> ExtractedRecord:
    assert_permit_active(permit)
    assert_task_allowed(permit, task.allow_write)

    start = resolve_start(task)
    if start:
        assert_url_allowed(permit, start)

    if audit:
        audit.write(
            "task_start",
            permit_id=permit.permit_id,
            operator=permit.operator,
            task=task.name,
            source=start,
        )

    collected: dict[str, Any] = {}
    ocr_used = False
    try:
        for step in task.steps:
            current = _source_url(session, task) or start
            if current:
                assert_url_allowed(permit, current)
            chunk = run_step(step, session, permit, ocr)
            if any(field.strategy.startswith("ocr_") for field in step.fields):
                ocr_used = True
            collected.update(chunk)
    except Exception:
        if audit:
            audit.write(
                "task_error",
                permit_id=permit.permit_id,
                operator=permit.operator,
                task=task.name,
            )
        raise

    record = ExtractedRecord(
        task=task.name,
        source_url=_source_url(session, task),
        collected_at=datetime.now(timezone.utc),
        permit_id=permit.permit_id,
        operator=permit.operator,
        data=collected,
        ocr_used=ocr_used,
    )
    if audit:
        audit.write(
            "task_done",
            permit_id=permit.permit_id,
            operator=permit.operator,
            task=task.name,
            source_url=record.source_url,
            ocr_used=ocr_used,
            field_names=sorted(collected.keys()),
        )
    return record


def write_record(record: ExtractedRecord, output_dir: str | Path) -> Path:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{record.task}.jsonl"
    with path.open("a", encoding="utf-8") as handle:
        handle.write(record.model_dump_json() + "\n")
    sidecar = out / f"{record.task}.json"
    sidecar.write_text(
        json.dumps(record.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path


def session_from_html_file(html_file: str | Path, url: str | None = None) -> HtmlFileSession:
    path = Path(html_file)
    html = path.read_text(encoding="utf-8")
    return HtmlFileSession(html=html, url=url or path.resolve().as_uri())
