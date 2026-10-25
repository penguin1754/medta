#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""真实调用一次 Coze，验证令牌、Bot 发布状态和解析是否都通了。

会消耗 1 次 Coze 调用额度。用法（在 medta 目录下）：
    python tools/coze_live_test.py

令牌只从 .env 或环境变量读取，不会打印出来。
"""
import importlib.util
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("medta_app", ROOT / "backend" / "app.py")
app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app)


def main():
    pat = (os.environ.get("COZE_PAT") or "").strip()
    bot = (os.environ.get("COZE_BOT_ID") or "").strip()
    base = os.environ.get("COZE_BASE", "https://api.coze.cn")
    if not pat or not bot:
        print("缺少 COZE_PAT 或 COZE_BOT_ID。")
        print("把令牌填进 medta/.env 的 COZE_PAT= 后面再运行。")
        print("令牌入口：https://www.coze.cn/open/oauth/pats")
        return 2
    print("正在调用 Coze（会消耗 1 次额度）……")
    started = time.time()
    try:
        res = app.CozeEngine(pat, bot, base).ask("名词解释：肝门静脉。并说明依据来自哪份资料。")
    except app.EngineError as exc:
        print("调用失败：" + str(exc))
        print("排错顺序：4101 换令牌；4200 检查 bot_id 和是否发布到 API 渠道；其他把这句话发我。")
        return 1
    cost = time.time() - started
    print("调用成功，用时 %.1f 秒。" % cost)
    print("conversation_id =", res.get("conversation_id") or "（空）")
    print("答案预览：", " ".join(res.get("answer", "").split())[:500])
    print()
    print("下一步：重启 backend/app.py，首页顶部会显示“在线模型已接入”。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
