#!/usr/bin/env python3
"""Text clipping / tiny type / overlap audit for the clinic theme."""
from playwright.sync_api import sync_playwright

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
URL = "http://localhost:8501"

CLIP_JS = """() => {
  const vis = e => { try { return e.checkVisibility({checkOpacity:true, checkVisibilityCSS:true}); } catch(err){ return true; } };
  const out = {clip: [], tiny: [], overlap: []};
  for (const e of document.querySelectorAll('[data-testid=stMainBlockContainer] *')) {
    if (!vis(e)) continue;
    const cs = getComputedStyle(e);
    if (e.children.length === 0 && e.textContent.trim() && e.scrollWidth > e.clientWidth + 2 && cs.overflowX !== 'auto' && cs.overflowX !== 'scroll' && cs.textOverflow !== 'ellipsis') {
      out.clip.push({t: e.textContent.trim().slice(0,28), sw: e.scrollWidth, cw: e.clientWidth, tag: e.tagName});
    }
    const fs = parseFloat(cs.fontSize);
    if (fs && fs < 11 && e.textContent.trim() && e.children.length === 0) out.tiny.push({t: e.textContent.trim().slice(0,20), fs});
  }
  const hero = document.querySelector('.page-hero');
  if (hero) {
    const a = hero.querySelector('.page-hero-copy'), b = hero.querySelector('.hero-metrics');
    if (a && b) { const ra = a.getBoundingClientRect(), rb = b.getBoundingClientRect(); if (ra.right > rb.left + 1 && ra.top < rb.bottom && rb.top < ra.bottom && innerWidth > 900) out.overlap.push('hero copy/metrics overlap'); }
  }
  const bar = document.querySelector('.app-topbar'), btn = document.querySelector('[data-testid=stExpandSidebarButton]');
  if (bar && btn && btn.checkVisibility()) { const rb = bar.getBoundingClientRect(), rn = btn.getBoundingClientRect(); if (rb.left < rn.right && rb.top < rn.bottom) out.overlap.push('topbar under open button'); }
  return out;
}"""

def go(pg, name, mobile):
    if mobile:
        pg.locator('[data-testid=stExpandSidebarButton]').click(); pg.wait_for_timeout(800)
    pg.locator('[data-testid="stSidebar"] [role=radiogroup] label').filter(has_text=name).first.click(); pg.wait_for_timeout(1500)
    if mobile:
        btn = pg.locator('[data-testid=stSidebarCollapseButton] button')
        if btn.count() and btn.first.is_visible():
            btn.first.click(); pg.wait_for_timeout(600)
        pg.wait_for_timeout(400)

with sync_playwright() as p:
    b = p.chromium.launch(executable_path=CHROME)
    for w, h in [(390, 844), (1440, 960)]:
        pg = b.new_page(viewport={"width": w, "height": h})
        pg.goto(URL, wait_until="networkidle", timeout=60000); pg.wait_for_timeout(3000)
        print("==", w, "initial scroll", pg.evaluate("(document.querySelector('[data-testid=stAppScrollToBottomContainer]')||document.querySelector('[data-testid=stMain]')).scrollTop"))
        for name in ["课程问答", "知识点速记", "自测练习", "考前冲刺", "学习档案"]:
            go(pg, name, w < 900)
            r = pg.evaluate(CLIP_JS)
            print(name, "clip", r["clip"][:3], "tiny", r["tiny"][:4], "overlap", r["overlap"])
            if name == "课程问答":
                print("   chatinput", pg.locator('[data-testid=stChatInput]').first.bounding_box())
        pg.close()
    b.close()


