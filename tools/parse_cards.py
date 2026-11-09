# -*- coding: utf-8 -*-
"""考点问答（20页）-> knowledge/cards.json 的知识卡。

输入：knowledge/_ocr/pages_cards.jsonl
输出：knowledge/_ocr/cards_raw.json（先看质量，再决定是否写入正式库）
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGES = ROOT / "knowledge" / "_ocr" / "pages_cards.jsonl"
OUT = ROOT / "knowledge" / "_ocr" / "cards_raw.json"

NOISE = ("微信公众号", "公众号", "关注", "简答汇总")
CH_NAMES = ("运动系统", "内脏学", "脉管系统", "感觉器", "神经系统", "内分泌系统", "绪论", "内脏")
ITEM_RE = re.compile(r"^(\d{1,3})\s*[.、．]\s*(.*)$")
STOP = ("什么", "哪些", "如何", "哪个", "是否", "包括", "具有", "下列", "关于", "试述", "简述", "分别")


def keywords(text, extra=""):
    segs = re.split(r"[，。、；：？！,.;:?!（）()\s]|的是|的|有|是|和|与|及|在|由", text)
    out = []
    for s in segs:
        s = s.strip()
        if 2 <= len(s) <= 6 and s not in STOP and not s.isdigit() and s not in out:
            out.append(s)
    for s in extra:
        if s and s not in out:
            out.insert(0, s)
    return out[:6]


def main():
    rows = [json.loads(l) for l in PAGES.read_text(encoding="utf-8").splitlines() if l.strip()]
    rows.sort(key=lambda r: r["page"])
    lines = []
    for r in rows:
        for l in r["lines"]:
            l = l.strip()
            if not l or any(n in l for n in NOISE):
                continue
            if l in CH_NAMES:
                lines.append(("CH", l))
                continue
            lines.append(("L", l))

    items, chapter, buf, num = [], "综合", [], 0
    for kind, text in lines:
        if kind == "CH":
            if buf:
                items.append((chapter, num, "".join(buf)))
            chapter, buf, num = text, [], 0
            continue
        m = ITEM_RE.match(text)
        if m and (num == 0 or int(m.group(1)) == num + 1):
            if buf:
                items.append((chapter, num, "".join(buf)))
            num = int(m.group(1))
            buf = [m.group(2)]
        else:
            if buf is not None:
                if buf and re.match(r"^\d{1,2}\s*[.、．]|^[一二三四五六七八九十]+\s*[、.]", text):
                    buf.append("；")
                buf.append(text)
    if buf:
        items.append((chapter, num, "".join(buf)))

    cards = []
    for chapter, num, body in items:
        body = body.strip()
        if len(body) < 8:
            continue
        m = re.search(r"[？?]", body)
        if m:
            front, rest = body[:m.start()], body[m.start() + 1:]
        else:
            m2 = re.search(r"[。.]", body)
            if not m2:
                continue
            front, rest = body[:m2.start()], body[m2.start() + 1:]
            front = front + "？"
        front = front.strip("　 ,，、")
        rest = rest.strip()
        if not front.endswith(("？", "?")):
            front = front + "？"
        if len(front) < 4 or len(rest) < 4:
            continue
        cards.append({
            "id": "card_q%d" % num if num else "card_x%d" % len(cards),
            "point_id": "pt_q%d" % num if num else "pt_x%d" % len(cards),
            "chapter": chapter,
            "topic": chapter,
            "front": front,
            "keywords": keywords(front),
            "answer": rest,
            "source": {"doc": "系统解剖学 重点考点及答案", "locator": chapter + " / 第" + str(num) + "题", "quote": ""},
            "origin": "ocr_point",
        })

    OUT.write_text(json.dumps(cards, ensure_ascii=False, indent=1), encoding="utf-8")
    dist = {}
    for c in cards:
        dist[c["chapter"]] = dist.get(c["chapter"], 0) + 1
    print("cards", len(cards), json.dumps(dist, ensure_ascii=False))
    for c in cards[:5]:
        print("-", c["chapter"], "|", c["front"][:40], "|", c["answer"][:50])


if __name__ == "__main__":
    main()
