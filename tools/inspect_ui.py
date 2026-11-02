#!/usr/bin/env python3
"""Dump Streamlit shell selectors and bounds for responsive CSS work."""

from playwright.sync_api import sync_playwright


CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
URL = "http://localhost:8501"


def main() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=CHROME)
        page = browser.new_page(viewport={"width": 390, "height": 844})
        page.goto(URL, wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(2500)
        print("URL", page.url)
        for sel in [
            '[data-testid="stAppViewContainer"]',
            '[data-testid="stHeader"]',
            '[data-testid="stMain"]',
            '[data-testid="stMainBlockContainer"]',
            '[data-testid="stMainBlockContainer"] > div',
            '[data-testid="stSidebar"]',
            '[data-testid="stSidebarContent"]',
            '[data-testid="stSidebarCollapseButton"]',
            '[data-testid="stSidebarCollapsedControl"]',
        ]:
            loc = page.locator(sel)
            if loc.count():
                box = loc.first.bounding_box()
                print(sel, "count=", loc.count(), "box=", box)
            else:
                print(sel, "MISSING")
        side = page.locator('[data-testid="stSidebar"]')
        if side.count():
            html = side.first.evaluate("(e) => e.outerHTML")
            print("SIDEBAR_HTML")
            print(html[:5000])
        print("MAIN_SELECTORS")
        for sel in [
            '[data-testid="stHorizontalBlock"]',
            '[data-testid="stColumn"]',
            '[data-testid="stMetric"]',
            '[data-testid="stChatMessage"]',
            '[data-testid="stButton"]',
            '[data-testid="stChatInput"]',
            '[data-testid="stTabs"]',
        ]:
            loc = page.locator(sel)
            print(sel, "count=", loc.count())
            if loc.count():
                print("  first_box=", loc.first.bounding_box())
        print("MOBILE_BODY", page.evaluate("() => ({iw:innerWidth, sw:document.documentElement.scrollWidth, sh:document.documentElement.scrollHeight})"))
        if page.locator('[data-testid="stHorizontalBlock"]').count():
            print("HORIZONTAL_HTML")
            print(page.locator('[data-testid="stHorizontalBlock"]').first.evaluate("(e) => e.outerHTML")[:5000])
        browser.close()


if __name__ == "__main__":
    main()
