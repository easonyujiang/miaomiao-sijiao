# 妙喵私教 · 问题清单

> 审计日期：2026-07-08 | 版本：0.2.0 | 更新：P0 已修复，P1 已修复

---

## 状态总览

| 优先级 | 总数 | 已修复 | 剩余 |
|--------|------|--------|------|
| P0 | 2 | **2** | 0 |
| P1 | 6 | **6** | 0 |
| P2 | 5 | 0 | 5 |

---

## P0 — 阻断性问题 ✅ 全部已修复

### P0-1: Dockerfile 引用不存在的 schema 文件 ✅ FIXED

- **文件**：[Dockerfile:10](Dockerfile#L10)
- **问题**：`COPY docs/personal-site-schema.sql docs/` — 该文件不存在，实际 schema 文件是 `docs/schema.sql`
- **修复**：改为 `COPY docs/schema.sql docs/`
- **提交**：2026-07-08

### P0-2: CORS 全部开放 ✅ FIXED

- **文件**：[ewa/core/middleware.py](ewa/core/middleware.py)
- **问题**：`allow_origins=["*"]` + `allow_methods=["*"]` + `allow_headers=["*"]`
- **修复**：通过环境变量 `EWA_CORS_ORIGINS` 配置，默认仅允许 localhost 开发 origin。设为 `*` 可恢复全开（调试用）
- **提交**：2026-07-08

---

## P1 — 重要问题 ✅ 全部已修复

### P1-1: LLM 调用逻辑重复 ✅ FIXED

- **原始文件**：[ewa/api/lesson.py](ewa/api/lesson.py) 和 [ewa/api/ext.py](ewa/api/ext.py)
- **修复**：抽取 `ewa/llm/client.py` — `LLMClient` 类提供统一的 `chat()` 和 `chat_json()` 接口，内部优先级 Kimi → DeepSeek
- **影响范围**：`lesson.py` 的 `_try_llm()` 和 `ext.py` 的 `call_llm()` 均替换为 `LLMClient`
- **提交**：2026-07-08

### P1-2: lesson 模块表结构独立管理 ✅ FIXED

- **原始文件**：[ewa/demo/store.py](ewa/demo/store.py)
- **问题**：`lesson_sessions` 和 `lesson_attempts` 表不在 `docs/schema.sql` 中，裸 `except Exception: pass` 吞错误
- **修复**：
  1. 将两张 lesson 表（含索引）加入 [docs/schema.sql](docs/schema.sql)，由 `SiteRepository.initialize()` 统一创建
  2. `_ensure_lesson_tables()` 保留为运行时兜底，但异常处理改为分类型（`sqlite3.OperationalError` → warning，其他 → exception log）
  3. `LessonStore` 方法中的异常处理同样改为分类型
- **提交**：2026-07-08

### P1-3: Chrome 插件 API 地址硬编码 ✅ FIXED

- **原始文件**：[extension/content_script.js:14](extension/content_script.js#L14)
- **问题**：`const API_BASE = "http://localhost:8000"` 写死
- **修复**：改为 `let API_BASE`，新增 `resolveApiBase()` 函数，初始化时通过 `chrome.runtime.sendMessage({ type: "GET_API_BASE" })` 从 background.js 的 chrome.storage 读取配置。失败时 fallback 到默认值
- **提交**：2026-07-08

### P1-4: 前后端数据重复维护 ✅ FIXED

- **原始文件**：[frontend/src/data/siteProfile.ts](frontend/src/data/siteProfile.ts) (~500行) 和 [ewa/site/repository.py](ewa/site/repository.py) `_seed()` (~400行)
- **修复**：
  1. 创建 [scripts/generate_fallback.py](scripts/generate_fallback.py) — 从后端 API 生成 `frontend/public/fallback.json`
  2. 更新 [frontend/lib/site.ts](frontend/lib/site.ts) — `getSite()` 三层降级：后端 API → `fallback.json` → 硬编码 `siteProfile.ts`
  3. 运行 `python scripts/generate_fallback.py` 即可从后端 seed 数据重新生成前端降级文件
- **提交**：2026-07-08

### P1-5: lesson 与 site 模块通过环境变量隐式耦合 ✅ FIXED

- **原始文件**：[ewa/demo/store.py](ewa/demo/store.py) 和 [ewa/core/app.py](ewa/core/app.py)
- **问题**：lesson 模块通过 `os.getenv("EWA_SITE_DB_PATH")` 获取数据库路径
- **修复**：
  1. `demo/store.py` 新增 `set_db_path(db_path)` 函数，支持显式注入
  2. `core/app.py` 的 lifespan 中调用 `set_db_path(db_path)` 显式注入
  3. `_get_db_path()` 优先级：`set_db_path()` > `EWA_SITE_DB_PATH` env > config 默认值
- **提交**：2026-07-08

### P1-6: 无请求限流 ✅ FIXED

- **原始文件**：所有 API 端点
- **修复**：在 [ewa/core/middleware.py](ewa/core/middleware.py) 中实现 `RateLimiter` 类和 `create_rate_limit_middleware()` 函数
  - 一般 API 端点：60 次/分钟
  - LLM 调用端点 (`quiz_submit`, `ext/chat`)：20 次/分钟
  - 通过 `EWA_RATE_LIMIT=0` 环境变量可禁用
  - 超出限制返回 429 + `retry_after_sec`
- **提交**：2026-07-08

---

## P2 — 改进建议（待处理）

### P2-1: content_script.js 单体巨型文件

- **文件**：[extension/content_script.js](extension/content_script.js)
- **问题**：820+ 行单文件包含 UI 构建、状态管理、API 调用、事件处理、渲染逻辑
- **建议**：拆分为 modules/（api.js, ui.js, state.js, render.js），用 bundler 打包

### P2-2: 数据库迁移策略缺失

- **文件**：[docs/schema.sql](docs/schema.sql)
- **问题**：只有 `CREATE TABLE IF NOT EXISTS`，无版本化管理
- **建议**：引入 Alembic 或 sqlite3 迁移脚本目录

### P2-3: 内存缓存不可扩展

- **文件**：[ewa/demo/subtitle.py](ewa/demo/subtitle.py)
- **问题**：`_video_cache` 和 `_subtitle_cache` 是模块级字典，多 worker 不共享，重启丢失
- **建议**：使用 Redis 或 SQLite 缓存

### P2-4: Session ID 非加密安全

- **文件**：[extension/content_script.js](extension/content_script.js)
- **问题**：`Math.random().toString(36)` 生成 session ID
- **建议**：使用 `crypto.randomUUID()`

### P2-5: 前端 ISR 配置在静态导出中无效

- **文件**：[frontend/lib/site.ts](frontend/lib/site.ts)
- **问题**：`next: { revalidate: 60 }` 在 `output: 'export'` 模式下无效
- **建议**：静态导出场景下移除无效配置

---

## 附录：重构后模块结构

```
ewa/
├── core/              [正式框架] app 工厂 + CORS + 限流中间件 + SPA 服务
├── llm/               [正式框架] LLMClient 统一 LLM 客户端
├── site/              [正式框架] 博主站点（Repository → Service → API）
├── api/               [路由层]  薄路由（lesson.py, ext.py）→ 委托 demo/
├── demo/              [DEMO]    scoring / store / feedback / faq / subtitle
└── production/        [正式框架] auth / analytics / lesson / extension 接口存根
```
