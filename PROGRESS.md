# 妙喵私教 — 项目进度

> 最后更新：2026-07-18

---

## 已完成

### 前端（Next.js 静态导出）

| 页面 | 路由 | 状态 | 说明 |
|------|------|------|------|
| 首页 | `/` | ✅ | `getSite()` 三级降级（API → fallback.json → 静态数据） |
| 项目展示 | `/projects` | ✅ | 视频列表 + 片段导航 |
| 简历 | `/resume` | ✅ | 个人资料 |
| 日记 | `/diary` | ✅ | 6 篇日记，静态数据 |
| 博客 | `/blog` | ✅ | MDX 静态生成，目前 1 篇文章（song-zhiqiu-archive） |
| 博客详情 | `/blog/[slug]` | ✅ | `generateStaticParams` 预渲染 |
| 社区 | `/community` | ✅ | **已对接后端 API**，话题列表+详情+评论+语音控制 |
| 管理后台 | `/admin/` | ✅ | 独立 SPA，FastAPI 静态托管 |
| 妙喵助手 | 全局 | ✅ | 客户端组件，后端在线用 LLM，离线降级到本地 FAQ |

### 后端（FastAPI + SQLite）

| 模块 | 端点 | 状态 |
|------|------|------|
| 站点数据 | `GET /api/site/{slug}` | ✅ |
| 视频详情 | `GET /api/videos/{id}` | ✅ |
| 日记 | `GET /api/site/{slug}/diary` | ✅ |
| 会话管理 | `POST /api/sessions` | ✅ |
| 宠物聊天 | `POST /api/site/{slug}/chat` | ✅ |
| 视频问答 | `POST /api/ext/chat` | ✅ |
| 闯关答题 | `POST /api/lesson/*` | ✅ |
| 社区话题 | `GET/POST /api/community/topics` | ✅ |
| 社区回复 | `GET/POST /api/community/topics/{id}/replies` | ✅ |
| 管理后台 | `GET/POST/PUT/DELETE /api/admin/*` | ✅ |

### 本次会话修复

1. **构建超时问题** — `getSite()` 的 `fetch('/fallback.json')` 在构建时挂起 300 秒
   - 改为 `readFileSync` 直接读本地文件，不走网络
   - API fetch 加 5 秒 `AbortController` 超时
   - 文件：`lib/site.ts`

2. **社区页面对接真实 API** — 原来用 300 行硬编码 mock 数据
   - 新增 `lib/community-api.ts`：API 客户端 + 后端→前端类型映射
   - `content-feed.tsx`：从 `GET /api/community/topics` 拉取话题
   - `content-detail.tsx`：点击话题调 `GET /api/community/topics/{id}` 获取详情+回复
   - `comment-section.tsx`：接收父组件传入的回复列表
   - `community-data.ts`：精简为只导出类型和分类标签
   - 新增 `scripts/seed_community.py`：写入 8 个话题 + 12 条回复到 SQLite

---

## 未完成 / 待做

### 高优先级

- [ ] **服务器部署** — 代码已推送到 master，需要在服务器上 `git pull` + `npm run build` + 重启后端
- [ ] **社区种子数据** — 需要在服务器上运行 `python scripts/seed_community.py`
- [ ] **CORS 配置** — 确认 `EWA_CORS_ORIGINS` 包含前端域名（如果是分离部署）
- [ ] **阿里云安全组** — 确认 8000 端口入站 TCP 已放行

### 中优先级

- [ ] **社区功能完善**
  - [ ] 发帖功能（前端创建话题表单 → `POST /api/community/topics`）
  - [ ] 回复功能（前端回复输入框 → `POST /api/community/topics/{id}/replies`）
  - [ ] 点赞功能（`PUT /api/community/topics/{id}/like` — 后端待实现）
  - [ ] 分类筛选后端支持（当前前端筛选，后端已有 category 参数）

- [ ] **博客扩充** — 目前只有 1 篇 MDX 文章，需要补充内容

- [ ] **视频进度同步** — `PUT /api/videos/{video_id}/progress` 已有端点，前端播放器未对接

### 低优先级

- [ ] **部署自动化** — 目前手动 `git pull` + `npm run build`，可加 CI/CD 或部署脚本
- [ ] **Docker 化** — 当前单进程 uvicorn，可以容器化
- [ ] **nginx 反向代理** — 生产环境加 HTTPS + 静态资源缓存
- [ ] **SEO 优化** — 静态导出已支持 `generateMetadata`，但 openGraph 图片等未配置
- [ ] **社区语音发帖** — 当前语音只支持导航，不支持语音输入内容

---

## 技术架构

```
                    ┌──────────────────────────────┐
                    │        阿里云 ECS             │
                    │                              │
                    │   uvicorn (0.0.0.0:8000)     │
                    │   ├── /api/*  → FastAPI       │
                    │   ├── /admin/ → 静态 SPA      │
                    │   └── /*      → 前端 dist/    │
                    │                              │
                    │   SQLite: data/site.db        │
                    └──────────────────────────────┘

构建流程:
  cd server/frontend && npm run build  → dist/
  cd server && python run.py           → uvicorn serve dist/
```

**关键配置：**
- `next.config.mjs`: `output: 'export'`, `distDir: 'dist'`, `trailingSlash: true`
- `lib/site.ts`: 三级降级 — API → fallback.json → 静态 siteProfile
- `ewa/core/app.py`: FastAPI 挂载 `dist/` 到 `/`，SPAStaticFiles 处理客户端路由

---

## 文件结构

```
server/
├── frontend/
│   ├── app/
│   │   ├── layout.tsx          # 根布局，调用 getSite()
│   │   ├── page.tsx            # 首页
│   │   ├── blog/               # 博客（MDX）
│   │   ├── community/          # 社区（对接 API）
│   │   ├── diary/              # 日记
│   │   ├── projects/           # 项目展示
│   │   └── resume/             # 简历
│   ├── components/
│   │   ├── community/          # 社区组件（feed, detail, comments）
│   │   ├── pet-assistant.tsx   # 妙喵助手
│   │   └── ui/                 # UI 基础组件
│   ├── lib/
│   │   ├── community-api.ts    # 社区 API 客户端 ← 新增
│   │   ├── community-data.ts   # 社区类型定义
│   │   ├── posts.ts            # 博客文章
│   │   ├── site.ts             # getSite() 三级降级
│   │   └── voice-commands.ts   # 语音命令
│   ├── src/
│   │   ├── content/posts/      # MDX 博客文章
│   │   └── lib/api.ts          # 通用 API 客户端
│   ├── dist/                   # 构建产物（git ignored）
│   └── next.config.mjs
├── ewa/
│   ├── core/app.py             # FastAPI 应用工厂
│   ├── community/api.py        # 社区 API 路由
│   └── config.py               # 配置
├── scripts/
│   ├── generate_fallback.py    # 生成前端 fallback.json
│   └── seed_community.py       # 社区种子数据 ← 新增
├── data/site.db                # SQLite 数据库
└── run.py                      # 启动入口
```
