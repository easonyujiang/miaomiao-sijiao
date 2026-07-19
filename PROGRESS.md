# 妙喵私教 — 项目进度

> 最后更新：2026-07-20 ｜ 测试：43 passed ｜ 服务器与本地代码 md5 审计一致

---

## 当前状态总览

**定位**：单博主复杂美观 Demo。阿里云 2C4GB + SQLite + 远端 LLM（Kimi→DeepSeek）+ 百度 ASR。

**生产入口**：文字 `http://8.130.190.169:8000` ｜ 网页端语音 `https://8.130.190.169`（自签名，接受一次警告）｜ duckdns 已弃用

### 前端（Next.js 静态导出）

| 页面 | 路由 | 状态 | 说明 |
|------|------|------|------|
| 首页 | `/` | ✅ | 客户端跳转 `/community`（静态导出不支持 redirects） |
| 社区 | `/community` | ✅ | 话题列表+详情+评论；支持 `?video_id=` 过滤与 `?topic=id` 深链 |
| 个人主页 | `/profile` | ✅ | Hero + 项目精选 + 日记 + 简历 |
| 项目展示 | `/projects` | ✅ | 视频列表 + 片段导航，支持 `?video=&t=` 定位 |
| 日记 | `/diary` | ✅ | 6 篇日记 |
| 博客 | `/blog`、`/blog/[slug]` | ✅ | MDX 静态生成（1 篇） |
| 简历 | `/resume` | ✅ | |
| 管理后台 | `/admin/` | ✅ | 独立 SPA，Bearer Token 登录 |
| 妙喵助手 | 全局 | ✅ | 文字+语音；意图分类；视频查询；社区直达 |

### 后端（FastAPI + SQLite）

| 模块 | 端点 | 状态 |
|------|------|------|
| 站点数据/日记/会话 | `GET /api/site/*`、`POST /api/sessions` | ✅ |
| 妙喵聊天 | `POST /api/site/{slug}/chat` | ✅ LLM 意图分类 + 关键词快路径 |
| 语音聊天/识别 | `voice-chat`、`/api/speech-to-text` | ✅ 百度 ASR |
| 插件问答 | `POST /api/ext/chat` | ✅ 社区检索 → LLM → 字幕 → FAQ |
| 课程闯关 | `POST /api/lesson/*` | ✅ 混合评分（关键词 + LLM） |
| 学习报告 | `GET /api/lesson/report/...` | ✅ 基于真实错题 lesson_attempts |
| 社区 | `GET/POST /api/community/topics*` | ✅ |
| 管理后台 | `GET/POST/PUT/DELETE /api/admin/*` | ✅ 通用 CRUD + 审计日志 |
| 视频资产管理 | `GET/POST/PUT/DELETE /api/admin/assets/*` | ✅ 三通道统一管理 |

### 插件端（Chrome MV3）

| 功能 | 状态 | 说明 |
|------|------|------|
| B站/抖音注入 | ✅ | 识别视频、注册、字幕匹配 |
| 视频问答 | ✅ | `[SEEK:秒]` 时间点跳转按钮 |
| 社区讨论检索 | ✅ | 问"有没有相关讨论"→ 帖子链接按钮 |
| 课程闯关 | ✅ | B站 5 关课程、评分、进度（抖音仅自由问答） |
| 学习报告 | ✅ | 通关自动生成，含真实错题与复习建议（可点击回看） |
| 语音输入 | ✅ | 按住 🎤 → background 代理 → 百度 ASR |
| 服务器地址配置 | ✅ | popup 设置，chrome.storage，默认 `http://8.130.190.169:8000` |

### 基础设施

| 项目 | 状态 | 说明 |
|------|------|------|
| nginx + 自签名 SSL | ✅ | 80→443 重定向，443→8000 反代，配置在 `infra/` |
| systemd | ✅ | `infra/miaomiao.service`，uvicorn workers=2 |
| 一键部署 | ✅ | `deploy-backend.ps1` / `deploy-community.ps1` |
| 部署验证 | ✅ | `verify-deploy.ps1` / `audit-server.ps1` / `test-live-chat.ps1` |
| 凭据管理 | ✅ | `.ssh-credentials.json`（gitignore，含 admin_token） |

---

## 2026-07-20 里程碑（数据与对话质量大修）

**🔴 核心 bug 根治**
- BUG-011：`INSERT OR REPLACE` 触发 ON DELETE CASCADE 清空 lesson_attempts → 改 UPSERT（含回归测试）
- BUG-012：字幕路径 `parents[3]` 错误导致永远读不到字幕 JSON → 走 `config.SUBTITLE_DIR`，字幕加 `[mm:ss]` 时间戳
- BUG-013：首页空白页（静态导出不支持 redirects 且 page.tsx 返回 null）
- BUG-014：LLM 调用失败静默 → 补日志；审计日志 handler 跨线程修复
- BUG-015：插件通关文案/地址硬编码 → 动态课程标题 + popup 配置化
- BUG-016：community_topics 缺 video_id 列 → schema + 幂等迁移
- BUG-017：摘要幻觉 + seek 按钮落点不准 → prompt 强制引用字幕 + 提取首个时间戳

**✨ 新能力**
- 妙喵 LLM 意图分类（video_query/diary/community），"有什么看法"类问题不再错分
- 问答 → 精确跳转闭环：视频 seek 按钮落到 `[mm:ss]`；社区 open_topic 直达帖子；社区页 `?topic=id` 深链
- 管理后台 `/api/admin/assets/*`：视频资产三通道（DB 行/字幕/课程）统一视图与一站式 upsert
- `scripts/fetch_subtitle.py`：B站 CC 字幕抓取（需 SESSDATA，见 KNOWN-ISSUES ISSUE-009）
- 线上实测四问全过（看法/当前视频/日记/讨论检索）

**⚠️ 经验**：字幕 JSON、课程 JSON、videos 表行是三条独立数据通道，新视频上线必须三者备齐（用 assets 端点一站式完成）。

---

## 已知问题（摘要，详见 docs/KNOWN-ISSUES.md）

- 🔴 语音输入依赖后端百度 ASR 可用
- 🟡 B站字幕抓取需登录 cookie（ISSUE-009）；`/api/speech-to-text` 与社区发帖无鉴权（ISSUE-010）；popup 改地址后 SITE_URL 跳转不联动（ISSUE-011）
- 🟢 抖音端无课程模式；社区无发帖/点赞交互；博客只有 1 篇；SEO 未配置；首页信息流无分页

---

## 下一步（按优先级）

1. 管理后端重构 Part 2/3：`/extension/learning` 学习数据视图、`/overview` 管理台首页、SPA 视频资产页（见 docs/PLAN-ADMIN-REFACTOR.md）
2. 插件重新加载后实测课程通关报告（验证 attempts 真实错题）
3. 中期：正式 HTTPS（域名 + ICP 备案）、社区互动完善
4. 不做（等有真实需求）：Postgres / 向量检索 / 多租户 / Chrome 商店上架
