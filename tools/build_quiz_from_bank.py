# -*- coding: utf-8 -*-
"""ocr 解析结果 -> quiz.json（单选/判断）。多选、填空、名词解释、问答不进这里。

用法：python tools/build_quiz_from_bank.py [--write]
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "knowledge" / "_ocr" / "quiz_raw.json"
OUT = ROOT / "knowledge" / "quiz.json"
DOC = "系统解剖学 题库完整版1033题"

RULES = [
    ("神经系统", ["脑神经", "脊神经", "脊髓", "大脑", "小脑", "脑干", "延髓", "脑桥", "中脑", "丘脑",
                  "下丘脑", "锥体束", "交感", "副交感", "硬膜", "蛛网膜", "脑脊液", "内囊", "基底核",
                  "皮质", "反射弧", "传导束", "神经核", "终脑", "硬脊膜", "脉络丛", "脑室"]),
    ("感觉器", ["眼球", "眼睑", "视网膜", "角膜", "晶状体", "瞳孔", "视神经盘", "中耳", "内耳", "鼓膜",
                "蜗", "半规管", "前庭", "听小骨", "咽鼓管", "结膜", "虹膜", "玻璃体", "外耳"]),
    ("脉管系统", ["心脏", "心房", "心室", "动脉", "静脉", "毛细血管", "淋巴", "心包", "瓣膜", "静脉角",
                  "门静脉", "腔静脉", "冠状动脉", "胸导管", "心传导", "窦房结", "房室结", "大循环",
                  "肺循环", "心瓣"]),
    ("内脏学", ["胃", "小肠", "空肠", "回肠", "十二指肠", "结肠", "直肠", "肝", "胆囊", "胆总管", "胰",
                "食管", "口腔", "舌", "牙", "咽", "肺", "气管", "喉", "胸膜", "纵隔", "肾", "输尿管",
                "膀胱", "尿道", "睾丸", "附睾", "输精管", "前列腺", "卵巢", "输卵管", "子宫", "阴道",
                "腹膜", "会阴", "鼻腔", "鼻旁窦", "唾液腺", "阑尾", "脾"]),
    ("运动系统", ["骨", "关节", "肌", "韧带", "椎骨", "肋骨", "胸骨", "颅骨", "寰椎", "枢椎", "肩胛骨",
                  "肱骨", "桡骨", "尺骨", "股骨", "胫骨", "腓骨", "髋骨", "骨盆", "膈", "腱", "滑膜",
                  "软骨", "椎间盘", "椎体", "棘突", "关节面", "关节囊", "肌群", "筋膜", "足弓"]),
]

JUDGE_TRUE = ("正确", "对", "√", "V", "v", "是", "T", "True")
JUDGE_FALSE = ("错误", "错", "×", "X", "x", "否", "F", "False")


def score_chapter(text):
    best, best_s = "", 0
    for chapter, kws in RULES:
        s = sum(len(k) for k in kws if k in text)
        if s > best_s:
            best, best_s = chapter, s
    return best


def classify_all(items):
    labels = []
    for it in items:
        text = (it.get("stem") or "") + "".join(it.get("options") or [])
        labels.append(score_chapter(text))
    # 邻域平滑：整段题目通常同属一章，孤立的“综合”用邻居补
    out = list(labels)
    for i, lab in enumerate(labels):
        if lab:
            continue
        window = [l for l in labels[max(0, i - 4):i + 5] if l]
        if window:
            out[i] = Counter(window).most_common(1)[0][0]
    return [l or "综合" for l in out]


def norm_answer(it):
    ans = (it.get("answer") or "").strip().strip("（）()　 ")
    if it["type"] == "choice":
        letters = re.findall(r"[A-E]", ans.upper())
        if letters:
            return letters[0], ("" if len(letters) == 1 else "多选答案")
        return "", "答案缺失或不识别"
    for k in JUDGE_TRUE:
        if ans.startswith(k):
            return "正确", ""
    for k in JUDGE_FALSE:
        if ans.startswith(k):
            return "错误", ""
    return "", "答案缺失或不识别"


def main():
    raw = [i for i in json.loads(RAW.read_text(encoding="utf-8"))
           if i["type"] in ("choice", "judge")]
    raw.sort(key=lambda x: x["no"])
    chapters = classify_all(raw)
    out, warns = [], []
    for it, chapter in zip(raw, chapters):
        stem = (it.get("stem") or "").strip()
        if not stem:
            warns.append((it["no"], "题干残缺（跨页丢失），跳过"))
            continue
        opts = [o.strip() for o in it.get("options") or [] if o.strip()]
        ans, w = norm_answer(it)
        if w in ("多选答案", "答案缺失或不识别"):
            warns.append((it["no"], w))
            continue
        if it["type"] == "choice":
            if len(opts) < 3:
                warns.append((it["no"], "选项不足"))
                continue
            idx = "ABCDE".index(ans)
            if idx >= len(opts):
                warns.append((it["no"], "答案字母超出选项范围"))
                continue
            quiz_type = "single"
        else:
            opts = ["正确", "错误"]
            idx = 0 if ans == "正确" else 1
            quiz_type = "judge"
        out.append({
            "id": "bank_" + str(it["no"]),
            "point_id": "bank_" + str(it["no"]),
            "chapter": chapter,
            "type": quiz_type,
            "stem": stem,
            "options": opts,
            "answer_index": idx,
            "explain": (it.get("explain") or "") or ("判断。" if quiz_type == "judge" else ""),
            "source": {"doc": DOC, "locator": "题号 " + str(it["no"]) + "/1033"},
            "origin": "ocr_bank",
        })

    dist = Counter(q["chapter"] for q in out)
    print("candidates %d -> usable %d" % (len(raw), len(out)))
    print("chapters:", json.dumps(dist, ensure_ascii=False, sort_keys=True))
    print("skipped:", len(warns), Counter(w[1] for w in warns).most_common())

    if "--write" in sys.argv:
        backup = OUT.with_suffix(".json.bak")
        if OUT.exists() and not backup.exists():
            backup.write_text(OUT.read_text(encoding="utf-8"), encoding="utf-8")
        OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
        print("written", OUT, len(out), "items")


if __name__ == "__main__":
    main()
