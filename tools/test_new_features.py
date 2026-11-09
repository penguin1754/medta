#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""冲刺排期与简答判分的单元检查（不依赖 Streamlit、不联网）。

用法（medta 目录下）：
    $env:PYTHONIOENCODING="utf-8"; python tools/test_new_features.py
"""
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import backend.app as core  # noqa: E402

fails = []


def check(name, ok, extra=""):
    print(("  [OK]   " if ok else "  [FAIL] ") + name + ("  " + str(extra) if extra else ""))
    if not ok:
        fails.append(name)


def test_score():
    item = {"keys": ["三角肌", "肩外侧", "四边孔"]}
    full = core.score_short_answer(item, "损伤后三角肌瘫痪，肩外侧感觉障碍，经四边孔穿出。")
    check("全命中得 100 分", full["score"] == 100 and full["passed"] == 1, full["score"])
    part = core.score_short_answer(item, "三角肌 四边孔")
    check("命中 2/3 得 67 分且不通过", part["score"] == 67 and part["passed"] == 0, part["score"])
    empty = core.score_short_answer(item, "")
    check("空答得 0 分", empty["score"] == 0 and len(empty["missed"]) == 3)
    noisy = core.score_short_answer(item, "三角肌、肩外侧；四边孔！！")
    check("标点不影响判分", noisy["score"] == 100)
    again = core.score_short_answer(item, "损伤后三角肌瘫痪，肩外侧感觉障碍，经四边孔穿出。")
    check("同一份作答结果稳定", again == full)


def test_sprint():
    sid = "test-sprint-unit"
    core.STORE.reset(sid)
    core.STORE.set_exam(sid, "2026-12-20")
    plan = core.STORE.sprint(sid)
    check("配额总和不超每日上限", sum(plan["quotas"].values()) <= plan["daily_cards"] or
          plan["daily_cards"] == 0, sum(plan["quotas"].values()))
    check("今日清单不超过每日配额", len(plan["today"]) <= max(1, plan["daily_cards"]),
          len(plan["today"]))
    check("待掌握数等于卡片总数（新用户）", plan["remaining"] == len(core.CARDS))
    lefts = [d["left_after"] for d in plan["preview"]]
    check("预览逐日不增且不为负", all(b <= a for a, b in zip(lefts, lefts[1:])) and lefts[-1] >= 0,
          lefts)
    if len(core.CARDS) <= plan["daily_cards"] * len(lefts):
        check("题目少时预览能清零", lefts[-1] == 0, lefts[-1])
    check("考试日期被记住", core.STORE.exam_date(sid) == "2026-12-20")

    core.STORE.set_exam(sid, (date.today() + timedelta(days=1)).isoformat())
    tight = core.STORE.sprint(sid)
    check("只剩 1 天时按每日上限学", tight["daily_cards"] == min(60, len(core.CARDS)),
          tight["daily_cards"])

    core.STORE.reset(sid)
    for card in core.CARDS:
        core.STORE.review_card(sid, card, True)
    done = core.STORE.sprint(sid)
    check("全部掌握后配额为 0", done["remaining"] == 0 and done["daily_cards"] == 0)
    core.STORE.reset(sid)


def test_short_answer_store():
    if not core.SA:
        check("简答题库非空", False, "run tools/build_short_answer.py")
        return
    sid = "test-sa-unit"
    core.STORE.reset(sid)
    item = core.SA[0]
    miss = core.STORE.answer_short(sid, item, "不知道")
    check("不及格返回 passed=0", miss["passed"] == 0)
    prof = core.STORE.profile(sid)
    check("不及格进复习清单", any(g["point_id"] == "sa:" + item["id"] for g in prof["gaps"]),
          [g["point_id"] for g in prof["gaps"]])
    hit = core.STORE.answer_short(sid, item, item["answer"])
    check("照考点作答得满分", hit["score"] == 100, hit["score"])
    prof2 = core.STORE.profile(sid)
    check("满分后简答通过数 +1", prof2["overview"]["sa_passed"] == 1,
          prof2["overview"]["sa_passed"])
    core.STORE.reset(sid)


if __name__ == "__main__":
    print("简答判分")
    test_score()
    print("考前冲刺")
    test_sprint()
    print("简答记录")
    test_short_answer_store()
    print()
    if fails:
        print("失败 " + str(len(fails)) + " 项：" + "；".join(fails))
        sys.exit(1)
    print("新增功能检查全部通过")
