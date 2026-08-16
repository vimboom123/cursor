from __future__ import annotations

from typing import Any

from bs4 import BeautifulSoup, Tag
from lxml import html as lxml_html

from awcollector.models import FieldSpec


class ExtractError(RuntimeError):
    """DOM 抽取失败。"""


def parse_html(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "lxml")


def text_of(node: Tag | None) -> str:
    if node is None:
        return ""
    return " ".join(node.get_text(" ", strip=True).split())


def extract_css(soup: BeautifulSoup, spec: FieldSpec) -> Any:
    if not spec.selector:
        raise ExtractError(f"字段 {spec.name} 缺少 selector")
    nodes = soup.select(spec.selector)
    if spec.multiple:
        return [text_of(node) for node in nodes if isinstance(node, Tag)]
    if not nodes:
        if spec.required:
            raise ExtractError(f"字段 {spec.name} 未匹配到: {spec.selector}")
        return None
    return text_of(nodes[0])


def extract_xpath(html: str, spec: FieldSpec) -> Any:
    if not spec.selector:
        raise ExtractError(f"字段 {spec.name} 缺少 xpath")
    tree = lxml_html.fromstring(html)
    found = tree.xpath(spec.selector)
    values: list[str] = []
    for item in found:
        if hasattr(item, "text_content"):
            values.append(" ".join(item.text_content().split()))
        else:
            values.append(str(item).strip())
    if spec.multiple:
        return values
    if not values:
        if spec.required:
            raise ExtractError(f"字段 {spec.name} 未匹配到 xpath: {spec.selector}")
        return None
    return values[0]


def extract_table(soup: BeautifulSoup, spec: FieldSpec) -> list[dict[str, str]]:
    if not spec.selector:
        raise ExtractError(f"表格字段 {spec.name} 缺少 selector")
    table = soup.select_one(spec.selector)
    if table is None:
        if spec.required:
            raise ExtractError(f"未找到表格: {spec.selector}")
        return []

    headers: list[str] = []
    head_row = table.select_one("thead tr") or table.select_one("tr")
    if head_row:
        headers = [text_of(cell) for cell in head_row.find_all(["th", "td"])]

    body_rows = table.select("tbody tr")
    if not body_rows:
        all_rows = table.select("tr")
        body_rows = all_rows[1:] if len(all_rows) > 1 else []

    records: list[dict[str, str]] = []
    for row in body_rows:
        cells = [text_of(cell) for cell in row.find_all(["td", "th"])]
        if not cells or cells == headers:
            continue
        if headers and len(headers) == len(cells):
            records.append(dict(zip(headers, cells, strict=False)))
        else:
            records.append({f"col_{index}": value for index, value in enumerate(cells)})
    return records


def extract_fields(html: str, fields: list[FieldSpec]) -> dict[str, Any]:
    soup = parse_html(html)
    data: dict[str, Any] = {}
    for spec in fields:
        if spec.strategy == "css":
            data[spec.name] = extract_css(soup, spec)
        elif spec.strategy == "xpath":
            data[spec.name] = extract_xpath(html, spec)
        elif spec.strategy == "table":
            data[spec.name] = extract_table(soup, spec)
        elif spec.strategy.startswith("ocr_"):
            continue
        else:
            raise ExtractError(f"不支持的抽取策略: {spec.strategy}")
    return data
