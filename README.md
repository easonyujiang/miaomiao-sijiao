# 妙喵私教 v0.3.0

把教学视频变成一对一私教——为每位视频博主生成有个人色彩的宠物 Agent。

**四个模块**：🛠 管理后台 · 🌐 博主网站 · 🔌 Chrome 插件 · 💬 共创社区

---

## 项目结构

```
ewa/
├── run.py                         # 启动入口
├── pyproject.toml
│
├── ewa/                           # Python 后端
│   ├── config.py                  # 统一配置（env + dotenv）
│   ├── core/                      # 基础设施
│   │   ├── app.py                 # FastAPI 工厂 + 四模块路由
│   │   ├── middleware.py          # CORS + 限流
│   │   └── logging.py            # 日志（控制台/文件/SQLite）
│   ├── admin/                     # 🛠 管理后台
│   │   ├── api.py                 # /api/admin/* CRUD（21 表）
│   │   ├── auth.py                # Token 认证
│   │   ├── repository.py          # 通用 CRUD
│   │   └── static/index.html      # 独立 SPA 界面
│   ├── website/                   # 🌐 博主网站
│   │   ├── api.py                 # /api/site/* 路由
│   │   ├── service.py             # 聊天 + 风格学习
│   │   └── repository.py          # SQLite + 种子数据
│   ├── extension/                 # 🔌 Chrome 插件后端
│   │   ├── ext_api.py             # /api/ext/*
│   │   ├── lesson_api.py          # /api/lesson/*
│   │   ├── scoring.py             # 关键词 + LLM 评分
│   │   ├── store.py               # 学习状态持久化
│   │   ├── feedback.py            # 猫咪反馈
│   │   ├── faq.py                 # 离线 FAQ
│   │   └── subtitle.py            # 字幕检索
│   ├── community/                 # 💬 共创社区
│   │   ├── api.py                 # /api/community/*
│   │   └── __init__.py
│   └── llm/                       # LLM 客户端（Kimi → DeepSeek）
│       └── client.py
│
├── extension/                     # Chrome 插件 (MV3 JS)
│   ├── manifest.json
│   ├── content_script.js
│   ├── content_style.css
│   └── background.js
│
├── frontend/                      # Next.js 前端
│   └── app/                       # Home / Blog / Projects / Diary / Resume / Community
│
├── data/miaomiao/                 # 课程 JSON + 字幕 + SQLite DB
├── tests/
└── docs/                          # schema.sql + TEST-GUIDE + AUDIT-REPORT
```

## 快速启动

```bash
# 安装
python -m venv .venv && .venv\Scripts\activate
pip install -e ".[dev]"

# 配置
cp .env.example .env
# 编辑 .env → 填入 DEEPSEEK_API_KEY 或 MOONSHOT_API_KEY

# 启动
python run.py                         # → http://localhost:8000
cd frontend && npm install && npm run dev  # → http://localhost:3000
```

## 四模块概览

| 模块 | 入口 | 认证 |
|------|------|------|
| 🛠 管理后台 | `http://localhost:8000/admin` | Token（`ADMIN_TOKEN` 环境变量） |
| 🌐 博主网站 | `http://localhost:3000` | 公开 |
| 🔌 Chrome 插件 | `chrome://extensions/` → 加载 `extension/` | 公开（localhost CORS） |
| 💬 共创社区 | `http://localhost:3000/community` | 公开读写 |

## API 端点

| 端点 | 模块 | 说明 |
|------|------|------|
| `GET /health` | core | 健康检查 |
| `GET /api/site/{slug}` | website | 博主全量数据 |
| `POST /api/site/{slug}/chat` | website | 猫咪聊天（LLM 风格改写） |
| `POST /api/ext/register_video` | extension | 注册视频 + 字幕匹配 |
| `POST /api/ext/chat` | extension | 视频时间戳问答 |
| `POST /api/lesson/load` | extension | 加载课程 |
| `POST /api/lesson/quiz_submit` | extension | 提交作答（关键词+LLM评分） |
| `GET /api/lesson/state/{session}/{lesson}` | extension | 学习状态 |
| `GET \| POST \| PUT \| DELETE /api/admin/{table}` | admin | 数据库 CRUD（21 表） |
| `POST /api/admin/import/video` | admin | 批量导入视频+片段+课程 |
| `GET /api/admin/logs/list` | admin | 审计日志查询 |
| `GET \| POST /api/community/topics` | community | 社区话题 |
| `POST /api/community/topics/{id}/replies` | community | 话题回复 |

## 多博主

设置环境变量 `NEXT_PUBLIC_SITE_SLUG=新博主slug`，数据通过管理后台 API 注入，所有表由 `profile_id` 隔离。
