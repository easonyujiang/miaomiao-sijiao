# 妙喵私教 v0.3.0

把教学视频变成一对一私教——为每位视频博主生成有个人色彩的宠物 Agent。

## 项目结构

```
ewa/
├── server/                # 服务端（Python + Next.js）
│   ├── ewa/               # FastAPI 后端
│   ├── frontend/          # Next.js 前端
│   ├── data/              # SQLite + 课程/字幕数据
│   ├── tests/             # pytest 测试
│   ├── run.py             # 启动入口
│   └── .env               # 环境变量
│
├── extension/             # 插件端（Chrome Extension MV3）
│   ├── manifest.json
│   ├── background.js      # Service Worker
│   ├── content/           # B站/抖音内容脚本
│   └── ...
│
└── docs/                  # 文档
```

## 快速启动

### 服务端

```powershell
cd server
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"

Copy-Item .env.example .env   # 填入 MOONSHOT_API_KEY 或 DEEPSEEK_API_KEY

python run.py                 # → http://localhost:8000

# 另开终端启动前端
cd frontend
npm install
npm run dev                   # → http://localhost:3000
```

### 插件端

1. Chrome → `chrome://extensions/` → 开发者模式
2. 加载已解压的扩展程序 → 选择 `extension/` 目录
3. 打开 B站视频页，妙喵面板自动出现

## 技术栈

| 层 | 技术 |
|---|------|
| 后端 | Python FastAPI + SQLite + Uvicorn |
| 前端 | Next.js 15 + React 19 + Tailwind CSS + shadcn/ui |
| LLM | Kimi (Moonshot) → DeepSeek 自动降级 |
| 插件 | Chrome Extension MV3 + Lottie + howler.js |

## API

| 端点 | 说明 |
|------|------|
| `GET /health` | 健康检查 |
| `POST /api/site/{slug}/chat` | 猫咪聊天（LLM 风格改写） |
| `POST /api/ext/register_video` | 注册视频 + 字幕匹配 |
| `POST /api/ext/chat` | 视频时间戳问答 |
| `POST /api/lesson/load` | 加载课程 |
| `POST /api/lesson/quiz_submit` | 提交答题 |
| `GET/POST/PUT/DELETE /api/admin/{table}` | 管理后台 CRUD |

## 文档

- [用户测试手册](docs/USER-TESTING-GUIDE.md)
- [服务端部署指导](docs/SERVER-DEPLOYMENT.md)
- [Chrome 插件打包指导](docs/EXTENSION-PACKAGING.md)
- [已知问题清单](docs/KNOWN-ISSUES.md)
