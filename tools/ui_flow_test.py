#!/usr/bin/env python3
"""Mobile/desktop interaction check for the clinic theme."""
from pathlib import Path
from playwright.sync_api import sync_playwright

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
URL = "http://localhost:8501"
OUT = Path(r"D:\Codex工作区\ai智能体\medta\docs\design\clinic\screens")
ok_all = []

def check(label, cond, detail=""):
    ok_all.append(bool(cond))
    print(("PASS " if cond else "FAIL ") + label + ("  " + str(detail) if detail else ""))

def open_sidebar(page):
    ctl = page.locator('[data-testid="stExpandSidebarButton"]')
    if ctl.count() and ctl.first.is_visible():
        ctl.first.click(); page.wait_for_timeout(800)

def close_sidebar(page):
    btn = page.locator('[data-testid="stSidebarCollapseButton"] button')
    if btn.count() and btn.first.is_visible():
        btn.first.click(); page.wait_for_timeout(700)

def go(page, name, mobile):
    if mobile: open_sidebar(page)
    page.locator('[data-testid="stSidebar"] [role="radiogroup"] label').filter(has_text=name).first.click()
    page.wait_for_timeout(1600)
    if mobile:
        close_sidebar(page); page.wait_for_timeout(600)

def run(page, w, label):
    mobile = w < 900
    print("==", label, w)
    # 知识点速记：翻牌
    go(page, "知识点速记", mobile)
    flip = page.get_by_role("button", name="翻面看答案")
    check("cards flip button visible", flip.count() > 0)
    if flip.count():
        flip.first.click(); page.wait_for_timeout(1200)
        back = page.locator(".face.back")
        box = back.first.bounding_box() if back.count() else None
        check("back face rendered", back.count() > 0, box)
        if box:
            check("back face fits viewport", box["x"] >= 0 and box["x"] + box["width"] <= w + 1, box)
            check("back face has height", box["height"] >= (300 if mobile else 320), box["height"])
        # 3D 效果保留
        wrap = page.locator(".flipwrap")
        tr = wrap.first.evaluate("e=>getComputedStyle(e).transform") if wrap.count() else ""
        check("flip wrap transformed", tr and tr != "none", tr)
        page.screenshot(path=str(OUT / f"state-{label}-flip.png"))
    # 自测：选择题
    go(page, "自测练习", mobile)
    radios = page.locator('[data-testid="stMainBlockContainer"] [data-testid="stRadioOption"]')
    check("quiz radios", radios.count() >= 2, radios.count())
    hs = [round(radios.nth(i).bounding_box()["height"]) for i in range(min(radios.count(), 6))]
    check("radio tap height", all(h >= 40 for h in hs), hs)
    radios.first.click(); page.wait_for_timeout(500)
    sub = page.get_by_role("button", name="提交答案")
    check("submit visible", sub.count() > 0)
    sub.first.click(); page.wait_for_timeout(1600)
    verdict = page.locator(".verdict")
    check("quiz verdict shown", verdict.count() > 0)
    if verdict.count():
        vb = verdict.first.bounding_box()
        check("verdict inside viewport", vb and vb["x"] >= 0 and vb["x"] + vb["width"] <= w + 1, vb)
    page.screenshot(path=str(OUT / f"state-{label}-quiz.png"))
    # 简答题
    tab = page.get_by_role("tab", name="简答题")
    if tab.count():
        tab.first.click(); page.wait_for_timeout(1400)
        area = page.locator('[data-testid="stTextArea"] textarea')
        check("short answer textarea", area.count() > 0)
        if area.count():
            area.first.fill("肱骨外科颈骨折容易损伤腋神经，出现三角肌麻痹。")
            page.get_by_role("button", name="提交，看命中几个要点").first.click()
            page.wait_for_timeout(1800)
            sv = page.locator(".verdict")
            check("short answer verdict", sv.count() > 0, sv.first.inner_text()[:40] if sv.count() else "")
            chips = page.locator(".keyhit, .keymiss")
            check("key chips", chips.count() > 0, chips.count())
            page.screenshot(path=str(OUT / f"state-{label}-sa.png"))
    # 冲刺
    go(page, "考前冲刺", mobile)
    metrics = page.locator('[data-testid="stMetric"]')
    check("sprint metrics count", metrics.count() >= 4, metrics.count())
    if mobile:
        xs = sorted({round(metrics.nth(i).bounding_box()["x"]) for i in range(min(4, metrics.count()))})
        check("sprint metrics two columns", len(xs) == 2, xs)
    strip = page.locator(".st-key-sprint_preview [data-testid='stHorizontalBlock']")
    if strip.count():
        sc = strip.first.evaluate("e=>({sw:e.scrollWidth, cw:e.clientWidth, ov:getComputedStyle(e).overflowX})")
        check("preview strip scrollable", (not mobile) or (sc["sw"] > sc["cw"] and sc["ov"] in ("auto", "scroll")), sc)
    page.screenshot(path=str(OUT / f"state-{label}-sprint.png"))
    # 档案
    go(page, "学习档案", mobile)
    ring = page.locator(".ring-wrap")
    check("profile ring", ring.count() > 0)
    heat = page.locator(".heat i")
    check("heat cells", heat.count() >= 7, heat.count())
    if mobile:
        hm = page.locator('[data-testid="stMetric"]')
        xs = sorted({round(hm.nth(i).bounding_box()["x"]) for i in range(min(5, hm.count()))})
        check("profile metrics two columns", len(xs) <= 2, xs)
    page.screenshot(path=str(OUT / f"state-{label}-profile.png"))

def main():
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=CHROME)
        for label, w, h in [("mobile", 390, 844), ("desktop", 1440, 960)]:
            ctx = b.new_context(viewport={"width": w, "height": h}, device_scale_factor=2 if w < 500 else 1)
            pg = ctx.new_page()
            pg.goto(URL, wait_until="networkidle", timeout=60000)
            pg.wait_for_timeout(2500)
            run(pg, w, label)
            ctx.close()
        b.close()
    print("SUMMARY", sum(ok_all), "/", len(ok_all), "passed")

if __name__ == "__main__":
    main()


