# -*- coding: utf-8 -*-
"""生成 knowledge/cards.json：题库里的名词解释 + 考点问答。

用法：python tools/build_cards.py [--write]
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from kb_common import classify_all, keywords  # noqa: E402

RAW = ROOT / "knowledge" / "_ocr" / "quiz_raw.json"
POINTS = ROOT / "knowledge" / "_ocr" / "cards_raw.json"
OUT = ROOT / "knowledge" / "cards.json"


def main():
    raw = json.loads(RAW.read_text(encoding="utf-8"))
    terms = [i for i in raw if i["type"] == "term" and i["stem"] and i["answer"]]
    terms.sort(key=lambda x: x["no"])

    points = json.loads(POINTS.read_text(encoding="utf-8")) if POINTS.exists() else []

    cards = []
    for it in terms:
        front = it["stem"].strip()
        ans = it["answer"].strip()
        for sep in ("：", ":"):
            if ans.startswith(front + sep):
                ans = ans[len(front) + 1:].strip()
                break
        if not front.endswith(("？", "?")):
            front = front + "是什么？" if len(front) <= 6 else front + "？"
        cards.append({
            "id": "card_term_" + str(it["no"]),
            "point_id": "pt_term_" + str(it["no"]),
            "chapter": None,
            "topic": "名词解释",
            "front": front,
            "keywords": keywords(front + it["answer"]),
            "answer": ans,
            "source": {"doc": "系统解剖学 题库完整版1033题", "locator": "名词解释 题号 " + str(it["no"]), "quote": ""},
            "origin": "ocr_bank",
        })

    for i, c in enumerate(points):
        cards.append({
            "id": "card_pt_" + str(i + 1),
            "point_id": "pt_pt_" + str(i + 1),
            "chapter": None,
            "topic": c["chapter"],
            "front": c["front"],
            "keywords": c["keywords"],
            "answer": c["answer"],
            "source": {"doc": "系统解剖学 重点考点及答案", "locator": c["source"]["locator"], "quote": ""},
            "origin": "ocr_point",
        })

    # 名词解释没有上下文，按顺序平滑会和邻居串味，单独按自身文本判章
    labels = classify_all(cards, lambda c: (c["front"] or "") + (c["answer"] or ""))
    for c, lab in zip(cards, labels):
        c["chapter"] = lab
        c["topic"] = c["topic"] if c["topic"] != c["chapter"] else c["chapter"]

    dist = {}
    for c in cards:
        dist[c["chapter"]] = dist.get(c["chapter"], 0) + 1
    print("cards", len(cards), json.dumps(dist, ensure_ascii=False, sort_keys=True))
    for c in cards[:3]:
        print("-", c["chapter"], "|", c["front"][:30], "|", c["answer"][:40])

    if "--write" in sys.argv:
        backup = OUT.with_suffix(".json.bak")
        if OUT.exists() and not backup.exists():
            backup.write_text(OUT.read_text(encoding="utf-8"), encoding="utf-8")
        OUT.write_text(json.dumps(cards, ensure_ascii=False, indent=1), encoding="utf-8")
        print("written", OUT)


if __name__ == "__main__":
    main()
