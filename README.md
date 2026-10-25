# 医学课程 AI 助教（MedTA）

郑州大学首届 AI 智能体创新应用大赛参赛项目 · 对应任务清单 A2（课程助教方向）
课程：系统解剖学（内容范围由团队确定）

四个模块构成一条学习闭环：

    一 课程问答    只答已审核资料里的内容，附出处；越界问题明确拒答
    二 知识点速记  翻卡式回忆，自评「记住了 / 没记住」，按间隔重复排下次复习
    三 自测练习    选择题即时判分，附解析与出处，答错自动进错题本
    四 学习档案    掌握度环、学习活跃度、复习节奏、缺口、错题本、复习清单

页首是「今日复习处方」：今天该复习哪几张、其中几张以前答错过、连续几天在学，
一眼看完并可直接开始今日复习。

不做教师端。判分、缺口记录、复习清单、复习排期全部由确定性代码完成，模型不参与，
同一份作答任何时候结果一致，现场可复现。

## 两种入口

两套界面共用 `backend/app.py` 里的同一套内容、判分、间隔重复和 Coze 调用逻辑：

    Streamlit 版（公网部署用）  streamlit run streamlit_app.py
    原网页版（设计更完整）      python backend/app.py   ->  http://127.0.0.1:8787

Streamlit 版适合直接连 GitHub + Streamlit Community Cloud，几分钟能拿到一个公网网址。
它的数据存在容器本地 SQLite 里，**应用休眠/重新部署后学习记录会重置**；
正式答辩要保留完整学习档案时，用原网页版或自己配一台常开的服务器。

## 间隔重复怎么算

SM-2 简化版，规则写在 `Store.review_card`，评委可以逐行核对：

    记住了  -> 间隔 1 天 -> 3 天 -> 上次间隔 x 难度系数（上限 180 天），系数 +0.1
    没记住  -> 间隔归 0（立刻回到今日队列），系数 -0.2，遗忘次数 +1

难度系数初始 2.5，取值区间 1.3 ~ 2.8。没学过的卡视为立即到期，
所以新用户的「今日复习处方」就是全部卡片，不会出现空面板。

## 怎么跑

    cd medta
    python backend/app.py

浏览器打开 http://127.0.0.1:8787
只用 Python 标准库，不需要 pip install，断网也能演示完整流程。

需要别的机器（比如队友电脑）打开时：

    set MEDTA_HOST=0.0.0.0 && python backend/app.py
    然后访问 http://<本机局域网IP>:8787

注意 8787 只有在本机后端进程运行时才有效，关掉窗口进程就停了，
要重新运行上面的命令（或 start_demo.cmd）。

### Streamlit 版与公网部署

本地：

    pip install -r requirements.txt
    streamlit run streamlit_app.py

Streamlit Community Cloud：

1. 把仓库推到 GitHub（入口文件保持 `streamlit_app.py`）。
2. 打开 https://share.streamlit.io ，新建 App，选这个仓库、`main` 分支、
   入口文件 `streamlit_app.py`。
3. 在 App 的 **Secrets** 面板里填：

       COZE_BASE = "https://api.coze.cn"
       COZE_BOT_ID = "7700440011057102875"
       COZE_PAT = "pat_你的令牌"
       COZE_MAX_CALLS = "100"
       COZE_PER_USER = "10"

4. 点 Deploy。首次启动会安装 `requirements.txt`，大约两三分钟。

不要把真实令牌写进 `streamlit_app.py`、`secrets.toml.example` 或任何提交到仓库的文件。
本地开发可以复制 `.streamlit/secrets.toml.example` 为 `.streamlit/secrets.toml`，
该文件已被 `.gitignore` 忽略。

## 引擎与额度

默认走 Coze API（`MEDTA_ENGINE=coze`），回答顺序见 `answer_question`：

    1. 新会话里同一问题命中缓存          -> 直接返回，不消耗额度
    2. Coze 已配置且还有余额              -> 调 Coze，同一浏览器复用 conversation_id
    3. Coze 未配置 / 额度用尽 / 调用失败  -> 回落本地知识卡
    4. 本地也没有依据                     -> 明确拒答，不硬编答案

