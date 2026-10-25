#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""离线测试 Coze SSE 解析，不需要令牌，也不会消耗额度。

用法（在 medta 目录下）：python tools/test_coze_parse.py
"""
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("medta_app", ROOT / "backend" / "app.py")
app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app)

fails = []


def check(name, ok, extra=""):
    print(("  [OK]   " if ok else "  [FAIL] ") + name + ("  " + extra if extra else ""))
    if not ok:
        fails.append(name)


def sse(event, data):
    return "event: " + event + "\n" + "data: " + json.dumps(data, ensure_ascii=False)


stream = "\n\n".join([
    sse("conversation.message.delta", {
        "id": "msg_1", "role": "assistant", "type": "answer",
        "content": "肱骨外科颈骨折", "conversation_id": "conv_1"}),
    sse("conversation.message.delta", {
        "id": "msg_1", "role": "assistant", "type": "answer",
        "content": "最容易损伤腋神经。", "conversation_id": "conv_1"}),
    sse("conversation.message.completed", {
        "id": "msg_1", "role": "assistant", "type": "answer",
        "content": "肱骨外科颈骨折最容易损伤腋神经。", "conversation_id": "conv_1"}),
    sse("conversation.chat.completed", {
        "id": "chat_1", "conversation_id": "conv_1", "status": "completed",
        "usage": {"token_count": 120}}),
    "event: done\ndata: [DONE]",
])

res = app.parse_coze_stream(stream)
check("delta 拼接成完整答案", res["answer"] == "肱骨外科颈骨折最容易损伤腋神经。",
      repr(res["answer"]))
check("取到 conversation_id", res["conversation_id"] == "conv_1")
check("取到 usage", res["usage"].get("token_count") == 120)
check("没有误报错误", res["error"] == "")

only_completed = sse("conversation.message.completed", {
    "role": "assistant", "type": "answer", "content": "完整答案",
    "conversation_id": "conv_2"})
res2 = app.parse_coze_stream(only_completed)
check("只有 completed 时也能取到答案", res2["answer"] == "完整答案")

failed = sse("conversation.chat.failed", {"code": 701231, "msg": "模型调用失败"})
res3 = app.parse_coze_stream(failed)
check("chat.failed 转成错误信息", "701231" in res3["error"] and "模型调用失败" in res3["error"],
      res3["error"])

http_200_error = json.dumps({"code": 4101, "msg": "The token you entered is incorrect."})
err = app._api_error_text(http_200_error)
check("HTTP 200 的错误体被识别", "4101" in err and "COZE_PAT" in err, err)

ok_body = json.dumps({"code": 0, "data": {"id": "chat_1"}})
check("code=0 不误报", app._api_error_text(ok_body) == "")

print()
if fails:
    print("失败 " + str(len(fails)) + " 项：" + "，".join(fails))
    sys.exit(1)
print("全部通过。解析逻辑正常，剩下只差真实 COZE_PAT 做在线验证。")
