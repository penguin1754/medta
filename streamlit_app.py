#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Streamlit 版医学课程 AI 助教。

本地启动：
    streamlit run streamlit_app.py

Streamlit Community Cloud：
    入口文件填 streamlit_app.py，在 Secrets 里填 COZE_PAT / COZE_BOT_ID。
"""
from __future__ import annotations

import html
import os
import secrets
import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

st.set_page_config(
    page_title="医学课程 AI 助教 · 系统解剖学",
    page_icon="🫀",
    layout="wide",
    initial_sidebar_state="expanded",
)


def _load_secrets():
    """把 Streamlit Cloud 的 Secrets 注入环境变量，供 backend/app.py 读取。"""
    try:
        secrets_map = st.secrets
    except Exception:
        return
    for key in ("COZE_PAT", "COZE_BOT_ID", "COZE_BASE", "MEDTA_ENGINE",
                "COZE_MAX_CALLS", "COZE_PER_USER", "COZE_TIMEOUT"):
        try:
            if key in secrets_map and not os.environ.get(key):
                os.environ[key] = str(secrets_map[key])
        except Exception:
            continue


_load_secrets()

import backend.app as core  # noqa: E402  （必须先注入 Secrets 再导入）


CSS = """
<style>
:root{
  --ground:#E8E6DF; --paper:#FCFBF7; --card:#FFFFFF; --tint:#F3F1E9;
  --ink:#191A17; --ink2:#3B3D37; --mute:#6C6E63;
  --line:#DCD9CE; --art:#B3352A; --vein:#2F5B82;
  --ease:cubic-bezier(.2,.7,.3,1);
}
[data-testid="stAppViewContainer"]{background:var(--ground);}
[data-testid="stHeader"]{background:transparent;}
[data-testid="stMainBlockContainer"]{
  max-width:1000px;background:var(--paper);padding:2.6rem 3.2rem 5rem;
  box-shadow:0 22px 60px -18px rgba(20,22,18,.35);border-radius:0 0 3px 3px;
}
html, body, [class*="css"]{font-family:"Microsoft YaHei","PingFang SC","Noto Sans SC",sans-serif;}
h1,h2,h3{font-family:"Songti SC","SimSun","宋体",serif !important;font-weight:500 !important;
  letter-spacing:.02em;color:var(--ink);}
