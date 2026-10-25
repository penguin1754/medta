#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""冒烟测试：自己起后端、打一轮接口、断言结果，结束后关闭。
用法（在 medta 目录下）：python tools/smoke_test.py
需要先把中文输出编码设好：
    $env:PYTHONIOENCODING="utf-8"; [Console]::OutputEncoding=[System.Text.Encoding]::UTF8
"""
import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PORT = 8799
BASE = "http://127.0.0.1:" + str(PORT)
SID = "smoke1"
fails = []


def check(name, ok, extra=""):
    print(("  [OK]   " if ok else "  [FAIL] ") + name + ("  " + extra if extra else ""))
    if not ok:
        fails.append(name)


def call(path, payload=None):
    url = BASE + path
    if payload is None:
        req = urllib.request.Request(url)
    else:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data,
                                     headers={"Content-Type": "application/json"},
                                     method="POST")
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode("utf-8"))


def wait_health():
    for _ in range(40):
        try:
            return call("/api/health")
        except Exception:
            time.sleep(0.5)
    raise SystemExit("后端没起来")


def main():
    # 冒烟测试忽略 .env、强制无令牌：即使本机填了真实令牌也不会消耗额度
    env = dict(os.environ, MEDTA_NO_ENV="1", MEDTA_ENGINE="coze",
               COZE_PAT="", COZE_BOT_ID="", COZE_BASE="https://api.coze.cn",
               COZE_MAX_CALLS="100", COZE_PER_USER="10")
    proc = subprocess.Popen([sys.executable, "backend/app.py", "--port", str(PORT)],
                            cwd=str(ROOT), env=env,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        h = wait_health()
        print("健康检查:", json.dumps(h, ensure_ascii=False))
        check("health 版本 v0.4", h.get("version") == "v0.4")
        check("health 知识卡 4 张", h.get("cards") == 4, "cards=" + str(h.get("cards")))
        check("health 自测题 4 道", h.get("quiz") == 4, "quiz=" + str(h.get("quiz")))
        check("health 带章节列表", bool(h.get("chapters")), str(h.get("chapters")))
        check("health 默认引擎为 coze 模式", h.get("mode") == "coze", str(h.get("mode")))
        check("未填令牌时 coze_ready=False", h.get("coze_ready") is False)
        check("health 带每人每日额度", h.get("user_limit") == 10 and h.get("user_used") == 0,
              str(h.get("user_used")) + "/" + str(h.get("user_limit")))

        page = urllib.request.urlopen(BASE + "/", timeout=10).read().decode("utf-8")
        check("首页可打开且含标题", "医学课程 AI 助教" in page, str(len(page)) + " 字节")
        check("首页已无病例模块", "病例" not in page)

        r1 = call("/api/ask", {"sid": SID, "question": "腋神经损伤会有什么表现？"})
        check("问答命中本地知识卡", r1.get("route") == "local_card" and not r1.get("refused"),
              "route=" + str(r1.get("route")))
        check("命中的答案带出处", bool(r1.get("citations")),
              json.dumps(r1.get("citations"), ensure_ascii=False)[:90])
        r2 = call("/api/ask", {"sid": SID, "question": "帮我写一篇马原期末论文"})
        check("越界问题明确拒答",
              bool(r2.get("refused")) and r2.get("route") in
              ("no_engine", "quota_exhausted", "coze_failed"), "route=" + str(r2.get("route")))

        cards = call("/api/cards?sid=" + SID)
        check("知识卡接口返回 4 张", len(cards) == 4, str(len(cards)))
        check("知识卡带 status 字段", all("status" in c for c in cards))
        cid = cards[0]["id"]
        rv1 = call("/api/cards/review", {"sid": SID, "card_id": cid, "known": True})
        check("速记「记住了」→ mastered", rv1.get("status") == "mastered")
        rv2 = call("/api/cards/review", {"sid": SID, "card_id": cid, "known": False})
        check("速记「没记住」→ learning", rv2.get("status") == "learning")
        check("速记返回学习概览", isinstance(rv2.get("overview"), dict))
        cards2 = call("/api/cards?sid=" + SID)
        check("重新拉卡能看到已标记状态",
              any(c["status"] == "learning" for c in cards2))

        quiz = call("/api/quiz?chapter=all&n=4")
        check("自测接口返回 4 题", quiz.get("total") == 4, "total=" + str(quiz.get("total")))
        items = quiz.get("items") or []
        check("下发题目不泄露答案", all("answer_index" not in i for i in items))
        good = call("/api/quiz/answer", {"sid": SID, "qid": items[0]["id"], "choice": 0})
        wrong = call("/api/quiz/answer", {"sid": SID, "qid": items[1]["id"], "choice": 3})
        check("答对：correct=True 且有解析", good.get("correct") is True and bool(good.get("explain")))
        check("答错：correct=False 且回正确答案",
              wrong.get("correct") is False and "answer_index" in wrong)

        prof = call("/api/profile/" + SID)
        o = prof.get("overview", {})
        check("档案：待复习知识点 >=1", o.get("open_gaps", 0) >= 1,
              "open_gaps=" + str(o.get("open_gaps")))
        check("档案：错题 >=1", o.get("wrong", 0) >= 1, "wrong=" + str(o.get("wrong")))
        check("档案：复习清单非空", len(prof.get("plan") or []) >= 1)
        check("档案：复习清单带出处", all(p.get("source") for p in (prof.get("plan") or [])))
        check("档案：章节掌握度有条目", len(prof.get("chapters") or []) >= 1)

        # 间隔重复：新卡立即到期 -> 记住后推到 1 天后 -> 没记住当场回到到期
        call("/api/reset", {"sid": "sched1"})
        due0 = call("/api/cards?sid=sched1&due=1")
        check("新会话 4 张卡全部到期", len(due0) == 4, str(len(due0)))
        c0 = call("/api/cards?sid=sched1")[0]
        r_known = call("/api/cards/review",
                       {"sid": "sched1", "card_id": c0["id"], "known": True})
        sch = r_known.get("schedule") or {}
        check("记住后间隔 1 天", sch.get("interval_days") == 1, str(sch.get("interval_days")))
        check("记住后不再到期", sch.get("due_ts", 0) > time.time())
        due1 = call("/api/cards?sid=sched1&due=1")
        check("到期列表少 1 张", len(due1) == 3, str(len(due1)))
        r_lapse = call("/api/cards/review",
                       {"sid": "sched1", "card_id": c0["id"], "known": False})
        check("没记住则当场重新到期",
              (r_lapse.get("schedule") or {}).get("due_ts", 1) <= time.time())
        due2 = call("/api/cards?sid=sched1&due=1")
        check("到期列表回到 4 张", len(due2) == 4, str(len(due2)))
        prof_s = call("/api/profile/sched1")
        ov = prof_s["overview"]
        check("档案含到期数与连续天数", "due" in ov and "streak" in ov,
              "due=" + str(ov.get("due")) + " streak=" + str(ov.get("streak")))
        check("活跃度窗口 35 天", len(prof_s.get("activity") or []) == 35)
        check("今天有学习记录", (prof_s["activity"][-1] or {}).get("n", 0) >= 1)
        check("复习节奏覆盖全部卡片", len(prof_s.get("sched") or []) == 4)

        src = call("/api/sources")
        check("资料来源含合规声明", "占位" in (src.get("note") or ""))

        call("/api/reset", {"sid": SID})
        p2 = call("/api/profile/" + SID)["overview"]
        check("清空记录后归零",
              p2["open_gaps"] == 0 and p2["wrong"] == 0 and p2["mastered"] == 0 and p2["events"] == 0)

        print()
        if fails:
            print("冒烟测试失败 " + str(len(fails)) + " 项：" + "；".join(fails))
            sys.exit(1)
        print("冒烟测试全部通过")
    finally:
        proc.terminate()


if __name__ == "__main__":
    main()
