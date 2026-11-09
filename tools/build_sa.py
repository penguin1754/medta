# -*- coding: utf-8 -*-
"""生成 knowledge/short_answer.json：题库里的问答题。

用法：python tools/build_sa.py [--write]
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from kb_common import answer_keys, classify_all  # noqa: E402

RAW = ROOT / "knowledge" / "_ocr" / "quiz_raw.json"
OUT = ROOT / "knowledge" / "short_answer.json"


def main():
    raw = json.loads(RAW.read_text(encoding="utf-8"))
    qa = [i for i in raw if i["type"] == "qa" and i["stem"] and i["answer"]]
    qa.sort(key=lambda x: x["no"])

    items = []
    # 先统计全库高频词，用来把“在受暴力时”这类口语片段筛掉
    from collections import Counter
    freq = Counter()
    for it in qa:
        for k in answer_keys(it["answer"], limit=20):
            freq[k] += 1
    for it in qa:
        q = it["stem"].strip()
        a = it["answer"].strip()
        if len(a) < 12:
            continue
        keys = answer_keys(a)
        strong = [k for k in keys if freq[k] >= 2]
        if len(strong) >= 2:
            keys = strong[:6]
        if len(keys) < 2:
            continue
        q = q.rstrip("。．.？? ")
        items.append({
            "id": "sa_bank_" + str(it["no"]),
            "card_id": "",
            "chapter": None,
            "question": q + "？",
            "answer": a,
            "keys": keys,
            "source": {"doc": "系统解剖学 题库完整版1033题", "locator": "问答 题号 " + str(it["no"]), "quote": ""},
            "origin": "ocr_bank",
        })

    labels = classify_all(items, lambda s: s["question"] + s["answer"])
    for s, lab in zip(items, labels):
        s["chapter"] = lab

    dist = {}
    for s in items:
        dist[s["chapter"]] = dist.get(s["chapter"], 0) + 1
    print("sa", len(items), json.dumps(dist, ensure_ascii=False, sort_keys=True))
    for s in items[:4]:
        print("-", s["chapter"], "|", s["question"][:34], "| keys", s["keys"])

    if "--write" in sys.argv:
        backup = OUT.with_suffix(".json.bak")
        if OUT.exists() and not backup.exists():
            backup.write_text(OUT.read_text(encoding="utf-8"), encoding="utf-8")
        OUT.write_text(json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")
        print("written", OUT)


if __name__ == "__main__":
    main()
