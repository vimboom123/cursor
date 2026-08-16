from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class Permit(BaseModel):
    """采集许可。没有有效许可，采集器拒绝运行。"""

    permit_id: str
    operator: str
    organization: str
    purpose: str
    allowed_url_prefixes: list[str] = Field(min_length=1)
    expires_at: datetime
    read_only: bool = True

    @field_validator("allowed_url_prefixes")
    @classmethod
    def prefixes_must_be_explicit(cls, value: list[str]) -> list[str]:
        cleaned = [item.strip() for item in value if item.strip()]
        if not cleaned:
            raise ValueError("许可必须声明至少一个允许的 URL 前缀")
        if any(item == "*" for item in cleaned):
            raise ValueError("不允许使用通配许可")
        return cleaned


class FieldSpec(BaseModel):
    name: str
    strategy: Literal["css", "xpath", "table", "ocr_selector", "ocr_region"]
    selector: str | None = None
    region: tuple[int, int, int, int] | None = None
    multiple: bool = False
    required: bool = True


class Step(BaseModel):
    action: Literal[
        "goto",
        "click",
        "fill",
        "wait",
        "extract",
        "paginate",
        "screenshot",
    ]
    url: str | None = None
    selector: str | None = None
    value: str | None = None
    timeout_ms: int = 15000
    fields: list[FieldSpec] = Field(default_factory=list)
    max_pages: int = 1
    next_selector: str | None = None
    note: str | None = None


class TaskSpec(BaseModel):
    name: str
    start_url: str | None = None
    html_file: str | None = None
    steps: list[Step] = Field(min_length=1)
    allow_write: bool = False


class ExtractedRecord(BaseModel):
    task: str
    source_url: str
    collected_at: datetime
    permit_id: str
    operator: str
    data: dict[str, Any]
    ocr_used: bool = False
