# 妙喵私教

把教学视频变成一对一私教——博主的数字分身"妙喵"，横跨**个人网站**与**浏览器插件**两端：

- **网站端**：数字名片（主页/博客/日记/项目/社区）+ 妙喵助手（文字/语音聊天、视频模糊查询、社区讨论直达）
- **插件端**：B站/抖音视频页注入妙喵面板（视频问答、时间点跳转、5 关课程闯关、学习报告、语音答题）

> 当前定位：单博主复杂美观的 Demo。阿里云 2C4GB + SQLite + 远端 LLM API，无多租户。

## 架构

```
┌─────────────────────────────── 阿里云 ECS 8.130.190.169 ───────────────────────────┐
│  http://IP:8000  uvicorn（FastAPI，workers=2）← 文字入口                            │
│  https://IP:443  nginx（自签名证书）→ 127.0.0.1:8000 ← 语音入口（安全上下文）        │
│                                                                                     │
│  FastAPI                                                                          │
│   ├─ /api/site/*      网站：站点数据 / 聊天 / 语音聊天 / 日记                        │
│   ├─ /api/ext/*       插件：视频注册 / 视频问答 / 社区讨论检索                        │
│   ├─ /api/lesson/*    插件：课程加载 / 判卷 / 学习报告                               │
│   ├─ /api/community/* 社区：话题 / 回复                                             │
│   ├─ /api/admin/*     管理：通用 CRUD + 视频资产三通道管理（Bearer Token）            │
│   ├─ /api/speech-to-text  语音转文字（百度 ASR）                                    │
│   ├─ /                静态挂载 frontend/dist（Next.js 静态导出）                     │
│   └─ /admin/          管理后台 SPA                                                  │
│                                                                                     │
│  数据：SQLite（data/miaomiao.db）+ 文件资产（字幕 JSON / 课程 JSON）                  │
│  LLM：Kimi → DeepSeek（远端 API）   ASR：百度短语音识别                              │
└─────────────────────────────────────────────────────────────────────────────────────┘

Chrome 插件（MV3）→ B站/抖音视频页 → API_BASE（默认 http://8.130.190.169:8000，popup 可改）
```

## 项目结构

```
ewa/
├── server/                  # 服务端
│   ├── ewa/                 # FastAPI 后端
│   │   ├── core/            # 应用工厂 / 日志 / 中间件 / 音频工具
│   │   ├── website/         # 网站：站点数据 + 妙喵聊天（意图分类/视频摘要/社区检索）
│   │   ├── extension/       # 插件：ext 问答 + 课程 lesson + 存储
│   │   ├── community/       # 社区话题/回复
│   │   ├── admin/           # 管理后台：通用 CRUD + assets 视频资产 + auth
│   │   ├── speech/          # 语音识别（百度 ASR provider）
│   │   └── llm/             # LLM 客户端（Kimi → DeepSeek 降级）
│   ├── frontend/            # Next.js 15（App Router，静态导出）
│   ├── data/miaomiao/       # 策展资产：subtitles/ lessons/ scored_videos.json
│   ├── scripts/             # fetch_subtitle.py（B站字幕抓取）等
│   └── tests/               # pytest（43 个测试）
│
├── extension/               # Chrome 插件（MV3）
│   ├── config.js            # 服务器地址配置（chrome.storage + 默认值）
│   ├── background.js        # Service Worker（音频上传代理）
│   ├── content/             # bilibili.js / douyin.js / voice.js / style.css
│   └── popup/               # 弹窗（含服务器地址设置）
│
├── infra/                   # nginx.conf + miaomiao.service（生产配置收编）
├── deploy-backend.ps1       # 后端一键部署（本地 → 服务器）
├── deploy-community.ps1     # 前端一键部署（构建 dist → 服务器）
├── verify-deploy.ps1        # 部署验证    audit-server.ps1   # 服务器↔本地 md5 审计
├── test-live-chat.ps1       # 线上聊天实测  get-admin-token.ps1 # 取回 ADMIN_TOKEN
└── docs/                    # 文档
```

## 核心功能

