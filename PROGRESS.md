# 妙喵私教 — 项目进度

> 最后更新：2026-07-19

---

## 已完成

### 前端（Next.js 静态导出）

| 页面 | 路由 | 状态 | 说明 |
|------|------|------|------|
| 首页 | `/` | ✅ | 博客+社区帖子混排，按日期排序，带类型标签 |
| 个人主页 | `/profile` | ✅ | Hero + 项目精选 + 日记 + 简历 |
| 项目展示 | `/projects` | ✅ | 视频列表 + 片段导航 |
| 简历 | `/resume` | ✅ | 个人资料 |
| 日记 | `/diary` | ✅ | 6 篇日记，静态数据 |
| 博客 | `/blog` | ✅ | MDX 静态生成 |
| 博客详情 | `/blog/[slug]` | ✅ | `generateStaticParams` 预渲染 |
| 社区 | `/community` | ✅ | 对接后端 API，话题列表+详情+评论 |
| 管理后台 | `/admin/` | ✅ | 独立 SPA，FastAPI 静态托管 |
| 妙喵助手 | 全局 | ✅ | 聊天 + **语音输入**（Baidu ASR） |

### 后端（FastAPI + SQLite）

| 模块 | 端点 | 状态 |
|------|------|------|
| 站点数据 | `GET /api/site/{slug}` | ✅ |
| 视频详情 | `GET /api/videos/{id}` | ✅ |
| 日记 | `GET /api/site/{slug}/diary` | ✅ |
| 会话管理 | `POST /api/sessions` | ✅ |
| 宠物聊天 | `POST /api/site/{slug}/chat` | ✅ |
| 语音聊天 | `POST /api/site/{slug}/voice-chat` | ✅ |
| 语音识别 | `POST /api/speech-to-text` | ✅ |
| 视频问答 | `POST /api/ext/chat` | ✅ |
| 闯关答题 | `POST /api/lesson/*` | ✅ |
| 社区话题 | `GET/POST /api/community/topics` | ✅ |
| 社区回复 | `GET/POST /api/community/topics/{id}/replies` | ✅ |
| 管理后台 | `GET/POST/PUT/DELETE /api/admin/*` | ✅ |

### 插件端（Chrome Extension MV3）

| 功能 | 状态 | 说明 |
|------|------|------|
| B站视频注入 | ✅ | 识别 BV 号、注册视频、加载字幕 |
| 抖音视频注入 | ✅ | 识别视频 ID、匹配 B站字幕 |
| 视频问答 | ✅ | 基于当前时间戳问答 + 跳转 |
| 课程闯关 | ✅ | B站端完整支持 5 步课程、评分、进度 |
| 语音输入 | ✅ | 按住 🎤 录音，Baidu ASR 识别后自动发送 |
| 桌宠交互 | ✅ | 拖拽、随机唠叨、互动菜单 |

### 基础设施

| 项目 | 状态 | 说明 |
|------|------|------|
| nginx 反向代理 | ✅ | 80 → 443 重定向，443 → 8000 代理 |
| 自签名 SSL | ✅ | 当前使用 |
| 百度语音识别 | ✅ | 短语音识别标准版，支持 16kHz WAV |
| 远程服务器 | ✅ | 8.130.190.169 / miaomiao-cat.duckdns.org |
| 插件指向服务器 | ✅ | API_BASE 改为 `http://8.130.190.169:8000` |

---

## 已知缺陷 / 待修复

### 🔴 关键

- **语音输入依赖后端可用** — 网页端/插件端录音后都必须能访问后端 Baidu ASR；若后端未启动或 Key 无效则识别失败。

### 🟡 中等

- **语音输入浏览器兼容** — 插件端 `MediaRecorder` 在 Firefox/Safari 上可能不支持 `audio/webm;codecs=opus`，需回退到 `audio/webm` 或 `audio/mp4`。
- **插件端麦克风权限** — 用户首次需手动允许页面麦克风权限，拒绝后需引导去浏览器设置开启。
- **首页信息流无分页** — 社区帖子最多拉 50 条，无无限滚动。
- **首页信息流的社区帖子点击跳转** — 点击社区帖子跳到 `/community` 而非具体帖子详情。

