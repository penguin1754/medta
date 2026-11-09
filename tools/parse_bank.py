# -*- coding: utf-8 -*-
"""把 OCR 逐页文本解析成题目 JSON。

输入：knowledge/_ocr/pages.jsonl
输出：knowledge/_ocr/quiz_raw.json
题型：choice(选择) / judge(判断) / term(名词解释)
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGES = ROOT / "knowledge" / "_ocr" / "pages.jsonl"
OUT = ROOT / "knowledge" / "_ocr" / "quiz_raw.json"

NOISE = ("微信公众号", "公众号", "关注", "题库（", "题库(", "试题答案列表", "答题指南")

SECTION = (
    ("只能选择其中最佳", "single"),
    ("共用备选项", "b"),
    ("一项或多项正确", "multi"),
    ("空白处填上", "fill"),
    ("判断下列说法", "judge"),
    ("解释下列名词", "term"),
    ("回答下列问题", "qa"),
)

NUM_RE = re.compile(r"题\s*号\s*[:：]?\s*(\d+)\s*/\s*(\d+)")
OPT_RE = re.compile(r"^([A-E])\s*[、.．:：]\s*(.+)$")
ANS_RE = re.compile(r"^答\s*案?\s*[:：]?\s*(.+)$")
EXP_RE = re.compile(r"^解\s*析\s*[:：]?\s*(.*)$")
FW = str.maketrans("ＡＢＣＤＥ０１２３４５６７８９：．，（）", "ABCDE0123456789:.,()")


def clean(s):
    return re.sub(r"\s+", "", s.translate(FW)).strip()


def load_pages():
    rows = [json.loads(l) for l in PAGES.read_text(encoding="utf-8").splitlines() if l.strip()]
    rows.sort(key=lambda r: r["page"])
    return rows


def build_item(no, page, lines, section):
    stem, opts, ans, exp = [], [], "", ""
    for line in lines:
        line = clean(line)
        if not line:
            continue
        m = EXP_RE.match(line)
        if m:
            exp += m.group(1)
            continue
        m = ANS_RE.match(line)
        if m:
            ans = m.group(1)
            continue
        m = OPT_RE.match(line)
        # 只有按 A/B/C/D/E 顺序出现才算选项，避免题干里的字母被误判
        if m and m.group(1) == "ABCDE"[len(opts)]:
            opts.append(m.group(2))
            continue
        if opts:
            opts[-1] += line
        elif ans:
            ans += line
        else:
            stem.append(line)

    text = "".join(stem)
    if not text and ans:
        # 名词解释常丢题干：答案开头就是“术语：定义”
        head = re.split(r"[：:]", ans, maxsplit=1)
        if len(head) == 2 and 1 <= len(head[0]) <= 12:
            text, ans = head[0], head[1]
    if section == "qa":
        kind = "qa"
    elif section == "term":
        kind = "term"
    elif section == "judge":
        kind = "judge"
    elif section in ("single", "b"):
        kind = "choice"
    elif section == "multi":
        kind = "multi"
    elif section == "fill":
        kind = "fill"
    elif len(opts) >= 2:
        kind = "choice"
    else:
        # 名解题干是术语（很短），问答题干是完整句子
        kind = "term" if len(text) <= 12 else "qa"
    # 问答题常被上一节的“名解”指南带到 term，这里按题干特征纠回
    if kind == "term" and len(text) > 14 and re.match(
            r"^(简述|试述|说明|叙述|何谓|什么是|如何|为什么|比较|论述|试比较|请|某)", text):
        kind = "qa"
    if kind == "term" and len(text) > 12:
        kind = "qa"
    ans = re.sub(r"^答\s*[:：]", "", ans).strip()
    return {"no": no, "page": page, "type": kind, "section": section, "stem": text,
            "options": opts, "answer": ans, "explain": exp}


def parse(rows):
    items, cur, buf = [], None, []
    section = ""

    def flush():
        nonlocal cur, buf
        if cur is not None:
            items.append(build_item(cur["no"], cur["page"], buf, cur["section"]))
        cur, buf = None, []

    for row in rows:
        for raw in row["lines"]:
            line = raw.strip()
            if "答题指南" in line:
                for key, name in SECTION:
                    if key in line:
                        section = name
                        break
                continue
            if not line or any(n in line for n in NOISE):
                continue
            m = NUM_RE.search(line)
            if m:
                flush()
                cur = {"no": int(m.group(1)), "page": row["page"], "section": section}
                rest = line[m.end():].strip()
                buf = [rest] if rest else []
                continue
            if cur is not None:
                buf.append(line)
    flush()
    return items


def main():
    rows = load_pages()
    items = parse(rows)
    OUT.write_text(json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")
    kinds = {}
    for i in items:
        kinds[i["type"]] = kinds.get(i["type"], 0) + 1
    print("pages=%d items=%d %s" % (len(rows), len(items), json.dumps(kinds, ensure_ascii=False)))
    nums = {i["no"] for i in items}
    missing = [n for n in range(1, 1034) if n not in nums]
    print("missing:", missing)
    for key, label in (("answer", "无答案"), ("stem", "无题干")):
        bad = [i["no"] for i in items if not i.get(key)]
        print(label + ":", len(bad), bad[:12])


if __name__ == "__main__":
    main()