| 端 | 功能 |
|---|---|
| 网站 | 妙喵聊天：LLM 意图分类（video_query/diary/community/FAQ），视频查询基于真实字幕 + `[mm:ss]` 时间戳，seek 按钮直达知识点 |
| 网站 | 社区讨论检索："有没有关于 X 的讨论" → open_topic 按钮直达帖子详情（`?topic=id` 深链） |
| 插件 | 视频问答带 `[SEEK:秒]` 时间点跳转；问"有没有相关讨论" → 帖子链接按钮 |
| 插件 | 课程闯关：5 关看片段答题、星级/小鱼干/成长值、通关学习报告（基于真实错题 lesson_attempts） |
| 两端 | 语音输入：MediaRecorder 录音 → 百度 ASR → 文字聊天链路 |
| 管理 | `/admin/` 通用 CRUD + `/api/admin/assets/videos` 视频资产三通道（DB 行/字幕/课程）统一管理 |

## 快速启动（本地开发）

```powershell
# 后端
cd server
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
Copy-Item .env.example .env   # 填 MOONSHOT/DEEPSEEK/BAIDU 的 Key
python run.py                 # → http://localhost:8000

# 前端（另开终端）
cd server/frontend
npm install
npm run dev                   # → http://localhost:3000

# 测试
cd server; python -m pytest tests/
```

**插件**：Chrome → `chrome://extensions/` → 开发者模式 → 加载 `extension/`。默认连 `http://8.130.190.169:8000`，点插件图标在 popup 底部"服务器地址"可改（存 chrome.storage，刷新页面生效）。

## 生产环境

| 入口 | 用途 |
|---|---|
| `http://8.130.190.169:8000` | 网站文字访问 / 插件 API |
| `https://8.130.190.169` | 网页端语音（自签名证书，接受一次警告；录音需要安全上下文） |

```powershell
.\deploy-backend.ps1      # 后端部署（ewa/ + scripts/ → 服务器，重启+健康检查）
.\deploy-community.ps1    # 前端部署（npm build → dist 上传替换）
.\verify-deploy.ps1       # 验证：主机名/服务状态/文件版本
.\audit-server.ps1        # 审计：服务器与本地全部 .py md5 对比
.\test-live-chat.ps1      # 线上聊天接口实测
```

凭据放 `.ssh-credentials.json`（gitignore）：`{"username","password","host","admin_token"}`。

## 主要 API

| 端点 | 说明 |
|------|------|
| `GET /health` | 健康检查 |
| `POST /api/site/{slug}/chat` | 妙喵聊天（意图分类 + 风格改写） |
| `POST /api/site/{slug}/voice-chat` | 语音聊天（ASR + 聊天链路） |
| `POST /api/ext/chat` | 插件视频问答（社区检索 → LLM → 字幕 → FAQ） |
| `POST /api/lesson/quiz_submit` | 课程判卷（关键词 + LLM 混合评分） |
| `GET /api/lesson/report/{session}/{lesson}` | 学习报告（基于真实答题记录） |
| `POST /api/speech-to-text` | 音频转文字（百度 ASR） |
| `GET/POST /api/community/topics*` | 社区话题/回复 |
| `GET/POST /api/admin/assets/videos` | 视频资产三通道管理（Bearer） |
| `GET/POST/PUT/DELETE /api/admin/{table}` | 管理后台通用 CRUD（Bearer） |

## 数据资产与新视频上线

一个"可上线的视频"需要三条数据通道齐备（管理后台 `POST /api/admin/assets/videos` 可一站式完成）：

1. **videos 表行**（SQLite）— 网站妙喵视频查询的数据源
2. **字幕 JSON**（`data/miaomiao/subtitles/{video_id}.json`）— 摘要质量的基础，`scripts/fetch_subtitle.py <BV号> --cookie "SESSDATA=..."` 可抓取
3. **课程 JSON**（`data/miaomiao/lessons/`，可选）— 插件课程模式

## 文档

- [项目进度](PROGRESS.md)
- [服务端部署指导](docs/SERVER-DEPLOYMENT.md)
- [Chrome 插件打包指导](docs/EXTENSION-PACKAGING.md)
- [用户测试手册](docs/USER-TESTING-GUIDE.md)
- [已知问题清单](docs/KNOWN-ISSUES.md)
- [管理后端重构计划](docs/PLAN-ADMIN-REFACTOR.md)
