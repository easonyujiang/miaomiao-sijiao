# 妙喵私教

把教学视频变成一对一私教——为每位视频博主生成有个人色彩的宠物 Agent。

B站/抖音视频页注入 🐱 猫咪私教：看片段 → 答案例题 → AI 判卷纠错 → 跳回讲解 → 下一关。同时为博主提供个人互动站，粉丝可聊天、追问视频、跳转片段。

---

## 项目结构

```
ewa/
├── run.py                     # 启动入口
├── pyproject.toml
│
├── ewa/                       # 后端 (Python/FastAPI)
│   ├── config.py              # 统一配置（env + dotenv）
│   ├── core/
│   │   └── app.py             # FastAPI 应用工厂 + 生命周期
│   ├── api/
│   │   ├── main.py            # 兼容入口
│   │   ├── lesson.py          # 私教答题 API
│   │   └── ext.py             # Chrome 插件 API
│   ├── site/
│   │   ├── repository.py      # SQLite 数据层 + 种子数据
│   │   ├── service.py         # 业务逻辑 + 风格学习 + 聊天
│   │   └── api.py             # 网站 REST 路由
│   ├── lesson/                # 课程核心实现
│   │   ├── scoring.py         # 关键词 + LLM 混合评分
│   │   ├── store.py           # 学习状态 SQLite 持久化
│   │   ├── feedback.py        # 猫咪反馈消息生成
│   │   ├── faq.py             # 离线 FAQ 知识库
│   │   └── subtitle.py        # 字幕加载与检索
│   └── llm/
│       └── client.py          # 统一 LLM 客户端 (Kimi → DeepSeek)
│
├── extension/                 # Chrome 插件 (MV3)
│   ├── manifest.json
│   ├── content_script.js
│   ├── content_style.css
│   ├── background.js
│   └── assets/
│
├── frontend/                  # Next.js 博主互动站
│   ├── app/                   # Home / Blog / Projects / Diary / Resume
│   └── components/            # PetAssistant 猫咪对话窗等
│
├── data/miaomiao/
│   ├── lessons/               # 课程 JSON
│   └── subtitles/             # B站字幕 JSON
│
├── tests/
│   ├── test_lesson_e2e.py
│   └── test_site_api.py
│
└── docs/
    ├── schema.sql             # 完整数据库结构
    ├── TEST-GUIDE.md          # 手动测试指南
    └── AUDIT-REPORT.md        # 多视频/多博主/模块化审计
```

## 快速启动

```bash
cd ewa

# 虚拟环境
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"

# 配置 API Key
cp .env.example .env
# 编辑 .env 填入至少一个 LLM API Key

# 启动
python run.py
# → 妙喵私教 ready. DB: data/miaomiao.db
```

## 多博主部署

设置环境变量切换到不同博主：

```bash
NEXT_PUBLIC_SITE_SLUG=新博主的slug
```

新博主数据通过种子数据或 API 注入 `profiles` 表，所有表通过 `profile_id` 隔离。

## 验证

```bash
# 健康检查
curl http://localhost:8000/health

# 运行测试
pytest tests/ -v
```

## 加载 Chrome 插件

1. Chrome → `chrome://extensions/` → 开发者模式
2.「加载已解压的扩展程序」→ 选择 `extension/` 目录
3. 打开 B站视频 `BV1mJ4m147PG` → 右下角 🐱 气泡

## API 端点

| 端点 | 说明 |
|------|------|
| `GET /health` | 健康检查 |
| `GET /api/site/{slug}` | 博主全量数据 |
| `POST /api/site/{slug}/chat` | 猫咪聊天 (LLM 风格改写) |
| `POST /api/ext/register_video` | 注册视频 + 字幕匹配 |
| `POST /api/ext/chat` | 视频时间戳问答 |
| `POST /api/lesson/load` | 加载课程 |
| `POST /api/lesson/quiz_submit` | 提交作答 |
| `GET /api/lesson/state/{session}/{lesson}` | 学习状态 |
| `POST /api/lesson/next_step` | 推进下一步 |
