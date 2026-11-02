#!/usr/bin/env python3
"""Clinic theme: screenshots + layout audit for desktop / mobile / narrow."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
URL = "http://localhost:8501"
OUT = Path(r"D:\Codex工作区\ai智能体\medta\docs\design\clinic\screens")
MODULES = [("课程问答", "ask"), ("知识点速记", "cards"), ("自测练习", "quiz"), ("考前冲刺", "sprint"), ("学习档案", "profile")]
SIZES = [("desktop", 1440, 960), ("mobile", 390, 844), ("narrow", 360, 800)]

AUDIT_JS = """() => {
  const vis = (el) => { try { return el.checkVisibility({checkOpacity:true, checkVisibilityCSS:true}); } catch(e) { return true; } };
  const iw = innerWidth;
  const bad = [];
  for (const el of document.querySelectorAll('[data-testid=stMainBlockContainer] *')) {
    if (!vis(el)) continue;
    const r = el.getBoundingClientRect();
    if (r.width < 1 || r.height < 1) continue;
    if (r.right > iw + 1.5 || r.left < -1.5) {
      bad.push({tag: el.tagName, cls: (el.className||'').toString().slice(0,50), testid: el.getAttribute('data-testid'), text: (el.innerText||'').trim().slice(0,32), l: Math.round(r.left), r: Math.round(r.right)});
    }
  }
  const seen = new Set(); const out = [];
  for (const b of bad) { const k = b.tag+b.cls+b.testid+b.text+b.l+b.r; if (!seen.has(k)) { seen.add(k); out.push(b); } }
  return {iw, sw: document.documentElement.scrollWidth, count: out.length, items: out.slice(0, 8)};
}"""

TAP_JS = """() => {
  const vis = (el) => { try { return el.checkVisibility({checkOpacity:true, checkVisibilityCSS:true}); } catch(e) { return true; } };
  const small = [];
  const nodes = document.querySelectorAll('button, [role=radio], [role=tab], [data-testid=stSelectbox] [role=combobox], input[type=checkbox]');
  for (const el of nodes) {
    if (!vis(el)) continue;
    const r = el.getBoundingClientRect();
    if (r.height < 38 || r.width < 24) {
      small.push({text:(el.innerText||el.getAttribute('aria-label')||'').trim().slice(0,24), w:Math.round(r.width), h:Math.round(r.height)});
    }
  }
  const seen = new Set(); const out = [];
  for (const b of small) { const k = b.text+b.w+b.h; if (!seen.has(k)) { seen.add(k); out.push(b); } }
  return out.slice(0, 10);
}"""

def open_sidebar(page):
    ctl = page.locator('[data-testid="stExpandSidebarButton"]')
    if ctl.count() and ctl.first.is_visible():
        ctl.first.click(); page.wait_for_timeout(800)

def close_sidebar(page):
    btn = page.locator('[data-testid="stSidebarCollapseButton"] button')
    if btn.count() and btn.first.is_visible():
        btn.first.click(); page.wait_for_timeout(700)

def select_module(page, name, mobile):
    if mobile:
        open_sidebar(page)
    page.locator('[data-testid="stSidebar"] [role="radiogroup"] label').filter(has_text=name).first.click()
    page.wait_for_timeout(1500)
    if mobile:
        close_sidebar(page); page.wait_for_timeout(600)

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    report = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=CHROME)
        for label, w, h in SIZES:
            ctx = browser.new_context(viewport={"width": w, "height": h}, device_scale_factor=2 if w < 500 else 1)
            page = ctx.new_page()
            page.goto(URL, wait_until="networkidle", timeout=60000)
            page.wait_for_timeout(2500)
            mobile = w < 900
            report[label] = {}
            for name, slug in MODULES:
                select_module(page, name, mobile)
                page.wait_for_timeout(400)
                audit = page.evaluate(AUDIT_JS)
                taps = page.evaluate(TAP_JS)
                page.screenshot(path=str(OUT / f"{label}-{slug}-top.png"))
                blk = page.locator('[data-testid="stMainBlockContainer"]')
                blk.screenshot(path=str(OUT / f"{label}-{slug}-full.png"))
                report[label][name] = {"audit": audit, "taps": taps}
                print(label, name, "overflow=", audit["count"], "sw=", audit["sw"], "tapSmall=", len(taps))
                for it in audit["items"]:
                    print("   OVF", it)
                for it in taps:
                    print("   TAP", it)
            if mobile:
                open_sidebar(page); page.wait_for_timeout(700)
                sb = page.locator('[data-testid="stSidebar"]').first.bounding_box()
                content = page.locator('[data-testid="stSidebarContent"]').first.bounding_box()
                close_btn = page.locator('[data-testid="stSidebarCollapseButton"] button').first.bounding_box()
                nav = page.locator('[data-testid="stSidebar"] [role="radiogroup"] label')
                nav_h = [round(nav.nth(i).bounding_box()["height"]) for i in range(nav.count())]
                report[label]["drawer"] = {"sidebar": sb, "content": content, "close": close_btn, "navHeights": nav_h}
                print(label, "drawer", sb, content, "close", close_btn, "nav", nav_h)
                page.screenshot(path=str(OUT / f"{label}-drawer.png"))
                close_sidebar(page); page.wait_for_timeout(600)
            ctx.close()
        browser.close()
    (OUT / "audit.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")

if __name__ == "__main__":
    main()
