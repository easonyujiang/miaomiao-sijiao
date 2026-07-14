# 妙喵私教 · 多视频/多博主/模块化审计报告

> 审计日期：2026-07-14 | 三份并行审计

---

## 一、Critical（阻断级，5 处）

### C1 · 全部 API 路由依赖 `ewa.demo.*`

"demo" 模块是唯一实现，"production/" 目录只有抽象接口，零运行时引用。所有路由直接导入 demo 模块。

- `ewa/api/lesson.py:23-25` — `from ewa.demo.scoring import score_answer_with_llm`
- `ewa/api/ext.py:24-29` — `from ewa.demo.faq import match_offline_faq`
- `ewa/core/app.py:27` — `from ewa.demo.store import set_db_path`

**修复**：重命名 `demo/` → `lesson/`，更新全部 import。

### C2 · 种子数据 100% 硬编码为 `profile_ashley`

`_seed()` 方法 ~400 行，全部 INSERTS 写死 `'profile_ashley'`。多博主不可添加。

- `ewa/site/repository.py:56-399`

**修复**：提取 `SeedProfile` 数据类，`_seed()` 接受 profile 参数。

### C3 · 前端硬编码 `ashley` slug

- `frontend/lib/site.ts:9` — `${origin}/api/site/ashley`
- `frontend/src/lib/api.ts:33,37,42,46,61` — 全部 5 个函数默认 `slug='ashley'`
- `frontend/app/diary/page.tsx:9` — 元数据硬编码"钟笑咪"
- `frontend/app/resume/page.tsx:5` — 元数据硬编码"钟笑咪"
- `frontend/src/data/siteProfile.ts` — 400 行 Ashley 静态数据副本

**修复**：slug 从环境变量/路由参数获取，移除默认值。

### C4 · `lesson_luoxiang_001` 硬编码为兜底课程

任何不匹配的视频都被错误分配此课程。

- `ewa/api/lesson.py:84`

**修复**：返回空课程 + 前端友好提示，不再静默分配错误课程。

### C5 · 种子数据包含 macOS 用户绝对路径

`/Users/ashley/Documents/...` 在 4 处 INSERT 中。

- `ewa/site/repository.py:199-224`

**修复**：改为相对路径或可配置的 `EWA_ASSETS_DIR`。

---

## 二、High（9 处）

| # | 问题 | 位置 |
|---|------|------|
| H1 | `lesson_sessions` / `lesson_attempts` 表无 `profile_id` 列 | `docs/schema.sql` |
| H2 | 视频接口无 profile 范围控制 | `ewa/site/api.py` |
| H3 | 扩展 API 无 profile 感知 | `ewa/api/ext.py` |
| H4 | Lesson JSON 无 `profile_id` 字段 | `data/miaomiao/lessons/` |
| H5 | `core/app.py` 耦合 `ewa.site` 和 `ewa.demo.store` | `ewa/core/app.py:26-27` |
| H6 | 限流中间件硬编码端点路径 | `ewa/core/middleware.py:137` |
| H7 | LLM provider 硬编码；OPENAI/ANTHROPIC key 配置但未用 | `ewa/llm/client.py:42-55` |
| H8 | 前端 400 行静态数据副本 | `frontend/src/data/siteProfile.ts` |
| H9 | `service.py` 硬编码产品描述文本 | `ewa/site/service.py:118-122` |

---

## 三、Medium（8 处）

| # | 问题 | 位置 |
|---|------|------|
| M1 | 两个独立 DB 访问层通过环境变量侧信道共享 SQLite | `ewa/site/repository.py` vs `ewa/demo/store.py` |
| M2 | 四种错误处理风格混用 | 全项目 |
| M3 | 两个健康检查端点 `/health` + `/api/ext/health` | `ewa/core/app.py`, `ewa/api/ext.py` |
| M4 | `production/` 模块零运行时引用 | `ewa/production/` |
| M5 | `ewa/api/` 和 `ewa/site/api.py` 模糊的模块边界 | |
| M6 | Lesson JSON 无 `domain` 字段，评分始终用"通用" | `data/` |
| M7 | 仅 1 个字幕文件、1 个课程文件 | `data/miaomiao/` |
| M8 | `demo/__init__.py` 无 re-exports | |

---

## 四、Low（4 处）

| # | 问题 | 位置 |
|---|------|------|
| L1 | 项目根目录计算 `parents[2]` 脆弱 | `ewa/core/app.py:65`, `ewa/config.py:14` |
| L2 | 无 API 版本化前缀 | 全部路由 |
| L3 | `KIMI_API_KEY` 回退未使用 | `ewa/config.py:37` |
| L4 | 配置导入风格不一致 | `ewa/demo/store.py:18` |
