#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""医学课程 AI 助教 · 学生端原型后端（零第三方依赖，只用 Python 标准库）。

启动：
    python backend/app.py            # 默认 127.0.0.1:8787
    python backend/app.py --port 9000
    MEDTA_HOST=0.0.0.0 python backend/app.py    # 需要同局域网演示时

凭据与额度（读 medta/.env，其次读环境变量）：
    MEDTA_ENGINE     coze（默认）| local
    COZE_PAT         Coze 个人访问令牌（只放服务端，绝不进前端/小程序）
    COZE_BOT_ID      发布到 API 渠道的 Bot ID
    COZE_BASE        https://api.coze.cn（默认）
    COZE_MAX_CALLS   全站累计调用上限，默认 100
    COZE_PER_USER    单个浏览器每天上限，默认 10
    COZE_TIMEOUT     单次调用超时秒数，默认 90

回答策略（见 answer_question）：
    1. 同一问题命中缓存               -> 直接返回，不消耗额度
    2. Coze 已配置且有余额            -> 调 Coze，同一 sid 复用 conversation_id
    3. Coze 未配置/额度用尽/调用失败  -> 回落本地知识卡
    4. 本地也没有依据                 -> 明确拒答，不编答案

学习闭环（判分与诊断全部是确定性代码，模型不参与）：
    课程问答 -> 知识点速记 -> 自测练习 -> 学习档案
    速记"没记住"和自测答错都会写入 knowledge gap，档案里据此生成复习清单。