Coze 免费额度有限，所以有三道闸：

    COZE_MAX_CALLS   全站累计上限，默认 100
    COZE_PER_USER    单个浏览器每天上限，默认 10
    同一问题缓存，重复提问不再消耗额度

判分、缺口记录、复习排期仍然全部由确定性代码完成，模型不参与。

启用 Coze：

1. 打开 https://www.coze.cn/open/oauth/pats 创建个人访问令牌（只需一次）。
2. 确认 Bot 已发布，并且在发布渠道里勾选了 **API**。
3. 把令牌填进 `medta/.env`：

       COZE_BASE=https://api.coze.cn
       COZE_BOT_ID=7700440011057102875
       COZE_PAT=pat_你的令牌

4. 先验证一次（会消耗 1 次额度）：

       python tools/coze_live_test.py

5. 看到“调用成功”后重启 `backend/app.py`，首页顶部会显示“在线模型已接入”。

`.env` 已被 `.gitignore` 忽略，不要提交、不要贴到聊天或截图里。
接口细节按官方文档 `docs.coze.cn/developer_guides/chat_v3` 实现；解析逻辑有离线测试：

    python tools/test_coze_parse.py

## 微信小程序怎么接

小程序只负责界面，**必须调你们自己的后端**（`POST /api/ask`），再由后端调 Coze。
不要把 `COZE_PAT` 写进小程序代码：小程序包可以被反编译，令牌泄露等于把账号额度交给别人，
比赛附件 3 也明确禁止泄露密钥。

## 目录

    backend/app.py        后端 + 引擎适配器（换在线模型只动 CozeEngine 这个类）
    knowledge/cards.json  知识卡（当前为占位示例，必须换成团队审核后的内容）
    knowledge/quiz.json   自测题（同上）
    frontend/index.html   单页应用（零依赖单文件，断网可演示）
    docs/screenshots/     真实渲染截图（申报表 / 答辩可用）
    tools/smoke_test.py   接口冒烟测试（自起后端、打一轮接口、断言结果）
    tools/coze_probe.py   Coze 原始响应探针（排查字段用）
    tools/coze_live_test.py  真实调用一次 Coze，验证令牌与 Bot 发布状态
    tools/test_coze_parse.py 离线测试流式解析，不消耗额度
    data_in/              放选定的 PDF，供后续提取结构化内容
    db/                   匿名学习记录（自动生成，不入库）

## 接口

    GET  /api/health               版本、引擎、额度、知识卡/题目数量、章节
    GET  /api/cards?sid=&due=1     知识卡列表（含掌握状态与复习排期；due=1 只返回到期）
    GET  /api/quiz?chapter=&n=     取自测题（不下发答案）
    GET  /api/sources              资料来源汇总 + 合规声明
    GET  /api/profile/<sid>        学习档案（概览 / 章节 / 缺口 / 错题 / 复习清单 /
                                   复习节奏 sched / 活跃度 activity / 到期数 due / 连续天数 streak）
    POST /api/ask                  {sid, question} 按三层策略作答
    POST /api/cards/review         {sid, card_id, known}
    POST /api/quiz/answer          {sid, qid, choice}
    POST /api/reset                {sid} 清空本机记录

## 验证

    $env:PYTHONIOENCODING="utf-8"; [Console]::OutputEncoding=[System.Text.Encoding]::UTF8
    python tools/smoke_test.py

36 项断言覆盖：健康检查、首页、问答命中与拒答、知识卡及掌握状态、速记两种标记、
自测取题（不泄露答案）、判分对错、档案缺口与复习清单、资料来源、清空归零，
以及间隔重复的完整链路：新卡到期 -> 记住后推后 1 天 -> 从到期列表消失 -> 没记住当场回到到期。

## 后续计划

内容流水线：从 data_in 的资料提取，扩充 cards.json / quiz.json 与评测集。
效果验证脚本：有出处率、拒答正确率、医学错误数、前后测成绩对比。

## 合规要点

学习记录只用匿名 sid（前端随机生成，不含姓名学号），不访问学校任何系统；
页面上不出现学校名称与「学生端」等字样，对外演示时按团队口径称呼项目；
资料为团队整理的课程复习资料，正式提交前必须把占位内容替换为审核后的版本；
页面与申报表中如实标注数据来源，演示数据不得当作实时结果。
