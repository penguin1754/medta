#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Coze 接口探针：用你自己的凭据实际打一次接口，把真实返回结构打印出来。

用法（在 medta 目录下）：
    python tools/coze_probe.py

凭据读取顺序：环境变量 COZE_BASE / COZE_BOT_ID / COZE_PAT，其次 medta/.env。
脚本只打印结构与内容预览，不打印完整令牌，可以放心把输出贴给我。
"""
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def explain(st):
    if st == 200:
        return "OK"
    if st == 400:
        return "请求参数不被接受：字段名或取值与该平台要求不一致（把原始响应发我即可定位）"
    if st == 401:
        return "鉴权失败：令牌无效、已过期，或没正确带 Authorizaton 头"
    if st == 403:
        return "无权限：多为该 Bot 未发布到 API 渠道，或账号套餐不含 API 调用"
    if st == 404:
        return "找不到：端点路径或 bot_id 不对"
    if st == 429:
        return "限流或额度用尽"
    return "其他状态码，把原始响应发我"


def load_env():
    env = {}
    f = ROOT / ".env"
    if f.exists():
        for line in f.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    for k in ("COZE_BASE", "COZE_BOT_ID", "COZE_PAT"):
        if os.environ.get(k):
            env[k] = os.environ[k]
    return env


def flat(s, n):
    return " ".join(str(s).split())[:n]


def post(url, payload, token):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data,
        headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"},
        method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.status, resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except Exception as e:
        return -1, "请求失败：" + str(e)


def get(url, token):
    req = urllib.request.Request(url, headers={"Authorization": "Bearer " + token}, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.status, resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except Exception as e:
        return -1, "请求失败：" + str(e)


def main():
    env = load_env()
    base = env.get("COZE_BASE", "https://api.coze.cn").rstrip("/")
    bot = env.get("COZE_BOT_ID", "")
    pat = env.get("COZE_PAT", "")
    print("base =", base)
    print("bot  =", bot or "（未填）")
    if not bot or not pat:
        print()
        print("缺少 COZE_BOT_ID 或 COZE_PAT。")
        print("bot_id 可以从商店链接里取到，令牌需要到扣子控制台创建个人访问令牌后粘贴进 .env。")
        return 1
    print("pat  = 已读取，长度", len(pat), "前缀", pat[:3])

    print()
    print("=== 测试 1：流式对话 POST /v3/chat （stream=true）===")
    st, body = post(base + "/v3/chat", {
        "bot_id": bot, "user_id": "medta_probe", "stream": True,
        "additional_messages": [{"role": "user", "content": "肱骨外科颈骨折最容易损伤哪条神经？请给出资料来源。"}],
    }, pat)
    print("HTTP", st, "|", explain(st))
    events = {}
    answer = []
    event = ""
    for line in body.splitlines():
        line = line.strip()
        if line.startswith("event:"):
            event = line[6:].strip()
            continue
        if not line.startswith("data:"):
            continue
        payload = line[5:].strip()
        if not payload or payload == "[DONE]":
            continue
        try:
            evt = json.loads(payload)
        except ValueError:
            continue
        if not isinstance(evt, dict):
            continue
        name = event or str(evt.get("event") or "unknown")
        events[name] = events.get(name, 0) + 1
        if name in ("conversation.chat.failed", "error"):
            print("接口报错：", flat(json.dumps(evt, ensure_ascii=False), 300))
        # 官方文档：data 后面直接是消息对象，不是 {"message": ...}
        if name.endswith("conversation.message.delta") and evt.get("type") == "answer":
            answer.append(str(evt.get("content") or ""))
        if name.endswith("conversation.message.completed") and evt.get("type") == "answer" and not answer:
            answer.append(str(evt.get("content") or ""))
    print("事件类型统计：", json.dumps(events, ensure_ascii=False))
    text = "".join(answer)
    print("拼接出的答案长度：", len(text))
    print("答案预览：", flat(text, 400))
    print("原始响应前 700 字符：", flat(body, 700))

    print()
    print("=== 测试 2：非流式 POST /v3/chat （stream=false）===")
    st, body = post(base + "/v3/chat", {
        "bot_id": bot, "user_id": "medta_probe", "stream": False, "auto_save_history": True,
        "additional_messages": [{"role": "user", "content": "名词解释：肝门静脉。并给出资料来源。"}],
    }, pat)
    print("HTTP", st, "|", explain(st))
    print("原始响应：", flat(body, 1200))
    try:
        obj = json.loads(body)
    except ValueError:
        obj = {}
    if obj.get("code") not in (0, "0", None):
        print("非流式接口报错：", flat(body, 500))
        print("优先处理这个错误，再跑流式测试。")
        return 1
    data = obj.get("data") or {}
    chat_id = data.get("id") or data.get("chat_id") or ""
    conv_id = data.get("conversation_id") or ""
    print("chat_id =", chat_id)
    print("conversation_id =", conv_id)

    if chat_id and conv_id:
        print()
        print("=== 测试 3：GET /v3/chat/retrieve （轮询任务状态）===")
        st, body = get(base + "/v3/chat/retrieve?conversation_id=" + conv_id + "&chat_id=" + chat_id, pat)
        print("HTTP", st, "|", explain(st), "：", flat(body, 700))

        print()
        print("=== 测试 4：GET /v3/conversation/message/list （取回答与出处字段）===")
        st, body = get(base + "/v3/conversation/message/list?conversation_id=" + conv_id, pat)
        print("HTTP", st, "|", explain(st))
        print("原始响应：", flat(body, 2500))
        try:
            msgs = json.loads(body).get("data") or []
        except ValueError:
            msgs = []
        print("消息条数：", len(msgs))
        if msgs:
            print("首条字段：", json.dumps(sorted(msgs[0].keys()), ensure_ascii=False))
            for m in msgs:
                if m.get("type") == "answer":
                    print("answer 消息字段：", json.dumps(sorted(m.keys()), ensure_ascii=False))
                    print("answer 内容：", flat(m.get("content", ""), 400))

    print()
    print("请把以上输出整段发给我（已不含令牌）。")
    print("重点看三件事：1) 有没有出处类字段；2) answer 消息的字段名；3) 能否用 conversation_id 复用会话。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
