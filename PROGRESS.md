# 妙喵私教 — 项目进度

> 最后更新：2026-07-20

---

## 2026-07-20 维护性更新

**后端修复（29 个测试全过）**
- 🔴 BUG-011 根治：`persist_session` 的 INSERT OR REPLACE 触发 ON DELETE CASCADE 清空 lesson_attempts → 改 UPSERT，学习报告恢复真实错题数据源（含回归测试）
- 🔴 BUG-012：字幕路径 `parents[3]` 错误导致永远读不到字幕 JSON → 改走 `config.SUBTITLE_DIR`，字幕加 `[mm:ss]` 真实时间戳
- 妙喵意图判断：关键词快路径收紧（去掉"内容/介绍/是什么"裸词）+ LLM 意图分类兜底（video_query/diary/other），"你有什么看法"类问题不再错分 FAQ
- 摘要 prompt 加固：只允许引用字幕原文、时间戳必须真实、禁止编字幕外案例；带 video_id 上下文时可直接总结当前视频
- BUG-014：LLM 调用失败补日志；审计日志 handler 补 `check_same_thread=False`；slug 默认值统一为 `ashley`
- 新增 `scripts/fetch_subtitle.py`：B站 CC 字幕 → 项目字幕格式（⚠️ 需 SESSDATA cookie，见 KNOWN-ISSUES ISSUE-009）

**前端修复**
- BUG-013：首页空白页 → 客户端跳转 /community；runAction 补全 diary/blog/community target
- 语音按钮补 `navigator.mediaDevices` 检测；清理 5 个死代码文件；`NEXT_PUBLIC_SITE_URL` 默认 `http://8.130.190.169:8000`（部署脚本构建时注入）

**插件修复**
- 新增 `config.js` + popup 服务器地址设置（chrome.storage）；清除全部 duckdns 引用与无效 manifest 权限
- 通关文案改用课程标题；语音文件名按 mimeType 生成；错误提示不再误导 localhost

**入口策略（Demo 阶段定稿）**
- 文字：`http://8.130.190.169:8000`；网页端语音：`https://8.130.190.169`（自签名，接受一次警告）；插件端语音：现状可用
- nginx/systemd 配置收进 `infra/`

**部署与线上验证（已完成）**
- 新增 `deploy-backend.ps1`（后端一键部署）/ `verify-deploy.ps1`（部署验证）/ `test-live-chat.ps1`（线上聊天实测）
- 线上排障：生产库 videos 表缺罗翔视频行（字幕/课程是文件资产，website 查询走 DB），已插入 `BV1mJ4m147PG` 记录
- 线上实测三问全过：看法类提问 → video_query 基于字幕的观点回答；video_id 上下文 → 当前视频摘要；日记意图不受影响
- ⚠️ 经验：字幕 JSON、课程 JSON、videos 表行是三条独立数据通道，新视频上线时三者都要备齐

**管理后端重构 Part 1（已上线）**
- 新增 `admin/assets.py`：视频资产三通道统一管理（合并视图 / 幂等 upsert / 格式校验 / 级联删除）
- 新增 6 个 `/api/admin/assets/*` 端点；`import/video` 路径走 config；auth 加固（严格 Bearer + compare_digest）
- 计划文档：`docs/PLAN-ADMIN-REFACTOR.md`（Part 2/3/4 待做）
- 新增 10 个测试，全量 39 passed

**问答 → 精确跳转闭环（已上线）**
- 网站妙喵：问"有没有相关讨论"→ community 意图 + open_topic 按钮直达帖子（社区页新增 `?topic=id` 深链）
- 网站妙喵：视频摘要必带 `[mm:ss]` 时间戳，seek 按钮自动落到首个引用时间点（如"跳到 13:00"）
- 插件端：ext chat 新增社区讨论检索层，回答附帖子链接按钮（B站/抖音脚本均已支持）
- 顺带修复：community_topics 缺 video_id 列（community API 按视频过滤会 500 的潜伏 bug），schema + 幂等迁移补齐
- 新增 4 个测试，全量 43 passed

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
