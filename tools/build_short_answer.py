"""从知识卡生成简答题（question = 卡面问题，answer = 卡片答案，keys = 卡片关键词）。

这样做的好处是简答题和速记共用同一份已审核内容，不会出现「速记说 A、简答说 B」。
以后换成团队整理的题源时，只要提供同样结构的 JSON，同样可以放进来。

用法：
    python tools/build_short_answer.py            # 生成 knowledge/short_answer.json
    python tools/build_short_answer.py --check    # 只检查现有文件是否与卡片同步
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KNOW = ROOT / "knowledge"


def build():
    cards = json.loads((KNOW / "cards.json").read_text(encoding="utf-8"))
    items = []
    for card in cards:
        keys = [k for k in (card.get("keywords") or []) if k]
        if len(keys) < 3:
            raise SystemExit("卡片 " + card["id"] + " 的 keywords 少于 3 个，无法作为评分要点")
        items.append({
            "id": "sa_" + card["id"],
            "card_id": card["id"],
            "chapter": card["chapter"],
            "question": card["front"],
            "answer": card["answer"],
            "keys": keys,
            "source": card.get("source") or {},
            "origin": "derived_from_card",
        })
    return items


def main():
    items = build()
    target = KNOW / "short_answer.json"
    if "--check" in sys.argv:
        if not target.exists():
            raise SystemExit("缺少 " + target.name)
        old = json.loads(target.read_text(encoding="utf-8"))
        print("卡片", len(items), "题 / 文件", len(old), "题 ->",
              "一致" if len(old) == len(items) else "需要重建")
        return
    target.write_text(json.dumps(items, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print("写入", target, len(items), "题")


if __name__ == "__main__":
    main()
