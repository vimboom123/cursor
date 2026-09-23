from pathlib import Path

from awcollector.extract_dom import extract_fields
from awcollector.models import FieldSpec

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "demo_gov_list.html"


def test_extract_title_and_table() -> None:
    html = FIXTURE.read_text(encoding="utf-8")
    data = extract_fields(
        html,
        [
            FieldSpec(name="page_title", strategy="css", selector="h1.page-title"),
            FieldSpec(name="matters", strategy="table", selector="table.matter-list"),
            FieldSpec(
                name="first_matter",
                strategy="xpath",
                selector="//table[contains(@class,'matter-list')]//tbody/tr[1]/td[2]",
            ),
        ],
    )
    assert data["page_title"] == "办事事项查询结果"
    assert len(data["matters"]) == 3
    assert data["matters"][0]["事项名称"] == "食品经营许可变更"
    assert data["matters"][1]["办理状态"] == "已办结"
    assert data["first_matter"] == "食品经营许可变更"


def test_ocr_fields_are_skipped_in_dom_pass() -> None:
    html = FIXTURE.read_text(encoding="utf-8")
    data = extract_fields(
        html,
        [FieldSpec(name="scan_text", strategy="ocr_selector", selector="img.scan-doc")],
    )
    assert data == {}
