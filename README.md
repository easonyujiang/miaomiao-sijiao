# 妙喵私教 v0.3.0

把教学视频变成一对一私教——为每位视频博主生成有个人色彩的宠物 Agent。支持文字/语音聊天、视频片段问答、课程闯关答题。

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

## 功能概览

| 端 | 功能 |
|---|---|
| 网页 | 博主个人主页、博客、社区、日记、项目展示、妙喵助手（文字+语音聊天） |
| 插件 | B站/抖音视频页注入妙喵面板，支持视频问答、课程闯关、语音答题 |
| 后端 | FastAPI 提供站点数据、聊天、视频问答、课程评分、语音识别、社区 API |

## 快速启动

### 服务端

```powershell
cd server
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"

Copy-Item .env.example .env
# 填入 MOONSHOT_API_KEY / DEEPSEEK_API_KEY / BAIDU_API_KEY / BAIDU_SECRET_KEY

python run.py                 # → http://localhost:8000

# 另开终端启动前端（开发模式）
cd frontend
npm install
npm run dev                   # → http://localhost:3000
```

### 插件端

1. Chrome → `chrome://extensions/` → 开发者模式
2. 加载已解压的扩展程序 → 选择 `extension/` 目录
3. 打开 B站视频页，妙喵面板自动出现

> 默认插件连接 `http://8.130.190.169:8000`。如需修改，点击插件图标在 popup 底部的"服务器地址"设置中修改（存 chrome.storage，刷新页面生效）。

## 技术栈

| 层 | 技术 |
|---|---|
| 后端 | Python FastAPI + SQLite + Uvicorn |
| 前端 | Next.js 15 + React 19 + Tailwind CSS + shadcn/ui |
| LLM | DeepSeek / Kimi (Moonshot) |
| 语音 | MediaRecorder 录音 + 百度短语音识别 (Baidu ASR，服务端转写) |
| 插件 | Chrome Extension MV3 + Lottie + howler.js + MediaRecorder |

## 主要 API

| 端点 | 说明 |
|------|------|
| `GET /health` | 健康检查 |
| `POST /api/site/{slug}/chat` | 猫咪聊天（LLM 风格改写） |
| `POST /api/site/{slug}/voice-chat` | 妙喵语音聊天（上传音频） |
| `POST /api/ext/register_video` | 注册视频 + 字幕匹配 |
| `POST /api/ext/chat` | 视频时间戳问答 |
| `POST /api/lesson/load` | 加载课程 |
| `POST /api/lesson/quiz_submit` | 提交答题 |
| `POST /api/speech-to-text` | 音频转文字（Baidu ASR） |
| `GET/POST/PUT/DELETE /api/admin/{table}` | 管理后台 CRUD |

## 语音功能

- **网页端**：妙喵助手面板支持按住麦克风说话，走百度 ASR 转文字后聊天。注意录音要求安全上下文：生产环境请用 `https://8.130.190.169`（自签名证书，接受一次警告即可），`http://` 裸 IP 入口下麦克风不可用。
- **插件端**：B站/抖音内容脚本的输入区支持按住 🎤 录音，通过 `background.js` 上传到后端 `/api/speech-to-text`，识别结果自动作为答案或问题发送。

## 文档

- [用户测试手册](docs/USER-TESTING-GUIDE.md)
- [服务端部署指导](docs/SERVER-DEPLOYMENT.md)
- [Chrome 插件打包指导](docs/EXTENSION-PACKAGING.md)
- [已知问题清单](docs/KNOWN-ISSUES.md)
