# -*- coding: utf-8 -*-
"""知识库构建的公共规则：分章、关键词、要点抽取。"""
import re
from collections import Counter

RULES = [
    ("神经系统", ["脑神经", "脊神经", "脊髓", "大脑", "小脑", "脑干", "延髓", "脑桥", "中脑", "丘脑",
                  "下丘脑", "锥体束", "交感", "副交感", "硬膜", "蛛网膜", "脑脊液", "内囊", "基底核",
                  "传导束", "神经核", "脉络丛", "脑室", "中枢神经", "周围神经"]),
    ("感觉器", ["眼球", "眼睑", "视网膜", "角膜", "晶状体", "瞳孔", "视神经盘", "中耳", "内耳", "鼓膜",
                "蜗", "半规管", "前庭", "听小骨", "咽鼓管", "结膜", "虹膜", "玻璃体", "外耳", "视器"]),
    ("脉管系统", ["心脏", "心房", "心室", "动脉", "静脉", "毛细血管", "淋巴", "心包", "瓣膜", "静脉角",
                  "门静脉", "腔静脉", "冠状动脉", "胸导管", "窦房结", "房室结", "大循环", "肺循环"]),
    ("内分泌系统", ["甲状腺", "甲状旁腺", "肾上腺", "垂体", "松果体", "胰岛", "胸腺", "内分泌腺"]),
    ("内脏学", ["胃", "小肠", "空肠", "回肠", "十二指肠", "结肠", "直肠", "肝", "胆囊", "胆总管", "胰",
                "食管", "口腔", "舌", "牙", "咽", "肺", "气管", "喉", "胸膜", "纵隔", "肾", "输尿管",
                "膀胱", "尿道", "睾丸", "附睾", "输精管", "前列腺", "卵巢", "输卵管", "子宫", "阴道",
                "腹膜", "会阴", "鼻腔", "鼻旁窦", "唾液腺", "阑尾", "脾"]),
    ("运动系统", ["骨", "关节", "肌", "韧带", "椎骨", "肋骨", "胸骨", "颅骨", "寰椎", "枢椎", "肩胛骨",
                  "肱骨", "桡骨", "尺骨", "股骨", "胫骨", "腓骨", "髋骨", "骨盆", "膈", "腱", "滑膜",
                  "软骨", "椎间盘", "椎体", "棘突", "关节面", "关节囊", "肌群", "筋膜", "足弓"]),
]

STOP = ("什么", "哪些", "如何", "哪个", "是否", "包括", "具有", "下列", "关于", "试述", "简述",
        "就是", "位于", "属于", "其", "该", "下列哪", "哪项", "主要")


def score_chapter(text):
    best, best_s = "", 0
    for chapter, kws in RULES:
        s = sum(len(k) for k in kws if k in text)
        if s > best_s:
            best, best_s = chapter, s
    return best


def classify_all(items, text_of):
    """逐条打分后做邻域平滑，孤立未命中用邻居补齐。"""
    labels = [score_chapter(text_of(it)) for it in items]
    out = list(labels)
    for i, lab in enumerate(labels):
        if lab:
            continue
        window = [l for l in labels[max(0, i - 4):i + 5] if l]
        if window:
            out[i] = Counter(window).most_common(1)[0][0]
    return [l or "综合" for l in out]


def keywords(text, limit=6):
    segs = re.split(r"[，。、；：？！,.;:?!（）()\s]|的是|的|有|是|和|与|及|在|由|称为|称", text)
    out = []
    for s in segs:
        s = s.strip()
        if 2 <= len(s) <= 6 and s not in STOP and not s.isdigit() and s not in out:
            out.append(s)
    return out[:limit]


def answer_keys(answer, limit=6):
    """从答案里抽要点词：只要名词性短语，供简答判分做命中率计算。"""
    BAD = set("的了就都被把对从向于以为所以因此但是而且如果并且可以具能有是称这那些个着过与和及或")
    segs = re.split(r"[，。、；：？！,.;:?!（）()\s]", answer)
    out = []
    for s in segs:
        s = s.strip(" 　")
        if not 2 <= len(s) <= 6:
            continue
        if s in STOP or s.isdigit():
            continue
        if any(ch in BAD for ch in s):
            continue
        if s[0] in "在由使因当若即其从对与和为把被将":
            continue
        if s.endswith("时"):
            continue
        if s not in out:
            out.append(s)
    return out[:limit]
