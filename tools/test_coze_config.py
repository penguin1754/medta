# -*- coding: utf-8 -*-
"""凭据校验的回归测试：不联网、不消耗 Coze 额度。"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import backend.app as core  # noqa: E402

BOT = "7700440011057102875"
fails = []


def expect(name, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + name + (" | " + detail if detail and not cond else ""))
    if not cond:
        fails.append(name)


os.environ["COZE_BOT_ID"] = BOT
os.environ["COZE_BASE"] = "https://api.coze.cn"

os.environ["COZE_PAT"] = "pat_" + "a" * 40
expect("正常令牌可用", core.coze_available(), core.coze_config_problem())

os.environ["COZE_PAT"] = '"pat_' + "a" * 40 + '"'
expect("引号被清理", core.coze_available(), core.coze_config_problem())

os.environ["COZE_PAT"] = " pat_" + "a" * 40 + "\n"
expect("空白被清理", core.coze_available(), core.coze_config_problem())

os.environ["COZE_PAT"] = "pat_示例占位符内容"
p = core.coze_config_problem()
expect("中文占位符被判为不可用", (not core.coze_available()) and "非英文字符" in p, p)

os.environ["COZE_PAT"] = ""
expect("空令牌提示未配置", "未配置" in core.coze_config_problem())

os.environ["COZE_PAT"] = "pat_" + "a" * 40
os.environ["COZE_BOT_ID"] = ""
expect("空 Bot ID 被判为不可用", not core.coze_available(), core.coze_config_problem())

os.environ["COZE_BOT_ID"] = BOT
os.environ["COZE_PAT"] = "pat_示例占位符内容"
out = core.answer_question("腋神经损伤会有什么表现？", "testcfg")
expect("凭据错误时不报网络错、走本地", out.get("route") in ("local_card", "no_engine"),
       str(out.get("route")))
expect("凭据错误时给出说明", bool(out.get("note")), str(out.get("note")))

print("")
print("FAILED " + str(len(fails)) if fails else "ALL OK")
sys.exit(1 if fails else 0)