### 🟢 低

- **博客只有 1 篇文章** — 需要补充内容。
- **社区功能不完整** — 无前端发帖/回复/点赞交互。
- **部署手动** — 每次需 git pull + npm run build + systemctl restart。
- **SEO 未优化** — openGraph 图片等未配置。
- **通关文案硬编码** — 课程全部通关时显示固定课程标题，当前只有一门课，影响有限。
- **抖音端缺少课程模式** — 抖音脚本只有自由问答，暂无课程数据。

---

## 技术架构

```
                    ┌──────────────────────────────────┐
                    │          阿里云 ECS               │
                    │                                  │
                    │   nginx (0.0.0.0:443 SSL)        │
                    │   └── proxy_pass → 127.0.0.1:8000│
                    │                                  │
                    │   uvicorn (0.0.0.0:8000)         │
                    │   ├── /api/*  → FastAPI           │
                    │   ├── /admin/ → 静态 SPA          │
                    │   └── /*      → 前端 dist/        │
                    │                                  │
                    │   SQLite: data/miaomiao.db        │
                    │   语音: Baidu ASR                 │
                    │   LLM: DeepSeek / Kimi            │
                    │                                  │
                    │   nginx SSL: /etc/nginx/ssl/      │
                    └──────────────────────────────────┘

访问方式:
  https://8.130.190.169:443     (自签名，需跳过警告)
  https://miaomiao-cat.duckdns.org (自签名，域名解析)
  http://8.130.190.169:8000     (直连后端，无 HTTPS)

构建流程:
  cd server/frontend && npm run build  → dist/
  systemctl restart miaomiao.service
```

**关键配置：**
- `next.config.mjs`: `output: 'export'`, `distDir: 'dist'`, `trailingSlash: true`
- `lib/site.ts`: 三级降级 — API → fallback.json → 静态 siteProfile
- `ewa/core/app.py`: FastAPI 挂载 `dist/` 到 `/`，SPAStaticFiles 处理客户端路由
- `nginx`: SSL 终止 + 反向代理，HTTP 自动跳转 HTTPS
- `ewa/config.py`: 从 `.env` 读取 `MOONSHOT_API_KEY` / `DEEPSEEK_API_KEY` / `BAIDU_API_KEY` / `BAIDU_SECRET_KEY`
- `extension/background.js`: Service Worker 代理所有插件 HTTP 请求，绕过 HTTPS 页面混合内容限制
- `extension/content/voice.js`: `MediaRecorder` 录音 + base64 上传 + 后端 Baidu ASR 识别

---

## 文件结构

```
server/
├── frontend/
│   ├── app/                      # Next.js 页面路由
│   ├── components/               # 页面组件
│   │   ├── community/            # 社区组件
│   │   ├── pet-assistant.tsx     # 妙喵助手（含语音输入）
│   │   └── site-header.tsx       # 导航栏
│   ├── lib/                      # 工具库
│   │   ├── community-api.ts      # 社区 API 客户端
│   │   ├── community-data.ts     # 社区类型定义
│   │   ├── use-voice-recorder.ts # 录音 Hook
│   │   ├── useVoiceChat.ts       # 语音聊天 Hook
│   │   └── use-speech-recognition.ts # Web Speech API Hook
│   ├── src/lib/api.ts            # 通用 API 客户端
│   └── dist/                     # 构建产物
├── ewa/
│   ├── core/app.py               # FastAPI 应用工厂
│   ├── speech/                   # 语音识别模块
│   ├── website/                  # 站点模块
│   ├── extension/                # 插件 API
│   ├── admin/                    # 管理后台
│   ├── community/                # 社区模块
│   └── config.py                 # 配置
├── data/
│   └── miaomiao/                 # SQLite + 课程/字幕 JSON
├── run.py                        # 启动入口
└── .env                          # 环境变量

extension/
├── manifest.json
├── background.js                 # Service Worker
├── sound.js / pet.js             # 音效与桌宠
├── content/
│   ├── bilibili.js               # B站脚本（含课程+语音）
│   ├── douyin.js                 # 抖音脚本（含语音）
│   ├── voice.js                  # 通用录音工具
│   └── style.css
└── ...
```
