# 妙喵私教 — 项目进度

> 最后更新：2026-07-19

---

## 已完成

### 前端（Next.js 静态导出）

| 页面 | 路由 | 状态 | 说明 |
|------|------|------|------|
| 动态（信息流） | `/` | ✅ | 博客+社区帖子混排，按日期排序，带类型标签 |
| 个人主页 | `/profile` | ✅ | Hero + 项目精选 + 日记 + 简历 |
| 项目展示 | `/projects` | ✅ | 视频列表 + 片段导航 |
| 简历 | `/resume` | ✅ | 个人资料（独立页面仍保留） |
| 日记 | `/diary` | ✅ | 6 篇日记，静态数据 |
| 博客 | `/blog` | ✅ | MDX 静态生成，1 篇文章 |
| 博客详情 | `/blog/[slug]` | ✅ | `generateStaticParams` 预渲染 |
| 社区 | `/community` | ✅ | 对接后端 API，话题列表+详情+评论 |
| 管理后台 | `/admin/` | ✅ | 独立 SPA，FastAPI 静态托管 |
| 妙喵助手 | 全局 | ✅ | 聊天 + **语音输入**（Web Speech API） |

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

### 基础设施

| 项目 | 状态 | 说明 |
|------|------|------|
| nginx 反向代理 | ✅ | 80 → 443 重定向，443 → 8000 代理 |
| 自签名 SSL | ✅ | `/etc/nginx/ssl/miaomiao.crt`，10 年有效期 |
| Let's Encrypt 自动重试 | ✅ | 每 30 分钟尝试，成功后自动切换正规证书 |
| 语音输入 | ✅ | Web Speech API，麦克风按钮，实时转文字 |

### 本次会话完成

1. **首页重构** — 从分区展示改为统一信息流（博客+社区混排）
2. **个人主页** — 新增 `/profile`，整合 Hero、项目、日记、简历
3. **导航简化** — 动态、主页、社区、项目、管理
4. **语音系统清理** — 删除 voice-context、voice-commands、voice 组件
5. **语音输入** — Web Speech API 实现妙喵聊天语音转文字
6. **HTTPS** — nginx + 自签名证书 + LE 自动重试
7. **社区页面** — 删除残留的「🎤 全程语音可控」文案

---

## 已知缺陷 / 待修复

### 🔴 关键

- **Let's Encrypt 证书申请失败** — 阿里云安全组 80/443 端口规则已添加但 Let's Encrypt 仍无法验证（Connection reset / Timeout）
  - 当前方案：自签名证书 + 每 30 分钟自动重试
  - 用户访问需手动跳过浏览器安全警告
  - 可能原因：阿里云安全组规则延迟生效、网络层拦截、或需要重启 ECS 实例

- **HTTPS 仅限 443 端口** — HTTP 80 端口会 301 到 HTTPS，但部分用户可能不知道用 https:// 访问

### 🟡 中等

- **语音输入仅支持 Chrome/Edge** — Web Speech API 在 Firefox/Safari 不可用（组件已做 `isSupported` 检测，不支持时隐藏按钮）
- **语音输入依赖 HTTPS** — Web Speech API 要求安全上下文，HTTP 下不可用
- **首页信息流无分页** — 社区帖子最多拉 50 条，无无限滚动
- **首页信息流的社区帖子点击跳转** — 点击社区帖子跳到 `/community` 而非具体帖子详情

### 🟢 低

- **博客只有 1 篇文章** — 需要补充内容
- **社区功能不完整** — 无发帖、回复、点赞的前端交互
- **部署手动** — 每次需 git pull + npm run build + systemctl restart
- **SEO 未优化** — openGraph 图片等未配置

---

## 技术架构

```
                    ┌──────────────────────────────────┐
                    │          阿里云 ECS               │
                    │                                  │
                    │   nginx (0.0.0.0:443 SSL)        │
                    │   └── proxy_pass → 127.0.0.1:8000│
                    │                                  │
                    │   uvicorn (127.0.0.1:8000)       │
                    │   ├── /api/*  → FastAPI           │
                    │   ├── /admin/ → 静态 SPA          │
                    │   └── /*      → 前端 dist/        │
                    │                                  │
                    │   SQLite: data/site.db            │
                    │                                  │
                    │   nginx SSL: /etc/nginx/ssl/      │
                    │   LE cron: 每 30 分钟自动重试     │
                    └──────────────────────────────────┘

访问方式:
  https://8-130-190-169.nip.io  (自签名，需跳过警告)
  https://8.130.190.169:443     (同上)
  http://8.130.190.169:8000     (直连，无 HTTPS)

构建流程:
  cd server/frontend && npm run build  → dist/
  systemctl restart miaomiao.service
```

**关键配置：**
- `next.config.mjs`: `output: 'export'`, `distDir: 'dist'`, `trailingSlash: true`
- `lib/site.ts`: 三级降级 — API → fallback.json → 静态 siteProfile
- `ewa/core/app.py`: FastAPI 挂载 `dist/` 到 `/`，SPAStaticFiles 处理客户端路由
- `nginx`: SSL 终止 + 反向代理，HTTP 自动跳转 HTTPS
- `lib/use-speech-recognition.ts`: Web Speech API hook，支持中文，实时转写

---

## 文件结构

```
server/
├── frontend/
│   ├── app/
│   │   ├── layout.tsx              # 根布局
│   │   ├── page.tsx                # 首页（统一信息流）
│   │   ├── profile/page.tsx        # 个人主页 ← 新增
│   │   ├── blog/                   # 博客（MDX）
│   │   ├── community/              # 社区（对接 API）
│   │   ├── diary/                  # 日记
│   │   ├── projects/               # 项目展示
│   │   └── resume/                 # 简历
│   ├── components/
│   │   ├── community/              # 社区组件
│   │   ├── pet-assistant.tsx       # 妙喵助手（含语音输入）
│   │   ├── site-header.tsx         # 导航栏
│   │   └── ui/                     # UI 基础组件
│   ├── lib/
│   │   ├── community-api.ts        # 社区 API 客户端
│   │   ├── community-data.ts       # 社区类型定义
│   │   ├── posts.ts                # 博客文章
│   │   ├── site.ts                 # getSite() 三级降级
│   │   └── use-speech-recognition.ts  # 语音识别 hook ← 新增
│   ├── src/
│   │   ├── content/posts/          # MDX 博客文章
│   │   └── lib/api.ts              # 通用 API 客户端
│   └── dist/                       # 构建产物
├── ewa/
│   ├── core/app.py                 # FastAPI 应用工厂
│   ├── community/api.py            # 社区 API 路由
│   └── config.py                   # 配置
├── scripts/
│   ├── generate_fallback.py        # 生成 fallback.json
│   └── seed_community.py           # 社区种子数据
├── data/site.db                    # SQLite 数据库
├── run.py                          # 启动入口
└── nginx/                          # nginx 相关
    └── /etc/nginx/ssl/             # SSL 证书
```
