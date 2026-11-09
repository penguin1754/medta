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
import hashlib
import os
import random
import secrets
import sys
from datetime import date, timedelta
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

st.set_page_config(
    page_title="医学课程 AI 助教 · 系统解剖学",
    page_icon="🫀",
    layout="wide",
    initial_sidebar_state="auto",
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


def _pat_fp():
    """令牌指纹：只用于对照本地与云端是不是同一个令牌，不暴露令牌本身。"""
    pat = (os.environ.get("COZE_PAT") or "").strip()
    if not pat:
        return "<未配置>"
    return hashlib.sha256(pat.encode("utf-8")).hexdigest()[:8] + " / 长度 " + str(len(pat))

import backend.app as core  # noqa: E402  （必须先注入 Secrets 再导入）

# Streamlit Cloud 部署时可能只替换脚本、不重载已导入的 backend 模块，
# 这里对新增接口做兜底，避免新旧代码混跑时整页崩掉。
QUIZ_CHAPTERS = getattr(core, "QUIZ_CHAPTERS", None) or sorted({q["chapter"] for q in core.QUIZ})


def coze_problem():
    fn = getattr(core, "coze_config_problem", None)
    if fn:
        return fn()
    return "" if core.coze_available() else "未配置 COZE_PAT，当前只查本地知识卡。"


LEGACY_CSS = """
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
/* 翻牌：两张面同占一格，整块绕 Y 轴翻过去，高度自动取较高的一面 */
.flipwrap{display:grid;perspective:1600px;position:relative;margin:.1rem 0 .5rem;
  transform-style:preserve-3d}
.flipwrap::before,.flipwrap::after{content:"";position:absolute;inset:0;z-index:-1;
  background:var(--tint);border:1px solid #EDEBE2;border-radius:4px}
.flipwrap::before{transform:translateY(8px) scaleX(.986)}
.flipwrap::after{transform:translateY(15px) scaleX(.972);opacity:.72}
.flipwrap:not(.flipped){animation:cardIn .42s var(--ease) both}
.flipwrap.flipped{transform:perspective(1600px) rotateY(180deg);
  animation:flipToBack .56s var(--ease) both}
@keyframes flipToBack{
  from{transform:perspective(1600px) rotateY(0)}
  to{transform:perspective(1600px) rotateY(180deg)}}
@keyframes cardIn{from{opacity:0;transform:translateY(14px) scale(.982)}
  to{opacity:1;transform:none}}
.face{grid-area:1 / 1;display:flex;flex-direction:column;justify-content:center;gap:14px;
  min-height:250px;background:var(--card);border:1px solid var(--line);border-radius:4px;
  padding:30px 34px;text-align:left;color:var(--ink);
  box-shadow:0 3px 10px -4px rgba(25,26,23,.16);
  backface-visibility:hidden;-webkit-backface-visibility:hidden}
.face.back{transform:rotateY(-180deg);justify-content:flex-start}
.face-tag{align-self:flex-start;font-size:12px;letter-spacing:.08em;color:var(--art);
  background:#F7E8E4;border-radius:2px;padding:4px 10px;line-height:1.3}
.face.back .face-tag{color:var(--vein);background:#E7EEF5}
.face.front .face-text{font-family:"Songti SC","SimSun",serif;font-size:27px;line-height:1.72}
.face.back .face-text{font-size:15.5px;line-height:1.95;color:var(--ink2)}
.face.back .face-text p{margin:0 0 .7rem}
.face-src{border-left:2px solid var(--vein);background:#E7EEF5;padding:.5rem .8rem;
  font-size:12.5px;color:var(--ink2);margin-top:.2rem}
.face-hint{font-size:11.5px;color:var(--mute);letter-spacing:.04em}
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
.keyhit,.keymiss{display:inline-block;font-size:12.5px;padding:2px 9px;border-radius:2px;margin:2px 5px 2px 0}
.keyhit{background:#E7EEF5;color:var(--vein);border:1px solid #C9DBEA}
.keymiss{background:#F7E8E4;color:var(--art);border:1px solid #EBCFC8}
.plan-row{display:flex;gap:.7rem;align-items:baseline;padding:.45rem 0;border-bottom:1px dashed var(--line)}
.plan-row:last-child{border-bottom:0}
.plan-idx{font-family:"Songti SC","SimSun",serif;color:var(--art);min-width:1.6rem}
.plan-why{font-size:12px;color:var(--mute);margin-left:auto;white-space:nowrap}
.pace-note{font-size:12.5px;color:var(--mute);margin-top:-.4rem}
@media (prefers-reduced-motion: reduce){*{animation:none !important;transition:none !important}}
</style>
"""


def _theme_css():
    """读取冷白诊室主题；CSS 放在 frontend/ 便于单独维护。"""
    parts = []
    for name in ("clinic.css", "clinic-mobile.css"):
        path = ROOT / "frontend" / name
        if path.exists():
            parts.append(path.read_text(encoding="utf-8"))
    return "<style>\n" + "\n".join(parts) + "\n</style>"


st.markdown(_theme_css(), unsafe_allow_html=True)

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
    st.session_state["_scroll_to_chat"] = True
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
        "dbg": result.get("error") or "",
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
            if msg.get("dbg"):
                with st.expander("技术详情（排查用）"):
                    st.code(str(msg["dbg"]), language="text")
                    st.caption("COZE_BASE=" + str(os.environ.get("COZE_BASE") or "https://api.coze.cn")
                               + " · COZE_BOT_ID=" + str(os.environ.get("COZE_BOT_ID") or "")
                               + " · 令牌指纹 " + _pat_fp())


PANEL_META = {
    "课程问答": ("课程问答", "把问题直接打在下面的输入框里。助教按课程资料回答并标出处；资料里没有的会明确说不知道。"),
    "知识点速记": ("知识点速记", "先自己回忆，再翻面核对；系统按间隔重复安排下一次复习。"),
    "自测练习": ("自测练习", "选择题即时判分；简答题按要点命中率打分，同一份作答结果永远一致。"),
    "考前冲刺": ("考前冲刺", "填考试日期，按还没掌握的张数除以剩余天数，倒排每天的复习量。"),
    "学习档案": ("学习档案", "所有记录只存在这台服务器上，用匿名 sid 区分，不采集姓名和学号。"),
}


def _reset_scroll_on_nav(panel):
    """首次进入或切换模块时回到页首；同页交互不打断阅读。"""
    if st.session_state.get("_scroll_panel") == panel:
        return
    st.session_state["_scroll_panel"] = panel
    components.html(
        """<script>
const doc = window.parent.document;
const win = window.parent;
let ticks = 0;
const settle = () => {
  const box = doc.querySelector('[data-testid="stAppScrollToBottomContainer"], [data-testid="stMain"]');
  if (box) box.scrollTop = 0;
  if (win.innerWidth <= 900) {
    const sb = doc.querySelector('[data-testid="stSidebar"]');
    if (sb && sb.getAttribute("data-collapsed") !== "true") {
      const btn = sb.querySelector('[data-testid="stSidebarCollapseButton"] button');
      if (btn) btn.click();
    }
  }
  if (++ticks < 10) win.setTimeout(settle, 100);
};
settle();
</script>""",
        height=0,
    )


def _hero_metric(label, value, unit, note, dark=False):
    return (
        '<div class="hero-metric' + (' dark' if dark else '') + '">'
        '<div class="hero-metric-label">' + html.escape(label) + '</div>'
        '<div class="hero-metric-line"><div class="hero-metric-value">' + html.escape(value)
        + ('<small>' + html.escape(unit) + '</small>' if unit else '') + '</div></div>'
        '<div class="hero-metric-note">' + html.escape(note) + '</div></div>'
    )


def _hero_panel(panel, sid):
    """每个模块只放和自己有关的数据，避免五页都是同一组卡片。"""
    if panel == "课程问答":
        return (
            '<div class="hero-ask">'
            '<div class="hero-ask-label">助教能回答</div>'
            '<div class="hero-ask-item"><b>概念</b><span>定义、分型、毗邻关系</span></div>'
            '<div class="hero-ask-item"><b>结构</b><span>走行、分支、支配范围</span></div>'
            '<div class="hero-ask-item"><b>损伤</b><span>典型表现与常考部位</span></div>'
            '<div class="hero-ask-note">回答优先引用课程资料，并标出处</div>'
            '</div>'
        )
    prof = core.STORE.profile(sid)
    ov = prof["overview"]
    plan = core.STORE.sprint(sid)
    total = max(1, int(ov["cards_total"]))
    if panel == "知识点速记":
        return (_hero_metric("今日到期", str(int(ov["due"])), "张", "到期就复习，不用等")
                + _hero_metric("已掌握", str(int(ov["mastered"])), "/ " + str(total) + " 张",
                               "按间隔重复往后排", dark=True))
    if panel == "自测练习":
        return (_hero_metric("已答题", str(int(ov["answered"])), "道", "选择和简答都计入")
                + _hero_metric("正确率", str(int(ov["accuracy"])), "%",
                               "答错自动进复习清单", dark=True))
    if panel == "考前冲刺":
        remaining = int(plan["remaining"])
        status = "已过完" if remaining == 0 else ("跟得上" if plan["feasible"] else "偏紧")
        note = "按剩余天数倒排" if plan["feasible"] else "超过每天 60 张，建议只保重点章"
        pace = "0.0" if remaining == 0 else ("%.1f" % float(plan["pace"]))
        return (_hero_metric("当前节奏", status, "", note)
                + _hero_metric("日均需掌握", pace, "张", "断一天不用补，次日重算", dark=True))
    week = prof["activity"][-7:]
    active_days = sum(1 for a in week if int(a["n"]) > 0)
    return (_hero_metric("最近 7 天", str(active_days), "天", "有学习记录的天数")
            + _hero_metric("累计动作", str(int(ov["events"])), "次",
                           "翻卡、答题、提问都算", dark=True))


def _page_header(panel, sid):
    """页面顶栏；右侧只展示本模块自己的数据。"""
    title, lede = PANEL_META[panel]
    st.markdown(
        '<div class="app-topbar">'
        '<div class="app-context">系统解剖学 / ' + html.escape(title) + '</div>'
        '<div class="app-status"><i></i>记录已保存</div>'
        '</div>'
        '<section class="page-hero">'
        '<div class="page-hero-copy"><h1>' + html.escape(title) + '</h1>'
        '<p>' + html.escape(lede) + '</p></div>'
        '<div class="hero-metrics">' + _hero_panel(panel, sid) + '</div>'
        '</section>',
        unsafe_allow_html=True,
    )

def page_ask():
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if st.session_state.pop("pending_q", None):
        _ask(st.session_state.pop("_pending_text"))
    with st.container(key="ask_composer"):
        st.markdown(
            '<div class="composer-label">直接输入问题</div>'
            '<div class="composer-hint">概念、结构、损伤表现都可以问，回答带出处</div>',
            unsafe_allow_html=True,
        )
        prompt = st.chat_input("例如：腋神经损伤会有什么表现？")
        if prompt:
            _ask(prompt)
            st.rerun()
    if not st.session_state.messages:
        st.markdown('<div class="section-label">试试这些问题</div>', unsafe_allow_html=True)
        with st.container(key="ask_chips"):
            cols = st.columns(len(QUESTIONS))
            for i, (text, col) in enumerate(zip(QUESTIONS, cols)):
                if col.button(text, key="chip" + str(i), use_container_width=True):
                    st.session_state.pending_q = True
                    st.session_state._pending_text = text
                    st.rerun()
    if not st.session_state.messages:
        st.markdown(
            '<div class="ask-empty"><b>还没有提问</b>'
            '<span>在上面的输入框打字，或点一个示例问题。</span></div>',
            unsafe_allow_html=True,
        )
    _render_messages()
    _maybe_scroll_to_chat()

def _flip_card_html(card, revealed):
    """整张卡一次渲染出正反两面，靠 CSS 三维翻转过去；高度由较高的一面决定。"""
    src = card.get("source") or {}
    src_line = html.escape(str(src.get("doc") or ""))
    if src.get("locator"):
        src_line += " · " + html.escape(str(src.get("locator")))
    body = [
        "<p>" + html.escape(part.strip()) + "</p>"
        for part in str(card["answer"]).split("\n")
        if part.strip()
    ]
    cls = "flipwrap flipped" if revealed else "flipwrap"
    return (
        '<div class="' + cls + '">'
        '<div class="face front">'
        '<span class="face-tag">' + html.escape(card["chapter"]) + " · "
        + html.escape(card["topic"]) + "</span>"
        '<div class="face-text">' + html.escape(card["front"]) + "</div>"
        '<span class="face-hint">先自己回忆一遍，再翻面核对</span>'
        "</div>"
        '<div class="face back">'
        '<span class="face-tag">答案</span>'
        '<div class="face-text">' + "".join(body) + "</div>"
        '<div class="face-src">出处　' + src_line + "</div>"
        "</div>"
        "</div>"
    )


def page_cards():
    sid = _sid()
    with st.container(key="card_filters"):
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
        revealed = bool(st.session_state.get("revealed"))
        st.markdown(_flip_card_html(card, revealed), unsafe_allow_html=True)
        if not revealed:
            if st.button("翻面看答案", type="primary", key="flip", use_container_width=True):
                st.session_state.revealed = True
                st.rerun()
        else:
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
            if st.button("翻回正面", key="unflip"):
                st.session_state.revealed = False
                st.rerun()


def page_quiz():
    tab_choice, tab_short = st.tabs(["选择题", "简答题"])
    with tab_choice:
        _quiz_choice()
    with tab_short:
        _quiz_short()


def _quiz_choice():
    sid = _sid()
    with st.container(key="quiz_filters"):
        c1, c2, c3 = st.columns([2, 1, 1])
        chapter = c1.selectbox("章节", ["全部"] + list(QUIZ_CHAPTERS), key="quiz_chapter")
        n = c2.number_input("题量", 1, 20, 4, key="quiz_n")
        if c3.button("换一组", use_container_width=True):
            pool = [q for q in core.QUIZ if chapter == "全部" or q["chapter"] == chapter]
            k = min(int(n), len(pool))
            st.session_state.quiz_items = random.sample(pool, k) if pool else []
            st.session_state.quiz_i = 0
            st.session_state.quiz_result = None
            st.rerun()
    if "quiz_items" not in st.session_state:
        st.session_state.quiz_items = random.sample(list(core.QUIZ), min(4, len(core.QUIZ)))
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


def _quiz_short():
    sid = _sid()
    if not core.SA:
        st.info("简答题库为空。先运行 `python tools/build_short_answer.py`。")
        return
    with st.container(key="sa_filters"):
        c1, c2 = st.columns([2, 1])
        chapter = c1.selectbox("章节", ["全部"] + list(core.SA_CHAPTERS), key="sa_chapter")
        deck = [s for s in core.SA if chapter == "全部" or s["chapter"] == chapter]
    if not deck:
        st.warning("这个章节还没有简答题。")
        return
    deck_key = (chapter, len(deck))
    if st.session_state.get("sa_deck_key") != deck_key:
        st.session_state.sa_deck_key = deck_key
        st.session_state.sa_i = 0
        st.session_state.sa_result = None
    i = st.session_state.get("sa_i", 0) % len(deck)
    item = deck[i]
    st.caption("第 " + str(i + 1) + " / " + str(len(deck)) + " 题 · " + item["chapter"]
               + "　共 " + str(len(item["keys"])) + " 个要点，命中 80% 以上算通过")
    with st.container(border=True, key="sabox"):
        st.markdown("### " + item["question"])
        answer = st.text_area("我的答案", key="sa_in_" + item["id"] + "_" + str(i), height=170,
                              placeholder="按要点写，用词接近教材即可，不用写成作文……")
        if st.button("提交，看命中几个要点", type="primary", use_container_width=True,
                     key="sa_ok_" + item["id"] + "_" + str(i)):
            if not answer.strip():
                st.warning("先写点内容再提交。")
            else:
                res = core.STORE.answer_short(sid, item, answer)
                st.session_state.sa_result = dict(res, id=item["id"], i=i)
                st.rerun()
        res = st.session_state.get("sa_result")
        if res and res.get("id") == item["id"] and res.get("i") == i:
            ok = bool(res["passed"])
            total_keys = len(res["hits"]) + len(res["missed"])
            st.markdown(
                '<div class="verdict ' + ("ok" if ok else "bad") + '"><i>'
                + ("过" if ok else "补") + '</i><span>要点命中 ' + str(res["score"])
                + "%（" + str(len(res["hits"])) + " / " + str(total_keys) + "）</span></div>",
                unsafe_allow_html=True)
            chips = "".join('<span class="keyhit">' + html.escape(k) + "</span>" for k in res["hits"])
            chips += "".join('<span class="keymiss">' + html.escape(k) + "</span>" for k in res["missed"])
            st.markdown(chips, unsafe_allow_html=True)
            st.markdown("**参考答案**")
            st.markdown(item["answer"])
            src = item.get("source") or {}
            st.markdown('<div class="cite-box"><b>出处</b>　' + html.escape(str(src.get("doc") or ""))
                        + (" · " + html.escape(str(src.get("locator"))) if src.get("locator") else "")
                        + "</div>", unsafe_allow_html=True)
            if not ok:
                st.caption("没过的题已经进学习档案的复习清单。")
            if st.button("下一题", key="sa_next_" + item["id"] + "_" + str(i)):
                st.session_state.sa_i = i + 1
                st.session_state.sa_result = None
                st.rerun()


def page_sprint():
    sid = _sid()
    cur = core.STORE.exam_date(sid)
    try:
        default = date.fromisoformat(cur) if cur else date.today() + timedelta(days=30)
    except ValueError:
        default = date.today() + timedelta(days=30)
    if default < date.today():  # 考试日已过，别让 date_input 因为越界报错
        default = date.today() + timedelta(days=30)
    picked = st.date_input("考试日期", value=default, min_value=date.today(),
                           max_value=date.today() + timedelta(days=365), key="exam_pick")
    if picked.isoformat() != cur:
        core.STORE.set_exam(sid, picked.isoformat())
    plan = core.STORE.sprint(sid)
    with st.container(key="sprint_metrics"):
        a, b, c, d = st.columns(4)
        a.metric("距考试", str(plan["days_left"]) + " 天")
        b.metric("待掌握", str(plan["remaining"]) + " / " + str(plan["cards_total"]))
        c.metric("今天卡片", str(plan["daily_cards"]) + " 张")
        d.metric("今天题目", str(plan["daily_quiz"]) + " 道")
    if plan["remaining"] == 0:
        st.success("卡片已经全部掌握，接下来按间隔重复维持就行。")
    elif plan["feasible"]:
        st.markdown('<div class="pace-note">每天 ' + str(plan["daily_cards"])
                    + " 张，正好在考前过完一遍。断一天也不用补，第二天会按剩余天数重算。</div>",
                    unsafe_allow_html=True)
    else:
        st.warning("按现在的速度跟不上：还剩 " + str(plan["remaining"]) + " 张、" + str(plan["days_left"])
                   + " 天，平均每天要 " + str(round(plan["pace"], 1)) + " 张。建议只保重点章节。")
    st.markdown("### 各章配额")
    for ch in plan["chapters"]:
        if ch["remaining"] == 0:
            continue
        st.progress(ch["mastered"] / float(max(1, ch["total"])),
                    text=ch["chapter"] + "　已掌握 " + str(ch["mastered"]) + "/" + str(ch["total"])
                    + "　今日配额 " + str(plan["quotas"].get(ch["chapter"], 0)) + " 张")
    st.markdown("### 今天的卡片")
    if plan["today"]:
        rows = []
        for k, item in enumerate(plan["today"], 1):
            rows.append('<div class="plan-row"><span class="plan-idx">' + str(k).zfill(2)
                        + "</span><span>" + html.escape(item["front"]) + '</span>'
                        '<span class="plan-why">' + html.escape(item["chapter"] + " · " + item["reason"])
                        + "</span></div>")
        st.markdown("".join(rows), unsafe_allow_html=True)
        if st.button("去速记，从今天这张开始", type="primary"):
            st.session_state.nav_pending = "知识点速记"
            st.rerun()
    else:
        st.info("今天没有待复习的卡片。")
    st.markdown("### 接下来几天")
    with st.container(key="sprint_preview"):
        cols = st.columns(len(plan["preview"]))
        for col, day in zip(cols, plan["preview"]):
            col.metric(day["date"][5:], str(day["cards"]) + " 张",
                       delta=("剩 " + str(day["left_after"])) if day["left_after"] else "收尾")


def page_profile():
    sid = _sid()
    prof = core.STORE.profile(sid)
    o = prof["overview"]
    with st.container(key="profile_metrics"):
        a, b, c, d, e = st.columns(5)
        a.metric("已掌握", str(o["mastered"]) + " / " + str(o["cards_total"]))
        b.metric("自测正确率", str(o["accuracy"]) + "%")
        c.metric("简答通过", str(o["sa_passed"]) + " / " + str(o["sa_total"]))
        d.metric("待复习", str(o["due"]))
        e.metric("连续学习", str(o["streak"]) + " 天")
    pct = int(round(100 * o["mastered"] / max(1, o["cards_total"])))
    off = round(289 * (1 - pct / 100.0), 1)
    st.markdown('<div class="ring-wrap"><svg width="104" height="104" viewBox="0 0 110 110">'
                '<circle cx="55" cy="55" r="46" fill="none" stroke="#DCE7E9" stroke-width="7"/>'
                '<circle class="ring-arc" cx="55" cy="55" r="46" fill="none" stroke="#286A78"'
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
        st.write("题库与知识点来自团队资料《系统解剖学 题库完整版1033题》《重点考点及答案》，"
                 "用 OCR 抽取后入库：已在线的有 " + str(len(core.QUIZ)) + " 道选择题/判断题、"
                 + str(len(core.CARDS)) + " 张知识卡、"
                 + str(len(core.SA)) + " 道简答题。个别字词可能识别有误，以教材原文为准。"
                 "系统不采集姓名与学号，也不访问学校任何系统。")
        for card in core.CARDS:
            src = card.get("source") or {}
            st.caption(str(src.get("doc") or "") + " · " + str(src.get("locator") or ""))


sid = _sid()
if st.session_state.get("nav_pending"):
    st.session_state.nav = st.session_state.pop("nav_pending")
with st.sidebar:
    st.markdown(
        '<div class="side-lockup">'
        '<div class="side-mark" aria-hidden="true">'
        '<svg viewBox="0 0 24 24"><g fill="none" stroke="#DCEBED" stroke-width="1.35">'
        '<path d="M12 3.2c4.6 0 8.2 3.8 8.2 8.4S16.6 20 12 20s-8.2-3.8-8.2-8.4S7.4 3.2 12 3.2Z"/>'
        '<path d="M12 6.5c2.8 0 4.9 2.3 4.9 5.1s-2.1 5.2-4.9 5.2-4.9-2.3-4.9-5.2 2.1-5.1 4.9-5.1Z"/>'
        '<path d="M12 9.7c1.1 0 1.9.9 1.9 2s-.8 2-1.9 2-1.9-.9-1.9-2 .8-2 1.9-2Z"/>'
        '</g></svg></div>'
        '<div><div class="side-brand">MEDTA</div><div class="side-sub">系统解剖学</div></div>'
        '</div>',
        unsafe_allow_html=True,
    )
    panel = st.radio("模块", ["课程问答", "知识点速记", "自测练习", "考前冲刺", "学习档案"],
                     label_visibility="collapsed", key="nav")
    st.markdown('<div class="side-divider"></div>', unsafe_allow_html=True)
    quota = core._quota(sid)
    if core.coze_available():
        st.markdown(
            '<div class="side-panel"><div class="side-panel-label">今日提问</div>'
            '<div class="side-panel-value">' + str(quota["user_used"]) + '<small>/ '
            + str(quota["user_limit"]) + '</small></div>'
            '<div class="side-panel-note">全站已用 ' + str(quota["coze_calls"]) + ' / '
            + str(quota["coze_max"]) + ' 次</div></div>',
            unsafe_allow_html=True,
        )
    else:
        problem = coze_problem() or "在线模型没有启用，当前只查本地知识卡。"
        st.markdown(
            '<div class="side-panel"><div class="side-panel-label">在线问答</div>'
            '<div class="side-panel-value">本地模式</div>'
            '<div class="side-panel-note">' + html.escape(problem) + '</div></div>',
            unsafe_allow_html=True,
        )
    st.markdown('<div class="side-divider"></div>', unsafe_allow_html=True)
    if st.button("清空我的学习记录", use_container_width=True):
        core.STORE.reset(sid)
        st.session_state.messages = []
        st.rerun()
    st.markdown('<div class="side-privacy">学习记录只保存在这台服务器，用匿名 sid 区分。</div>',
                unsafe_allow_html=True)
    st.markdown('<div class="side-privacy">题库 ' + str(len(core.QUIZ)) + " 题 · 知识卡 "
                + str(len(core.CARDS)) + " 张 · 简答 " + str(len(core.SA)) + " 道</div>",
                unsafe_allow_html=True)

def _maybe_scroll_to_chat():
    """问完自动滚到最新一条回答；同一页的其他操作不打扰。"""
    if not st.session_state.pop("_scroll_to_chat", False):
        return
    components.html(
        """<script>
const doc = window.parent.document;
const win = window.parent;
const smooth = win.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth";
let n = 0;
const go = () => {
  const msgs = doc.querySelectorAll('[data-testid="stChatMessage"]');
  if (msgs.length) msgs[msgs.length - 1].scrollIntoView({block: "end", behavior: smooth});
  if (++n < 3) win.setTimeout(go, 300);
};
go();
</script>""",
        height=0,
    )

_page_header(panel, sid)

if panel == "课程问答":
    page_ask()
elif panel == "知识点速记":
    page_cards()
elif panel == "自测练习":
    page_quiz()
elif panel == "考前冲刺":
    page_sprint()
else:
    page_profile()
def _install_mobile_ui():
    """手机上点完导航自动收起抽屉，点空白处或按 Esc 也能关。"""
    components.html(
        """<script>
const doc = window.parent.document;
const win = window.parent;
if (!doc.__medtaMobileUi) {
  doc.__medtaMobileUi = true;
  const isMobile = () => win.matchMedia("(max-width: 900px)").matches;
  const closeDrawer = () => {
    const sb = doc.querySelector('[data-testid="stSidebar"]');
    if (!sb || sb.getAttribute("data-collapsed") === "true") return;
    const btn = sb.querySelector('[data-testid="stSidebarCollapseButton"] button');
    if (btn) btn.click();
  };
  doc.addEventListener("click", (ev) => {
    if (!isMobile()) return;
    const sb = doc.querySelector('[data-testid="stSidebar"]');
    if (!sb || sb.getAttribute("data-collapsed") === "true") return;
    const t = ev.target;
    if (sb.contains(t)) {
      return;
    }
    if (!(t.closest && t.closest('[data-testid="stExpandSidebarButton"]'))) closeDrawer();
  }, true);
  doc.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && isMobile()) closeDrawer();
  });
}
</script>""",
        height=0,
    )

_reset_scroll_on_nav(panel)
_install_mobile_ui()