[data-testid="stSidebar"]{background:#171A18;}
[data-testid="stSidebar"] *{color:#EAE8DF;}
[data-testid="stSidebar"] [role="radiogroup"] label{
  padding:.45rem .6rem;border-radius:2px;font-size:14px;letter-spacing:.03em;
}
[data-testid="stSidebar"] [role="radiogroup"] label:hover{background:rgba(255,255,255,.07);}
.hero-kicker{font-size:11px;letter-spacing:.24em;color:var(--mute);text-transform:uppercase;}
.hero-title{font-family:"Songti SC","SimSun",serif;font-size:44px;line-height:1.18;
  margin:.25rem 0 0;font-weight:400;letter-spacing:.02em;}
.hero-lede{color:var(--mute);max-width:36em;margin:.7rem 0 1.5rem;font-size:15px;line-height:1.9;}
.rule{height:1px;background:var(--line);margin:0 0 1.6rem;}
.panel-kicker{font-size:11px;letter-spacing:.2em;color:var(--art);margin-bottom:.2rem;}
.side-brand{font-family:"Songti SC","SimSun",serif;font-size:26px;letter-spacing:.16em;
  color:#F6F4EA;margin:.6rem 0 .1rem;}
.side-sub{font-size:11px;letter-spacing:.18em;color:#98A094;margin-bottom:1.2rem;}
.side-stat{font-size:13px;line-height:1.8;color:#EAE8DF;}
.side-stat b{font-family:"Songti SC","SimSun",serif;font-size:24px;font-weight:400;color:#F6F4EA;}
.side-stat span{color:#98A094;font-size:12px;}
.card-front{font-family:"Songti SC","SimSun",serif;font-size:28px;line-height:1.55;
  padding:.4rem 0 .2rem;color:var(--ink);}
.cite-box{border-left:2px solid var(--vein);background:#E7EEF5;padding:.6rem .9rem;
  font-size:13px;color:var(--ink2);margin:.5rem 0;}
.ask-meta{font-size:12.5px;color:var(--mute);margin-top:.4rem;}
[data-testid="stChatMessage"]{background:var(--card);border:1px solid var(--line);
  border-radius:3px;padding:14px 18px;box-shadow:0 1px 0 rgba(0,0,0,.03);}
[data-testid="stChatMessage"] p{font-size:15.5px;line-height:1.9;}
.stButton>button{border-radius:2px;border:1px solid var(--ink);background:transparent;
  color:var(--ink);font-size:13.5px;letter-spacing:.02em;min-height:2.4rem;}
.stButton>button:hover{background:var(--ink);color:var(--paper);border-color:var(--ink);}
.stButton>button[kind="primary"]{background:var(--art);color:#fff;border-color:var(--art);}
.stButton>button[kind="primary"]:hover{background:#8E2A21;border-color:#8E2A21;}
[data-testid="stMetricValue"]{font-family:"Songti SC","SimSun",serif;font-weight:400;}
[data-testid="stVerticalBlockBorderWrapper"]{border-color:var(--line) !important;
  background:var(--card);border-radius:3px;}
/* ══ 动效层：全部挂在真实状态变化上 ══════════════════════════ */
@keyframes softIn{from{opacity:0;transform:translateY(7px)}to{opacity:1;transform:none}}
@keyframes panelIn{from{opacity:0;transform:translateY(9px)}to{opacity:1;transform:none}}
@keyframes pageTurn{from{opacity:0;transform:perspective(900px) rotateX(9deg) translateY(10px)}to{opacity:1;transform:none}}
@keyframes stampIn{from{opacity:0;transform:rotate(-8deg) scale(1.55)}to{opacity:1;transform:rotate(-8deg) scale(1)}}
@keyframes cellIn{from{opacity:0;transform:scale(.55)}to{opacity:1;transform:none}}
@keyframes noteIn{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:none}}
@keyframes barGrow{from{transform:scaleX(0)}to{transform:scaleX(1)}}
@keyframes ringDraw{from{stroke-dashoffset:289}}

.hero-kicker{animation:softIn .46s var(--ease) both}
.hero-title{animation:softIn .58s var(--ease) .06s both}
.hero-lede{animation:softIn .58s var(--ease) .12s both}
.rule{animation:softIn .5s var(--ease) .2s both}
.panel-kicker{animation:softIn .4s var(--ease) both}
[data-testid="stVerticalBlockBorderWrapper"]{animation:panelIn .38s var(--ease) both}
.st-key-cardbox,.st-key-quizbox{background:var(--card);border-radius:3px;
  animation:panelIn .38s var(--ease) both}
[data-testid="stAlert"]{animation:softIn .32s var(--ease) both}
[data-testid="stChatMessage"]{animation:noteIn .34s var(--ease) both}
.card-front{animation:pageTurn .52s var(--ease) both}
.cite-box{animation:softIn .34s var(--ease) .1s both}
[data-testid="stMetric"]{animation:panelIn .42s var(--ease) both}
[data-testid="stProgress"] [role="progressbar"] > div{transform-origin:left;animation:barGrow .8s var(--ease) both}
.stButton>button{transition:background .18s,border-color .18s,color .18s,transform .12s,box-shadow .2s}
.stButton>button:hover{transform:translateY(-1px);box-shadow:0 6px 16px -10px rgba(20,22,18,.6)}
.stButton>button:active{transform:translateY(1px) scale(.985)}
[data-testid="stSidebar"] [role="radiogroup"] label{transition:background .18s,transform .12s}
[data-testid="stSidebar"] [role="radiogroup"] label:active{transform:translateY(1px)}
.verdict{display:inline-flex;align-items:center;gap:.55rem;margin:.2rem 0 .7rem;font-size:13.5px;letter-spacing:.04em}
.verdict i{font-family:"Songti SC","SimSun",serif;font-style:normal;font-size:15px;width:30px;height:30px;
  display:grid;place-items:center;border:1.5px solid currentColor;border-radius:2px;
  transform:rotate(-8deg);animation:stampIn .36s var(--ease) .08s both}
.verdict.ok{color:var(--vein)}
.verdict.bad{color:var(--art)}
.heat{display:flex;gap:4px;flex-wrap:wrap;margin:.4rem 0 .2rem}
.heat i{width:15px;height:15px;border-radius:2px;background:#EDEBE2;display:block;animation:cellIn .34s var(--ease) both}
.heat i.l1{background:#DCE4EC}
.heat i.l2{background:#AFC4D6}
.heat i.l3{background:#6E93B4}
.heat i.l4{background:var(--vein)}
.heat-legend{display:flex;align-items:center;gap:7px;font-size:11.5px;color:var(--mute);margin-top:.45rem}
.heat-legend b{width:11px;height:11px;border-radius:2px;background:var(--vein);display:block}
.ring-wrap{display:flex;align-items:center;gap:1.2rem;margin:.2rem 0 .9rem}
.ring-num{font-family:"Songti SC","SimSun",serif;font-size:34px;line-height:1}
.ring-cap{font-size:11px;letter-spacing:.18em;color:var(--mute);margin-top:.4rem}
.ring-arc{animation:ringDraw 1.1s var(--ease) both}
@media (prefers-reduced-motion: reduce){*{animation:none !important;transition:none !important}}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

ROUTE_TEXT = {
    "local_card": "来源：本地已审核知识卡，未消耗在线额度。",
    "local_fallback": "来源：本地知识卡兜底，未消耗在线额度。",
    "coze": "来源：在线模型（Coze），本次消耗 1 次调用额度。",
    "quota_exhausted": "来源：在线额度已用完，本次没有作答。",
    "coze_failed": "来源：在线模型暂时不可用，本次没有作答。",
    "no_engine": "来源：未配置在线模型，只查了本地知识卡。",
}
QUESTIONS = [
    "腋神经损伤会有什么表现？",
    "肱骨外科颈骨折最容易损伤哪条神经？",
    "肝门静脉的属支有哪些？",
]


def _sid():
    if "sid" not in st.session_state:
        st.session_state.sid = "st" + secrets.token_hex(5)
    return st.session_state.sid


def _ask(prompt):
    sid = _sid()
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.spinner("正在查课程资料并组织答案…"):
        result = core.answer_question(prompt, sid)
    if result.get("refused"):
        content = "**没有作答。** " + str(result.get("reason") or "")
    else:
        content = str(result.get("answer") or "")
    st.session_state.messages.append({
        "role": "assistant",
        "content": content,
        "meta": ROUTE_TEXT.get(result.get("route"), ""),
        "cites": result.get("citations") or [],
        "note": result.get("note") or "",
    })


def _render_messages():
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            for cite in msg.get("cites") or []:
                loc = (" · " + str(cite.get("locator"))) if cite.get("locator") else ""
                st.markdown(
                    '<div class="cite-box"><b>出处</b>　'
                    + html.escape(str(cite.get("doc") or "")) + html.escape(loc)
                    + "</div>", unsafe_allow_html=True)
            if msg.get("note"):
                st.caption(msg["note"])
            if msg.get("meta"):
                st.caption(msg["meta"])


def page_ask():
    st.markdown('<div class="panel-kicker">01 / 问答</div>', unsafe_allow_html=True)
    st.markdown("## 课程问答")
    st.caption("只回答系统解剖学相关问题，优先依据课程资料；资料里没有的会明确说不知道。")
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if st.session_state.pop("pending_q", None):
        _ask(st.session_state.pop("_pending_text"))
    cols = st.columns(len(QUESTIONS))
    for i, (text, col) in enumerate(zip(QUESTIONS, cols)):
        if col.button(text, key="chip" + str(i), use_container_width=True):
            st.session_state.pending_q = True
            st.session_state._pending_text = text
            st.rerun()
    if not st.session_state.messages:
        st.info("先点上面一个问题，或在下面输入框里提问。")
    _render_messages()
    prompt = st.chat_input("问一个系统解剖学问题…")
    if prompt:
        _ask(prompt)
        st.rerun()


def page_cards():
    sid = _sid()
    st.markdown('<div class="panel-kicker">02 / 速记</div>', unsafe_allow_html=True)
    st.markdown("## 知识点速记")
    st.caption("先自己回忆，再翻面核对；系统按间隔重复安排下一次复习。")
    c1, c2 = st.columns([2, 1])
    chapter = c1.selectbox("章节", ["全部"] + list(core.CHAPTERS), key="card_chapter")
    due_only = c2.checkbox("只看今天到期", value=False, key="card_due")
    deck = [c for c in core.CARDS if chapter == "全部" or c["chapter"] == chapter]
    if due_only:
        deck = [c for c in deck if core.STORE.sched_state(sid, c["id"])["due_ts"] <= core._now()]
    if not deck:
        st.success("今天到期的卡片已经复习完了。可以取消“只看今天到期”继续看。")
        return
    deck_key = (chapter, due_only, len(deck))
    if st.session_state.get("deck_key") != deck_key:
        st.session_state.deck_key = deck_key
        st.session_state.card_i = 0
        st.session_state.revealed = False
    idx = st.session_state.get("card_i", 0) % len(deck)
    card = deck[idx]
    state = core.STORE.sched_state(sid, card["id"])
    st.caption("第 " + str(idx + 1) + " / " + str(len(deck)) + " 张　当前状态：" + state["status"])
    with st.container(border=True, key="cardbox"):
        st.caption(card["chapter"] + " · " + card["topic"])
        st.markdown('<div class="card-front">' + html.escape(card["front"]) + "</div>",
                    unsafe_allow_html=True)
        if not st.session_state.get("revealed"):
            if st.button("翻面看答案", type="primary", key="flip"):
                st.session_state.revealed = True
                st.rerun()
        else:
            st.markdown(card["answer"])
            src = card.get("source") or {}
            st.markdown('<div class="cite-box"><b>出处</b>　' + html.escape(str(src.get("doc") or ""))
                        + (" · " + html.escape(str(src.get("locator"))) if src.get("locator") else "")
                        + "</div>", unsafe_allow_html=True)
            a, b = st.columns(2)
            if a.button("记住了", type="primary", key="known", use_container_width=True):
                core.STORE.review_card(sid, card, True)
                st.session_state.card_i = idx + 1
                st.session_state.revealed = False
                st.rerun()
            if b.button("没记住", key="unknown", use_container_width=True):
                core.STORE.review_card(sid, card, False)
                st.session_state.card_i = idx + 1
                st.session_state.revealed = False
                st.rerun()


def page_quiz():
    sid = _sid()
    st.markdown('<div class="panel-kicker">03 / 自测</div>', unsafe_allow_html=True)
    st.markdown("## 自测练习")
    st.caption("即时判分，答错自动进入错题本和复习清单。")
    c1, c2, c3 = st.columns([2, 1, 1])
    chapter = c1.selectbox("章节", ["全部"] + list(core.CHAPTERS), key="quiz_chapter")
    n = c2.number_input("题量", 1, 20, 4, key="quiz_n")
    if c3.button("换一组", use_container_width=True):
        pool = [q for q in core.QUIZ if chapter == "全部" or q["chapter"] == chapter]
        st.session_state.quiz_items = pool[:int(n)]
        st.session_state.quiz_i = 0
        st.session_state.quiz_result = None
        st.rerun()
    if "quiz_items" not in st.session_state:
        st.session_state.quiz_items = list(core.QUIZ)[:4]
        st.session_state.quiz_i = 0
        st.session_state.quiz_result = None
    items = st.session_state.quiz_items
    if not items:
        st.warning("这个章节暂时没有题目。")
        return
    i = st.session_state.quiz_i % len(items)
    q = items[i]
    st.caption("第 " + str(i + 1) + " / " + str(len(items)) + " 题 · " + q["chapter"])
    with st.container(border=True, key="quizbox"):
        st.markdown("### " + q["stem"])
        labels = ["ABCDEF"[k] + ". " + opt for k, opt in enumerate(q["options"])]
        choice = st.radio("选择一个答案", list(range(len(q["options"]))),
                          format_func=lambda k: labels[k], key="choice_" + q["id"] + "_" + str(i))
        if st.button("提交答案", type="primary", key="submit_" + q["id"] + "_" + str(i)):
            ok = core.STORE.answer_quiz(sid, q, int(choice))
            st.session_state.quiz_result = {"qid": q["id"], "ok": bool(ok), "choice": int(choice)}
            st.rerun()
        result = st.session_state.get("quiz_result")
        if result and result.get("qid") == q["id"]:
            if result["ok"]:
                st.markdown('<div class="verdict ok"><i>对</i><span>答对了</span></div>',
                            unsafe_allow_html=True)
            else:
                st.markdown('<div class="verdict bad"><i>误</i><span>答错了，正确答案是 '
                            + "ABCDEF"[q["answer_index"]] + "。</span></div>",
                            unsafe_allow_html=True)
            st.markdown(q["explain"])
            src = q.get("source") or {}
            st.markdown('<div class="cite-box"><b>出处</b>　' + html.escape(str(src.get("doc") or ""))
                        + (" · " + html.escape(str(src.get("locator"))) if src.get("locator") else "")
                        + "</div>", unsafe_allow_html=True)
            if st.button("下一题", key="next_" + q["id"] + "_" + str(i)):
                st.session_state.quiz_i = i + 1
                st.session_state.quiz_result = None
                st.rerun()


def page_profile():
    sid = _sid()
    st.markdown('<div class="panel-kicker">04 / 档案</div>', unsafe_allow_html=True)
    st.markdown("## 学习档案")
    st.caption("所有记录只存在这台服务器上，用匿名 sid 区分，不采集姓名和学号。")
    prof = core.STORE.profile(sid)
    o = prof["overview"]
    a, b, c, d = st.columns(4)
    a.metric("已掌握", str(o["mastered"]) + " / " + str(o["cards_total"]))
    b.metric("自测正确率", str(o["accuracy"]) + "%")
    c.metric("待复习", str(o["due"]))
    d.metric("连续学习", str(o["streak"]) + " 天")
    pct = int(round(100 * o["mastered"] / max(1, o["cards_total"])))
    off = round(289 * (1 - pct / 100.0), 1)
    st.markdown('<div class="ring-wrap"><svg width="104" height="104" viewBox="0 0 110 110">'
                '<circle cx="55" cy="55" r="46" fill="none" stroke="#EDEBE2" stroke-width="7"/>'
                '<circle class="ring-arc" cx="55" cy="55" r="46" fill="none" stroke="#2F5B82"'
                ' stroke-width="7" stroke-linecap="round" stroke-dasharray="289"'
                ' stroke-dashoffset="' + str(off) + '" transform="rotate(-90 55 55)"/></svg>'
                '<div><div class="ring-num">' + str(pct) + '%</div>'
                '<div class="ring-cap">今日掌握度</div></div></div>', unsafe_allow_html=True)
    st.markdown("### 章节掌握度")
    for ch in prof["chapters"]:
        st.progress(ch["rate"] / 100.0, text=ch["chapter"] + "　" + str(ch["mastered"]) + "/" + str(ch["total"]))
    st.markdown("### 今天的复习清单")
    if prof["plan"]:
        for item in prof["plan"]:
            st.markdown("- **" + item["chapter"] + " · " + item["gap"] + "**　" + item["action"])
    else:
        st.success("暂时没有待补的知识缺口。")
    st.markdown("### 最近 35 天学习活跃度")
    acts = prof["activity"]
    if acts:
        cells = []
        for k, x in enumerate(acts):
            n = int(x["n"])
            lvl = 0 if n <= 0 else 1 if n <= 2 else 2 if n <= 5 else 3 if n <= 9 else 4
            cells.append('<i class="l' + str(lvl) + '" style="animation-delay:'
                         + str(round(k * 0.012, 3)) + 's" title="' + x["date"] + " · "
                         + str(n) + ' 次"></i>')
        st.markdown('<div class="heat">' + "".join(cells) + "</div>", unsafe_allow_html=True)
        st.markdown('<div class="heat-legend"><b></b><span>' + acts[0]["date"][5:]
                    + " 至 " + acts[-1]["date"][5:]
                    + "　颜色越深，当天练习越多</span></div>", unsafe_allow_html=True)
    with st.expander("资料来源与合规说明"):
        st.write("当前内容为占位示例，正式提交前必须替换为团队审核后的系统解剖学资料。"
                 "系统不采集姓名与学号，也不访问学校任何系统。")
        for card in core.CARDS:
            src = card.get("source") or {}
            st.caption(str(src.get("doc") or "") + " · " + str(src.get("locator") or ""))


sid = _sid()
with st.sidebar:
    st.markdown('<div class="side-brand">MEDTA</div>', unsafe_allow_html=True)
    st.markdown('<div class="side-sub">系统解剖学 · 学习台</div>', unsafe_allow_html=True)
    panel = st.radio("模块", ["课程问答", "知识点速记", "自测练习", "学习档案"],
                     label_visibility="collapsed")
    st.markdown("---")
    quota = core._quota(sid)
    if core.coze_available():
        st.markdown('<div class="side-stat"><b>' + str(quota["user_used"]) + "/" + str(quota["user_limit"])
                    + '</b> 今日提问<br><span>全站 ' + str(quota["coze_calls"]) + "/"
                    + str(quota["coze_max"]) + " 次</span></div>", unsafe_allow_html=True)
    else:
        st.markdown('<div class="side-stat"><b>本地模式</b><br><span>未配置 COZE_PAT</span></div>',
                    unsafe_allow_html=True)
    st.markdown("---")
    if st.button("清空我的学习记录", use_container_width=True):
        core.STORE.reset(sid)
        st.session_state.messages = []
        st.rerun()

st.markdown('<div class="hero-kicker">郑州大学 · 系统解剖学</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-title">医学课程 AI 助教</div>', unsafe_allow_html=True)
st.markdown('<p class="hero-lede">问、记、测、看四件事连成一条学习闭环：先问清楚，'
            '再翻卡记住，用自测检验，最后在学习档案里看到下一步该补什么。</p>',
            unsafe_allow_html=True)
st.markdown('<div class="rule"></div>', unsafe_allow_html=True)

if panel == "课程问答":
    page_ask()
elif panel == "知识点速记":
    page_cards()
elif panel == "自测练习":
    page_quiz()
else:
    page_profile()
