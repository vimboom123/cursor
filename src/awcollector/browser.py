from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


class BrowserSession(Protocol):
    def goto(self, url: str, timeout_ms: int = 15000) -> None: ...
    def click(self, selector: str, timeout_ms: int = 15000) -> None: ...
    def fill(self, selector: str, value: str, timeout_ms: int = 15000) -> None: ...
    def wait(self, selector: str, timeout_ms: int = 15000) -> None: ...
    def content(self) -> str: ...
    def current_url(self) -> str: ...
    def screenshot_bytes(self, selector: str | None = None) -> bytes: ...
    def close(self) -> None: ...


@dataclass
class HtmlFileSession:
    """无浏览器模式：直接读本地 HTML，便于演练和单测。"""

    html: str
    url: str

    def goto(self, url: str, timeout_ms: int = 15000) -> None:
        self.url = url

    def click(self, selector: str, timeout_ms: int = 15000) -> None:
        return None

    def fill(self, selector: str, value: str, timeout_ms: int = 15000) -> None:
        return None

    def wait(self, selector: str, timeout_ms: int = 15000) -> None:
        return None

    def content(self) -> str:
        return self.html

    def current_url(self) -> str:
        return self.url

    def screenshot_bytes(self, selector: str | None = None) -> bytes:
        return b""

    def close(self) -> None:
        return None


class PlaywrightSession:
    """挂到已登录的 Chrome/Chromium，或使用持久化用户目录。"""

    def __init__(self, page: Any) -> None:
        self.page = page

    def goto(self, url: str, timeout_ms: int = 15000) -> None:
        self.page.goto(url, timeout=timeout_ms, wait_until="domcontentloaded")

    def click(self, selector: str, timeout_ms: int = 15000) -> None:
        self.page.locator(selector).first.click(timeout=timeout_ms)

    def fill(self, selector: str, value: str, timeout_ms: int = 15000) -> None:
        locator = self.page.locator(selector).first
        locator.wait_for(timeout=timeout_ms)
        locator.fill(value)

    def wait(self, selector: str, timeout_ms: int = 15000) -> None:
        self.page.locator(selector).first.wait_for(timeout=timeout_ms)

    def content(self) -> str:
        return self.page.content()

    def current_url(self) -> str:
        return self.page.url

    def screenshot_bytes(self, selector: str | None = None) -> bytes:
        if selector:
            return self.page.locator(selector).first.screenshot(type="png")
        return self.page.screenshot(type="png", full_page=False)

    def close(self) -> None:
        return None


def connect_existing_chrome(cdp_url: str = "http://127.0.0.1:9222") -> PlaywrightSession:
    from playwright.sync_api import sync_playwright

    playwright = sync_playwright().start()
    browser = playwright.chromium.connect_over_cdp(cdp_url)
    if not browser.contexts:
        raise RuntimeError("已连接浏览器，但没有任何上下文。请先在该浏览器中打开业务页。")
    context = browser.contexts[0]
    page = context.pages[0] if context.pages else context.new_page()
    session = PlaywrightSession(page)
    session._playwright = playwright  # noqa: SLF001
    session._browser = browser  # noqa: SLF001
    return session
