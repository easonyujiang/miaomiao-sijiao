# 妙喵私教 · 现存问题

> 2026-07-14

## 架构

- `ewa/api/` 仅为兼容入口层，路由分散在 `website/`、`extension/`、`admin/`、`community/` 四个模块
- 两个独立 DB 访问层（`website/repository.py` + `extension/store.py`）通过环境变量侧信道共享同一个 SQLite 文件
- 项目根目录计算使用 `Path(__file__).resolve().parents[2]`，目录结构变更会断裂
- 无 API 版本化前缀

## 数据

- `video_segments`、`video_relations`、`conversation_messages`、`visitor_events`、`agent_actions` 等表无 `profile_id` 列
- Lesson JSON 无 `domain` 字段，评分始终使用默认值「通用」
- `data/miaomiao/subtitles/` 仅一个字幕文件，无 profile 关联
- `extension/store.py` 的 DDL 与 `docs/schema.sql` 重复定义

## 前端

- `frontend/src/data/siteProfile.ts` 为 400 行静态数据副本，与种子数据重复
- `frontend/lib/site.ts` 的 `getSite()` 仍有 fallback 到静态数据的路径

## 错误处理

- 四种错误处理风格混用：bare except-pass / HTTPException / 200-with-error-dict / logged exception
- `ewa/llm/client.py:181` `except Exception: pass` 静默吞掉所有网络错误

## 认证

- 仅管理后台有 Token 认证
- 网站 API、插件 API、社区 API 全部公开无鉴权
- 社区 API 的 `author_name` 字段无验证，可任意伪造

## 视频管理

- 视频导入需要手动在 Admin SPA 中逐字段填写，无 URL 抓取/自动解析
- 扩展的 `register_video` 使用内存缓存，重启丢失
- 字幕匹配为简单字符集交集，无向量检索
