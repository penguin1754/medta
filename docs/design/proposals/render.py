"""Render the three static design directions for review."""

import json
from pathlib import Path

from playwright.sync_api import sync_playwright


HERE = Path(__file__).resolve().parent
OUT = HERE / "renders"
OUT.mkdir(exist_ok=True)

PAGES = {
    "index": "index.html",
    "a-clinic": "scheme-a-clinic.html",
    "b-night": "scheme-b-night.html",
    "c-atlas": "scheme-c-atlas.html",
}

AUDIT = {
    "index": [".grid"],
    "a-clinic": [".a-rail", ".a-card", ".a-side"],
    "b-night": [".b-top", ".b-card", ".b-dock"],
    "c-atlas": [".c-index", ".c-plate", ".c-lens", ".c-foot"],
}


def main() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path=r"C:\Program Files\Google\Chrome\Application\chrome.exe"
        )
        page = browser.new_page(viewport={"width": 1440, "height": 960}, device_scale_factor=2)
        for name, filename in PAGES.items():
            page.goto((HERE / filename).as_uri(), wait_until="networkidle")
            page.wait_for_timeout(1800)
            page.screenshot(path=str(OUT / f"{name}.png"), full_page=False)
            metrics = page.evaluate(
                """(selectors) => {
                    const box = (el) => {
                        const r = el.getBoundingClientRect();
                        return {x:Math.round(r.x), y:Math.round(r.y),
                                w:Math.round(r.width), h:Math.round(r.height),
                                right:Math.round(r.right), bottom:Math.round(r.bottom)};
                    };
                    return {
                        viewport:{w:innerWidth,h:innerHeight},
                        document:{w:document.documentElement.scrollWidth,
                                  h:document.documentElement.scrollHeight},
                        boxes:Object.fromEntries(selectors.map(s => [s, box(document.querySelector(s))]))
                    };
                }""",
                AUDIT[name],
            )
            clipped = page.evaluate(
                """() => [...document.querySelectorAll('h1,h2,p,span,b,strong,small,a,button')]
                    .filter(el => {
                        const cs = getComputedStyle(el);
                        const hidden = cs.overflow === 'hidden' || cs.overflowX === 'hidden';
                        return !hidden && (el.scrollWidth > el.clientWidth + 2 ||
                                           el.scrollHeight > el.clientHeight + 2);
                    })
                    .map(el => ({tag:el.tagName, cls:el.className, text:(el.textContent||'').trim().slice(0,36),
                                 cw:el.clientWidth, sw:el.scrollWidth, ch:el.clientHeight, sh:el.scrollHeight}))
                    .slice(0,12)"""
            )
            beyond = page.evaluate(
                """() => [...document.querySelectorAll('body > *')]
                    .map(el => { const r=el.getBoundingClientRect(); const cs=getComputedStyle(el);
                      return {tag:el.tagName, cls:el.className, y:Math.round(r.y), bottom:Math.round(r.bottom),
                              h:Math.round(r.height), pos:cs.position}; })
                    .filter(x => x.bottom > innerHeight + 1)"""
            )
            print(f"rendered {name}: {OUT / (name + '.png')}")
            print(json.dumps(metrics, ensure_ascii=False))
            if clipped:
                print("CLIPPED " + json.dumps(clipped, ensure_ascii=False))
            if beyond:
                print("BEYOND " + json.dumps(beyond, ensure_ascii=False))
        browser.close()


if __name__ == "__main__":
    main()