"""
import json
import os
import re
import sqlite3
import sys
from datetime import date, timedelta
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

ROOT = Path(__file__).resolve().parent.parent
KNOW = ROOT / "knowledge"
FRONT = ROOT / "frontend"
DB_PATH = ROOT / "db" / "progress.db"
VERSION = "v0.4"

REFUSE_TEXT = "这个问题不在当前已审核的课程资料范围内，或者资料里没有相关依据，我不能作答。可以试着换一个更具体的问法（例如点出章节名或解剖学名词）。"
QUOTA_TEXT = "这个问题超出本地已审核资料范围，而在线模型额度已用完，所以我不能作答。可以试着换一个更具体的问法（例如点出章节名或解剖学名词）。"
FAIL_TEXT = "在线模型暂时不可用，本地资料里也没有这个问题的依据，所以我不能作答。请稍后再试，或换一个更具体的问法。"

_lock = threading.Lock()


def load_env_file():
    """把 medta/.env 读进 os.environ（不覆盖已存在的环境变量）。"""
    if os.environ.get("MEDTA_NO_ENV") == "1":
        return
    f = ROOT / ".env"
    if not f.exists():
        return
    for line in f.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k, v = k.strip(), v.strip()
        if k and not os.environ.get(k):
            os.environ[k] = v


load_env_file()


def _env_int(key, default):
    try:
        return int(os.environ.get(key) or default)
    except ValueError:
        return default


def _now():
    return int(time.time())


def _cache_key(text):
    """同一问题的缓存键：去掉空白与标点，忽略大小写。"""
    return re.sub(r"[\s\W_]+", "", text.lower())[:200]


def _load(name):
    with open(KNOW / name, encoding="utf-8") as f:
        return json.load(f)


CARDS = _load("cards.json")
QUIZ = _load("quiz.json")
CARD_BY_ID = {c["id"]: c for c in CARDS}
CARD_BY_POINT = {c["point_id"]: c for c in CARDS}
QUIZ_BY_ID = {q["id"]: q for q in QUIZ}
CHAPTERS = sorted({c["chapter"] for c in CARDS})


class EngineError(RuntimeError):
    pass


class Store:
    """匿名学习记录。sid 是前端生成的随机串，不含姓名学号。"""

    def __init__(self):
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        with _lock:
            self.conn.execute(
                "create table if not exists events(sid text, ts int, kind text, ref text, detail text)")
            self.conn.execute(
                "create table if not exists gaps(sid text, point_id text, label text, chapter text,"
                " count int, status text, primary key(sid, point_id))")
            self.conn.execute(
                "create table if not exists card_state(sid text, card_id text, point_id text,"
                " chapter text, label text, status text, reviews int, last_ts int,"
                " primary key(sid, card_id))")
            self.conn.execute(
                "create table if not exists quiz_state(sid text, qid text, point_id text,"
                " chapter text, stem text, chosen int, answer_index int, is_correct int,"
                " last_ts int, primary key(sid, qid))")
            self.conn.execute(
                "create table if not exists answer_cache(qkey text primary key,"
                " answer text, ts int)")
            self.conn.execute(
                "create table if not exists meta(key text primary key, value int)")
            self.conn.execute(
                "create table if not exists chat_state(sid text primary key,"
                " conversation_id text, ts int)")
            self.conn.execute(
                "create table if not exists usage(sid text, day text, calls int,"
                " primary key(sid, day))")
            self._migrate()
            self.conn.commit()

    def _migrate(self):
        """给旧的 card_state 补上间隔重复所需字段（就地升级，不丢历史记录）。
        注意：本方法在 __init__ 的锁内调用，自己不再取锁。"""
        cols = {r[1] for r in self.conn.execute("pragma table_info(card_state)")}
        for name, decl in (("due_ts", "integer default 0"),
                           ("interval_days", "integer default 0"),
                           ("ease", "real default 2.5"),
                           ("lapses", "integer default 0")):
            if name not in cols:
                self.conn.execute("alter table card_state add column " + name + " " + decl)

    def bump(self, key, n=1):
        with _lock:
            self.conn.execute(
                "insert into meta values(?,?) on conflict(key) do update set value=value+?",
                (key, n, n))
            self.conn.commit()
            row = self.conn.execute("select value from meta where key=?", (key,)).fetchone()
        return int(row[0]) if row else n

    def get_int(self, key, default=0):
        with _lock:
            row = self.conn.execute("select value from meta where key=?", (key,)).fetchone()
        return int(row[0]) if row else default

    def log(self, sid, kind, ref, detail):
        with _lock:
            self.conn.execute("insert into events values(?,?,?,?,?)",
                              (sid, _now(), kind, str(ref)[:200],
                               json.dumps(detail, ensure_ascii=False)[:500]))
            self.conn.commit()

    def record_gap(self, sid, point_id, label, chapter):
        with _lock:
            self.conn.execute(
                "insert into gaps values(?,?,?,?,1,'open')"
                " on conflict(sid, point_id) do update set count=count+1, status='open'",
                (sid, point_id, label, chapter))
            self.conn.commit()

    def close_gap(self, sid, point_id):
        with _lock:
            self.conn.execute("update gaps set status='reviewed' where sid=? and point_id=?",
                              (sid, point_id))
            self.conn.commit()

    def sched_state(self, sid, card_id):
        """单张卡的复习节奏。没学过当成立即到期，所以新卡永远先出现在今日复习里。"""
        with _lock:
            row = self.conn.execute(
                "select status, reviews, interval_days, ease, lapses, due_ts"
                " from card_state where sid=? and card_id=?", (sid, card_id)).fetchone()
        if not row:
            return {"status": "unseen", "reviews": 0, "interval_days": 0,
                    "ease": 2.5, "lapses": 0, "due_ts": 0}
        return {"status": row[0], "reviews": row[1], "interval_days": row[2],
                "ease": round(row[3], 2), "lapses": row[4], "due_ts": row[5]}

    def review_card(self, sid, card, known):
        """间隔重复（SM-2 简化版）：记住就拉长间隔，没记住就当场清零重来。

        间隔序列 1 天 -> 3 天 -> 上次间隔 x ease（上限 180 天）；
        没记住则间隔归 0（立刻到期）、ease 下调、lapses+1。
        """
        st = self.sched_state(sid, card["id"])
        ease = st["ease"]
        if known:
            iv = st["interval_days"]
            iv = 1 if iv <= 0 else (3 if iv == 1 else int(round(iv * ease)))
            iv = min(iv, 180)
            ease = min(2.8, ease + 0.1)
            status, lapses = "mastered", st["lapses"]
        else:
            iv, status = 0, "learning"
            ease = max(1.3, ease - 0.2)
            lapses = st["lapses"] + 1
        due = _now() + iv * 86400
        with _lock:
            self.conn.execute(
                "insert into card_state(sid, card_id, point_id, chapter, label, status,"
                " reviews, last_ts, due_ts, interval_days, ease, lapses)"
                " values(?,?,?,?,?,?,1,?,?,?,?,?)"
                " on conflict(sid, card_id) do update set status=excluded.status,"
                " reviews=reviews+1, last_ts=excluded.last_ts, due_ts=excluded.due_ts,"
                " interval_days=excluded.interval_days, ease=excluded.ease,"
                " lapses=excluded.lapses",
                (sid, card["id"], card["point_id"], card["chapter"], card["front"],
                 status, _now(), due, iv, ease, lapses))
            self.conn.commit()
        if known:
            self.close_gap(sid, card["point_id"])
        else:
            self.record_gap(sid, card["point_id"], card["front"], card["chapter"])
        return {"status": status, "interval_days": iv, "ease": round(ease, 2),
                "due_ts": due, "lapses": lapses}

    def answer_quiz(self, sid, item, chosen):
        ok = 1 if chosen == item["answer_index"] else 0
        with _lock:
            self.conn.execute(
                "insert into quiz_state values(?,?,?,?,?,?,?,?,?)"
                " on conflict(sid, qid) do update set chosen=excluded.chosen,"
                " is_correct=excluded.is_correct, last_ts=excluded.last_ts",
                (sid, item["id"], item["point_id"], item["chapter"], item["stem"],
                 chosen, item["answer_index"], ok, _now()))
            self.conn.commit()
        if not ok:
            self.record_gap(sid, item["point_id"], item["stem"], item["chapter"])
        return ok

    def card_status(self, sid, card_id):
        with _lock:
            row = self.conn.execute(
                "select status from card_state where sid=? and card_id=?",
                (sid, card_id)).fetchone()
        return row[0] if row else "unseen"

    def cache_get(self, key):
        with _lock:
            row = self.conn.execute(
                "select answer from answer_cache where qkey=?", (key,)).fetchone()
        return row[0] if row else None

    def cache_put(self, key, answer):
        with _lock:
            self.conn.execute(
                "insert into answer_cache values(?,?,?)"
                " on conflict(qkey) do update set answer=excluded.answer, ts=excluded.ts",
                (key, answer, _now()))
            self.conn.commit()

    def conversation(self, sid):
        """取该浏览器上次的 Coze 会话，用于连续追问。"""
        with _lock:
            row = self.conn.execute(
                "select conversation_id from chat_state where sid=?", (sid,)).fetchone()
        return row[0] if row else ""

    def set_conversation(self, sid, conversation_id):
        if not conversation_id:
            return
        with _lock:
            self.conn.execute(
                "insert into chat_state values(?,?,?)"
                " on conflict(sid) do update set conversation_id=excluded.conversation_id,"
                " ts=excluded.ts", (sid, conversation_id, _now()))
            self.conn.commit()

    def clear_conversation(self, sid):
        with _lock:
            self.conn.execute("delete from chat_state where sid=?", (sid,))
            self.conn.commit()

    def calls_today(self, sid):
        with _lock:
            row = self.conn.execute(
                "select calls from usage where sid=? and day=?",
                (sid, date.today().isoformat())).fetchone()
        return int(row[0]) if row else 0

    def bump_today(self, sid, n=1):
        with _lock:
            self.conn.execute(
                "insert into usage values(?,?,?) on conflict(sid, day)"
                " do update set calls=calls+?", (sid, date.today().isoformat(), n, n))
            self.conn.commit()
            row = self.conn.execute(
                "select calls from usage where sid=? and day=?",
                (sid, date.today().isoformat())).fetchone()
        return int(row[0]) if row else n

    def profile(self, sid):
        with _lock:
            cards = self.conn.execute(
                "select card_id, status, interval_days, ease, due_ts, lapses"
                " from card_state where sid=?", (sid,)).fetchall()
            quiz = self.conn.execute(
                "select qid, chosen, answer_index, is_correct, stem, chapter, point_id"
                " from quiz_state where sid=?", (sid,)).fetchall()
            gaps = self.conn.execute(
                "select point_id, label, chapter, count, status from gaps where sid=?"
                " order by status asc, count desc", (sid,)).fetchall()
            events = self.conn.execute(
                "select count(*) from events where sid=?", (sid,)).fetchone()
        state = {r[0]: r[1] for r in cards}
        mastered = sum(1 for v in state.values() if v == "mastered")
        learning = sum(1 for v in state.values() if v == "learning")

        chapters = []
        for ch in CHAPTERS:
            ids = [c["id"] for c in CARDS if c["chapter"] == ch]
            m = sum(1 for i in ids if state.get(i) == "mastered")
            chapters.append({"chapter": ch, "total": len(ids), "mastered": m,
                             "rate": round(100.0 * m / len(ids)) if ids else 0})

        answered = len(quiz)
        correct = sum(1 for r in quiz if r[3])
        wrong = [{"qid": r[0], "stem": r[4], "chapter": r[5],
                  "your_answer": r[1], "answer_index": r[2]} for r in quiz if not r[3]]

        open_gaps = [{"point_id": g[0], "label": g[1], "chapter": g[2], "count": g[3]}
                     for g in gaps if g[4] == "open"]
        reviewed = [{"point_id": g[0], "label": g[1], "chapter": g[2], "count": g[3]}
                    for g in gaps if g[4] != "open"]

        plan = []
        for g in open_gaps:
            card = CARD_BY_POINT.get(g["point_id"])
            plan.append({
                "gap": g["label"],
                "chapter": g["chapter"],
                "action": ("先看知识卡「" + card["front"] + "」，再回自测练习重做对应题目。")
                          if card else "复习该知识点，然后在自测练习里重做对应题目。",
                "source": card["source"] if card else None,
            })

        now = _now()
        by_id = {r[0]: r for r in cards}
        sched, due_now = [], 0
        for c in CARDS:
            r = by_id.get(c["id"])
            due_ts = r[4] if r else 0
            if due_ts <= now:
                due_now += 1
            sched.append({"card_id": c["id"], "front": c["front"], "chapter": c["chapter"],
                          "status": r[1] if r else "unseen",
                          "interval_days": r[2] if r else 0,
                          "ease": round(r[3], 2) if r else 2.5,
                          "lapses": r[5] if r else 0,
                          "due_in_days": max(0, int((due_ts - now) // 86400)) if due_ts else 0})

        act = {}
        with _lock:
            for d, n in self.conn.execute(
                    "select date(ts,'unixepoch','localtime') d, count(*) c from events"
                    " where sid=? group by d", (sid,)).fetchall():
                act[d] = n
        days, today = [], date.today()
        for k in range(34, -1, -1):
            d = (today - timedelta(days=k)).isoformat()
            days.append({"date": d, "n": act.get(d, 0)})
        streak, probe = 0, today
        if act.get(today.isoformat(), 0) == 0:
            probe = today - timedelta(days=1)
        while act.get(probe.isoformat(), 0) > 0:
            streak += 1
            probe = probe - timedelta(days=1)

        return {
            "sid": sid,
            "overview": {
                "cards_total": len(CARDS), "mastered": mastered, "learning": learning,
                "unseen": len(CARDS) - mastered - learning,
                "answered": answered, "correct": correct,
                "accuracy": round(100.0 * correct / answered) if answered else 0,
                "open_gaps": len(open_gaps), "wrong": len(wrong),
                "events": int(events[0]) if events else 0,
                "due": due_now, "streak": streak,
            },
            "chapters": chapters,
            "gaps": open_gaps,
            "reviewed": reviewed,
            "wrong": wrong,
            "plan": plan,
            "sched": sched,
            "activity": days,
        }

    def reset(self, sid):
        with _lock:
            for t in ("events", "gaps", "card_state", "quiz_state"):
                self.conn.execute("delete from " + t + " where sid=?", (sid,))
            self.conn.execute("delete from chat_state where sid=?", (sid,))
            self.conn.commit()


class LocalCardEngine:
    """本地知识卡引擎：命中已审核资料就回答，不消耗任何在线额度。"""

    name = "local"

    def ask(self, question):
        q = question.strip()
        best, score = None, 0
        for c in CARDS:
            s = sum(1 for k in c["keywords"] if k in q)
            if s > score:
                best, score = c, s
        if best is None or score == 0:
            return {"refused": True, "answer": "", "reason": REFUSE_TEXT, "citations": [],
                    "source": "none"}
        return {"refused": False, "answer": best["answer"],
                "citations": [dict(best["source"], chapter=best["chapter"])],
                "matched": {"id": best["id"], "front": best["front"],
                            "chapter": best["chapter"], "topic": best["topic"]},
                "source": "local_card"}


def _api_error_text(raw, http_code=0):
    """把 Coze 的错误体转成一行人话。Coze 出错时也常返回 HTTP 200，必须看 code。"""
    text = (raw or "").strip()
    try:
        obj = json.loads(text)
    except ValueError:
        snippet = " ".join(text.split())[:200]
        return "Coze 接口返回 HTTP " + str(http_code or "?") + "：" + (snippet or "空响应")
    if not isinstance(obj, dict):
        return "Coze 接口返回了无法识别的内容"
    code = obj.get("code")
    if code in (0, "0", None):
        return ""
    msg = obj.get("msg") or obj.get("message") or "未知错误"
    hint = {4101: "COZE_PAT 无效或已过期",
            4200: "Bot ID 不存在，或该 Bot 没有发布到 API 渠道"}.get(code, "")
    return "Coze " + str(code) + "：" + str(msg) + ("（" + hint + "）" if hint else "")


def parse_coze_stream(text):
    """解析 v3/chat 的 SSE。官方文档中 data: 后面直接是消息对象，不是 {"message": ...}。"""
    parts, completed = [], ""
    conv_id, usage, status, error = "", {}, "", ""
    event = ""
    for raw in (text or "").splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("event:"):
            event = line[6:].strip()
            continue
        if not line.startswith("data:"):
            continue
        payload = line[5:].strip()
        if payload == "[DONE]":
            break
        try:
            data = json.loads(payload)
        except ValueError:
            continue
        if not isinstance(data, dict):
            continue
        name = event or str(data.get("event") or "")
        if name in ("conversation.chat.failed", "error"):
            error = _api_error_text(payload) or "Coze 对话失败"
            continue
        if name.startswith("conversation.message."):
            conv_id = str(data.get("conversation_id") or conv_id)
            if data.get("type") == "answer":
                if name.endswith(".delta"):
                    parts.append(str(data.get("content") or ""))
                elif name.endswith(".completed"):
                    completed = str(data.get("content") or completed)
        elif name == "conversation.chat.completed":
            conv_id = str(data.get("conversation_id") or conv_id)
            status = str(data.get("status") or status)
            usage = data.get("usage") or usage
    answer = "".join(parts).strip() or completed.strip()
    return {"answer": answer, "conversation_id": conv_id, "usage": usage,
            "status": status, "error": error}


class CozeEngine:
    """Coze v3/chat 客户端（零依赖）。接口文档：docs.coze.cn/developer_guides/chat_v3

    流式响应里 `data:` 后面直接就是消息对象；鉴权和参数错误则常以
    HTTP 200 + {"code": ...} 返回。两种形态都在这里处理。
    """

    name = "coze"

    def __init__(self, pat, bot_id, base):
        self.pat = pat
        self.bot_id = bot_id
        self.base = base.rstrip("/")

    def ask(self, question, conversation_id="", user_id="medta_student"):
        payload = {
            "bot_id": self.bot_id,
            "user_id": user_id,
            "stream": True,
            "auto_save_history": True,
            "additional_messages": [{"role": "user", "content": question}],
        }
        if conversation_id:
            payload["conversation_id"] = conversation_id
        raw = self._post("/v3/chat", payload)

        # 出错时 Coze 直接回一段 JSON（HTTP 可能仍是 200）
        if raw.lstrip().startswith("{"):
            try:
                obj = json.loads(raw)
            except ValueError as exc:
                raise EngineError("Coze 返回了无法解析的 JSON") from exc
            err = _api_error_text(raw)
            if err:
                raise EngineError(err)
            data = obj.get("data") or {}
            chat_id = str(data.get("id") or "")
            conv = str(data.get("conversation_id") or conversation_id)
            if not chat_id:
                raise EngineError("Coze 没有返回 chat_id")
            answer = self._poll_answer(chat_id, conv)
            if not answer:
                raise EngineError("Coze 没有返回答案内容")
            return {"answer": answer, "conversation_id": conv, "usage": {}, "source": "coze"}

        parsed = parse_coze_stream(raw)
        if parsed["error"]:
            raise EngineError(parsed["error"])
        if not parsed["answer"]:
            raise EngineError("Coze 没有返回答案内容（可能被安全策略拦截，或 Bot 未发布到 API 渠道）")
        return {"answer": parsed["answer"],
                "conversation_id": parsed["conversation_id"] or conversation_id,
                "usage": parsed["usage"], "source": "coze"}

    def _headers(self):
        return {"Authorization": "Bearer " + self.pat,
                "Content-Type": "application/json"}

    def _post(self, path, payload):
        req = urllib.request.Request(
            self.base + path,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers=self._headers(), method="POST")
        try:
            with urllib.request.urlopen(req, timeout=COZE_TIMEOUT) as resp:
                return resp.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", "replace")
            raise EngineError(_api_error_text(raw, exc.code)) from exc
        except Exception as exc:
            raise EngineError("网络请求失败：" + str(exc)[:160]) from exc

    def _get(self, path):
        req = urllib.request.Request(self.base + path,
                                     headers={"Authorization": "Bearer " + self.pat},
                                     method="GET")
        try:
            with urllib.request.urlopen(req, timeout=COZE_TIMEOUT) as resp:
                raw = resp.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", "replace")
            raise EngineError(_api_error_text(raw, exc.code)) from exc
        except Exception as exc:
            raise EngineError("网络请求失败：" + str(exc)[:160]) from exc
        try:
            obj = json.loads(raw)
        except ValueError as exc:
            raise EngineError("Coze 返回了无法解析的 JSON") from exc
        err = _api_error_text(raw)
        if err:
            raise EngineError(err)
        return obj

    def _poll_answer(self, chat_id, conversation_id):
        """非流式兜底：轮询对话状态，再取最后一条 answer 消息。"""
        qs = urllib.parse.urlencode({"conversation_id": conversation_id, "chat_id": chat_id})
        deadline = time.time() + COZE_TIMEOUT
        while time.time() < deadline:
            data = self._get("/v3/chat/retrieve?" + qs).get("data") or {}
            status = data.get("status")
            if status in ("completed", "required_action", "canceled", "failed"):
                if status == "failed":
                    err = data.get("last_error") or {}
                    raise EngineError(_api_error_text(json.dumps(err, ensure_ascii=False))
                                      or "Coze 对话失败")
                break
            time.sleep(1)
        msgs = self._get("/v3/conversation/message/list?" + qs).get("data") or []
        for msg in reversed(msgs):
            if msg.get("type") == "answer" and msg.get("role") == "assistant":
                return str(msg.get("content") or "").strip()
        return ""


STORE = Store()
COZE_MAX_CALLS = max(1, _env_int("COZE_MAX_CALLS", 100))
COZE_PER_USER = max(1, _env_int("COZE_PER_USER", 10))
COZE_TIMEOUT = max(10, _env_int("COZE_TIMEOUT", 90))
ENGINE_MODE = (os.environ.get("MEDTA_ENGINE") or "coze").strip().lower()
_last_coze_error = {"msg": "", "ts": 0}


def _note_coze_error(msg):
    global _last_coze_error
    _last_coze_error = {"msg": (msg or "")[:300], "ts": _now()}
    print("[coze] " + (msg or ""), file=sys.stderr)


def coze_available():
    return bool((os.environ.get("COZE_PAT") or "").strip()
                and (os.environ.get("COZE_BOT_ID") or "").strip())


def coze_engine():
    return CozeEngine(os.environ.get("COZE_PAT", "").strip(),
                      os.environ.get("COZE_BOT_ID", "").strip(),
                      os.environ.get("COZE_BASE", "https://api.coze.cn"))


def engine_name():
    if ENGINE_MODE == "local":
        return "local"
    return "coze" if coze_available() else "local"


def _quota(sid):
    return {"coze_calls": STORE.get_int("coze_calls", 0), "coze_max": COZE_MAX_CALLS,
            "user_used": STORE.calls_today(sid), "user_limit": COZE_PER_USER}


def answer_question(question, sid="anon"):
    """Coze 优先；缓存省额度，本地知识卡在额度用尽或接口失败时兜底。"""
    conv = STORE.conversation(sid)
    ck = _cache_key(question)
    # 已经进入多轮会话后不再读缓存：同一个问句在不同上下文里的答案可能不同
    hit = None if conv else STORE.cache_get(ck)
    if hit:
        out = {"refused": False, "answer": hit, "citations": [], "source": "coze_cache",
               "demo": False, "route": "coze", "cached": True}
        out.update(_quota(sid))
        return out

    local = LocalCardEngine().ask(question)
    local_hit = not local.get("refused")

    if ENGINE_MODE != "coze" or not coze_available():
        if local_hit:
            out = dict(local)
            out.update({"demo": False, "route": "local_card"})
        else:
            out = {"refused": True, "answer": "", "citations": [], "reason": REFUSE_TEXT,
                   "demo": False, "route": "no_engine"}
        out.update(_quota(sid))
        return out

    used, mine = STORE.get_int("coze_calls", 0), STORE.calls_today(sid)
    if used >= COZE_MAX_CALLS or mine >= COZE_PER_USER:
        if local_hit:
            out = dict(local)
            out["demo"] = False
            out["route"] = "local_fallback"
            out["note"] = ("今天的个人提问额度用完了，先给本地知识卡里的依据，明天自动恢复。"
                           if mine >= COZE_PER_USER
                           else "在线调用总额度用完了，先给本地知识卡里的依据。")
        else:
            out = {"refused": True, "answer": "", "citations": [], "reason": QUOTA_TEXT,
                   "demo": False, "route": "quota_exhausted", "quota_exceeded": True}
        out.update(_quota(sid))
        return out

    STORE.bump("coze_calls", 1)
    STORE.bump_today(sid, 1)
    try:
        res = coze_engine().ask(question, conv, "medta_" + sid)
        STORE.set_conversation(sid, res.get("conversation_id"))
        if not conv:
            STORE.cache_put(ck, res["answer"])
        out = {"refused": False, "answer": res["answer"], "citations": [],
               "source": "coze", "demo": False, "route": "coze"}
        out.update(_quota(sid))
        return out
    except EngineError as exc:
        # 调用失败不计入额度，避免配置错误把 100 次额度试没
        STORE.bump("coze_calls", -1)
        STORE.bump_today(sid, -1)
        _note_coze_error(str(exc))
        if local_hit:
            out = dict(local)
            out["demo"] = False
            out["route"] = "local_fallback"
            out["note"] = "在线模型暂时不可用，先给出本地知识卡里的依据。"
        else:
            out = {"refused": True, "answer": "", "citations": [], "reason": FAIL_TEXT,
                   "demo": False, "route": "coze_failed", "error": str(exc)[:160]}
        out.update(_quota(sid))
        return out


class Handler(BaseHTTPRequestHandler):
    server_version = "MedTA/0.4"

    def log_message(self, fmt, *args):
        pass

    def _send(self, obj, code=200):
        data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _body(self):
        n = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(n) if n else b"{}"
        try:
            return json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            return {}

    @staticmethod
    def _sid(body):
        sid = str(body.get("sid") or "anon")[:64]
        return re.sub(r"[^0-9a-zA-Z_-]", "", sid) or "anon"

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        if path in ("/", "/index.html"):
            data = (FRONT / "index.html").read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        if path == "/api/health":
            qs = parse_qs(parsed.query)
            sid = re.sub(r"[^0-9a-zA-Z_-]", "", (qs.get("sid") or ["anon"])[0])[:64] or "anon"
            out = {"version": VERSION, "engine": engine_name(), "mode": ENGINE_MODE,
                   "coze_ready": coze_available(),
                   "last_error": _last_coze_error["msg"], "cards": len(CARDS),
                   "quiz": len(QUIZ), "chapters": CHAPTERS}
            out.update(_quota(sid))
            self._send(out)
            return
        if path == "/api/cards":
            qs = parse_qs(parsed.query)
            sid = re.sub(r"[^0-9a-zA-Z_-]", "", (qs.get("sid") or ["anon"])[0])[:64] or "anon"
            only_due = (qs.get("due") or ["0"])[0] in ("1", "true", "yes")
            now = _now()
            out = []
            for c in CARDS:
                st = STORE.sched_state(sid, c["id"])
                if only_due and st["due_ts"] > now:
                    continue
                out.append({"id": c["id"], "point_id": c["point_id"],
                            "chapter": c["chapter"], "topic": c["topic"],
                            "front": c["front"], "answer": c["answer"],
                            "source": c["source"], "origin": c.get("origin", "placeholder"),
                            "status": st["status"], "due_ts": st["due_ts"],
                            "interval_days": st["interval_days"], "ease": st["ease"],
                            "reviews": st["reviews"], "lapses": st["lapses"]})
            self._send(out)
            return
        if path == "/api/quiz":
            qs = parse_qs(parsed.query)
            chapter = (qs.get("chapter") or ["all"])[0]
            try:
                n = max(1, min(20, int((qs.get("n") or ["4"])[0])))
            except ValueError:
                n = 4
            pool = [q for q in QUIZ if chapter == "all" or q["chapter"] == chapter]
            if not pool:
                pool = QUIZ
            items = [{"id": q["id"], "chapter": q["chapter"], "stem": q["stem"],
                      "options": q["options"], "origin": q.get("origin", "placeholder")}
                     for q in pool[:n]]
            self._send({"chapter": chapter, "total": len(items), "items": items})
            return
        if path == "/api/sources":
            docs = {}
            for c in CARDS:
                d = docs.setdefault(c["source"]["doc"],
                                    {"doc": c["source"]["doc"], "cards": 0, "quiz": 0,
                                     "locators": []})
                d["cards"] += 1
                if c["source"].get("locator"):
                    d["locators"].append(c["source"]["locator"])
            for q in QUIZ:
                d = docs.setdefault(q["source"]["doc"],
                                    {"doc": q["source"]["doc"], "cards": 0, "quiz": 0,
                                     "locators": []})
                d["quiz"] += 1
            self._send({"docs": list(docs.values()),
                        "note": "本原型内容为占位示例，正式提交前必须替换为团队整理的课程复习资料。"
                                "系统不采集姓名与学号，也不需要访问学校任何系统。"})
            return
        m = re.fullmatch(r"/api/profile/([0-9a-zA-Z_-]{1,64})", path)
        if m:
            self._send(STORE.profile(m.group(1)))
            return
        self._send({"error": "not found"}, 404)

    def do_POST(self):
        path = urlparse(self.path).path
        body = self._body()
        sid = self._sid(body)

        if path == "/api/ask":
            q = str(body.get("question") or "").strip()
            if not q:
                self._send({"error": "问题为空"}, 400)
                return
            result = answer_question(q, sid)
            STORE.log(sid, "ask", q, {"route": result.get("route"),
                                      "refused": result.get("refused")})
            self._send(result)
            return

        if path == "/api/cards/review":
            card = CARD_BY_ID.get(str(body.get("card_id") or ""))
            if not card:
                self._send({"error": "卡片不存在"}, 404)
                return
            known = bool(body.get("known"))
            res = STORE.review_card(sid, card, known)
            STORE.log(sid, "card_review", card["id"], {"known": known})
            prof = STORE.profile(sid)
            self._send({"card_id": card["id"], "known": known, "status": res["status"],
                        "schedule": res, "overview": prof["overview"],
                        "due": prof["overview"]["due"]})
            return

        if path == "/api/quiz/answer":
            item = QUIZ_BY_ID.get(str(body.get("qid") or ""))
            if not item:
                self._send({"error": "题目不存在"}, 404)
                return
            try:
                chosen = int(body.get("choice"))
            except (TypeError, ValueError):
                self._send({"error": "请先选择一个选项"}, 400)
                return
            if chosen < 0 or chosen >= len(item["options"]):
                self._send({"error": "选项超出范围"}, 400)
                return
            ok = STORE.answer_quiz(sid, item, chosen)
            STORE.log(sid, "quiz_answer", item["id"], {"chosen": chosen, "correct": bool(ok)})
            self._send({"qid": item["id"], "correct": bool(ok), "chosen": chosen,
                        "answer_index": item["answer_index"], "explain": item["explain"],
                        "source": item["source"], "point_id": item["point_id"]})
            return

        if path == "/api/reset":
            STORE.reset(sid)
            STORE.clear_conversation(sid)
            self._send({"ok": True, "sid": sid})
            return

        self._send({"error": "not found"}, 404)


def main():
    port = 8787
    if "--port" in sys.argv:
        port = int(sys.argv[sys.argv.index("--port") + 1])
    host = os.environ.get("MEDTA_HOST", "127.0.0.1")
    if "--host" in sys.argv:
        host = sys.argv[sys.argv.index("--host") + 1]
    httpd = ThreadingHTTPServer((host, port), Handler)
    print("医学课程 AI 助教（学生端原型）已启动：http://" + host + ":" + str(port))
    if host == "0.0.0.0":
        print("  已对外监听，同网段设备请用本机 IP 访问，例如 http://192.168.x.x:" + str(port))
    print("  引擎=" + engine_name() + "（" + ENGINE_MODE + "）  知识卡=" + str(len(CARDS))
          + "  自测题=" + str(len(QUIZ))
          + "  Coze 额度=" + str(STORE.get_int("coze_calls", 0)) + "/" + str(COZE_MAX_CALLS)
          + "  每人每天=" + str(COZE_PER_USER))
    if not coze_available():
        print("  提示：COZE_PAT 未填写，当前只能用本地知识卡。")
    httpd.serve_forever()


if __name__ == "__main__":
    main()
