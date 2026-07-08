# 妙喵私教

把教学视频变成一对一私教。抖音创变者大赛 · 赛道二：内容重构。

两条产品线共享同一后端：
- **博主互动站** — Lee Robinson 风格个人网站 + 🐱 妙喵对话窗
- **Chrome 插件** — B站/抖音视频页注入猫咪私教，法学案例练习评分

## 已实现

- Lee Robinson 风格的极简技术主页
- Home / Blog / Projects / Diary / Resume 独立路由
- MDX 文章内容层、搜索、独立文章 URL
- 页面级 SEO、静态元信息、sitemap、robots 与 RSS
- 本地 H.264 演示视频、章节时间轴和播放器跳转
- FastAPI 站点/视频/妙喵问答/会话/事件/播放进度 API
- SQLite 自动建表与本地资料种子数据
- 后端不可用时的前端离线 FAQ 降级
- Chrome 插件后端 API（视频注册/字幕匹配/LLM 问答）
- 视频私教 API（Lesson 加载/答题评分/步骤推进/游戏化）
- 数据来源状态与公开范围展示

## 本地运行

```bash
cd ewa
pip install -e ".[dev]"

# 构建前端
cd frontend && npm install && npm run build && cd ..

# 配置 LLM Key（至少一个）
cp .env.example .env
# 编辑 .env 填入 MOONSHOT_API_KEY 或 DEEPSEEK_API_KEY

python run.py
```

打开 `http://localhost:8000`。

主要页面：

- `/` — 个人简介、精选项目与近期文章
- `/blog` — MDX 文章列表与搜索
- `/projects` — 项目档案、视频播放器与章节跳转
- `/diary` — 日记时间线
- `/resume` — 经历和能力摘要
- `/feed.xml` — RSS
- `/sitemap.xml` — 站点地图

## API 端点

| 端点 | 说明 |
|------|------|
| `GET /api/site/{slug}` | 博主全量数据 |
| `GET /api/site/{slug}/diary` | 日记列表 |
| `POST /api/site/{slug}/chat` | 妙喵问答 |
| `POST /api/ext/register_video` | 注册视频 + 字幕匹配 |
| `POST /api/ext/chat` | 视频时间戳问答 |
| `POST /api/lesson/load` | 加载 Lesson |
| `POST /api/lesson/quiz_submit` | 提交作答评分 |
| `GET /api/lesson/state/{session}/{lesson}` | 学习状态 |

## 开发

```bash
# 终端一：后端
pip install -e ".[dev]"
python run.py

# 终端二：前端热更新
cd frontend && npm run dev
# Next.js 会将 /api 代理到 localhost:8000
```

## 验证

```bash
pytest -q
ruff check ewa/ tests/ run.py
cd frontend && npm run build
```

## 项目结构

```
ewa/                   # 后端
├── api/
│   ├── main.py        # FastAPI 入口
│   ├── ext.py         # Chrome 插件 API
│   └── lesson.py      # 私教答题 API
├── site/              # 博主网站业务层
│   ├── repository.py  # SQLite 数据层 + 种子数据
│   ├── service.py     # 业务逻辑
│   └── api.py         # REST 路由
└── config.py          # 统一配置

frontend/              # Next.js 前端
├── app/               # 页面路由
├── components/        # UI 组件 (PetAssistant...)
└── src/               # API 客户端 + 静态数据

data/miaomiao/         # 插件数据（字幕/Lesson JSON）
docs/                  # Schema + 项目文档
tests/                 # 测试
```

## DEMO 目标

```bash
# 1. 启动后端
cd ewa && python run.py

# 2. Chrome 加载插件
# chrome://extensions/ → 开发者模式 → 加载已解压 → 选择 extension/

# 3. 打开视频 → 气泡出现 → 开始学习
# B站 BV1mJ4m147PG（罗翔讲正当防卫）
```

详见 [docs/DEMO-RUNBOOK.md](docs/DEMO-RUNBOOK.md)
