# 妙喵私教功能实现计划

> 目标：实现网站妙喵的视频模糊查询 + 插件端学习分析报告
> 决策：用户已确认本方案

---

## 一、网站妙喵：收录视频模糊查询

### 目标
用户在网站端（妙喵宠物助手）可以输入：
- "BV1mJ4m147PG 讲了什么"
- "罗翔正当防卫那期讲了什么"

妙喵在已收录视频里模糊匹配，总结内容，并给出可跳转的链接/动作。

### 实现路径

1. **数据层**（`server/ewa/website/repository.py`）
   - 新增 `search_videos(profile_id, keyword, limit=5)`：
     - 精确匹配 `video_id`（BV 号/抖音号）
     - 子串匹配 `title`
     - 简单相似度兜底（`difflib.SequenceMatcher`）
   - 新增 `get_video_segments(video_id)`：读取 `video_segments` 表
   - 新增 `get_subtitle_text(video_id)`：优先读取 `data/miaomiao/subtitles/{video_id}.json`，fallback 到 `video_segments`

2. **服务层**（`server/ewa/website/service.py`）
   - 在 `chat()` 中新增 `video_query` 意图分支：
     - 检测用户消息中是否含 BV 号、抖音号、"讲了什么"、"关于" 等关键词
     - 调用 `search_videos` 获取候选视频
     - 读取字幕/片段，用 `LLMClient` 生成摘要
     - 返回 `answer` + `actions`（`seek_video`）
   - 保持现有 FAQ 和 Diary 分支优先，video_query 作为 fallback 或显式意图

3. **API 层**（`server/ewa/website/api.py`）
   - `POST /api/site/{slug}/chat` 已支持 `video_id` 和 `current_time_ms` 字段
   - 确保前端传入这两个字段

4. **前端层**（`server/frontend/components/pet-assistant.tsx`）
   - 发送 `chatWithPet` 时，如果当前页面 URL 包含 `?video=...&t=...`，解析并传入 `video_id` 和 `current_time_ms`
   - `runAction()` 已支持 `seek_video` 跳转 `/projects?video=...&t=...`

### 响应示例
```json
{
  "answer": "这期视频主要讲正当防卫的五个构成要件：起因、时间、对象、主观、限度...",
  "intent": "video_query",
  "actions": [
    {"type": "seek_video", "video_id": "BV1mJ4m147PG", "time_ms": 0, "label": "▶ 跳转到视频"}
  ]
}
```

---

## 二、插件端：学习分析报告

### 目标
课程全部通关后，自动以妙喵对话形式弹出学习分析报告，包含：
- 完成度和总奖励
- 薄弱知识点
- 推荐回看片段
- LLM 生成的个性化指导

### 实现路径

1. **数据层**（`server/ewa/extension/store.py`）
   - 新增 `load_attempts(session_id)`：按 `step_id` 和 `attempt_num` 排序读取 `lesson_attempts`

2. **API 层**（`server/ewa/extension/lesson_api.py`）
   - 新增 `GET /api/lesson/report/{session_id}/{lesson_id}`：
     - 读取 session 和 attempts
     - 汇总统计
     - 用 `LLMClient` 生成指导语
     - 返回结构化报告

3. **服务层**（可在 `lesson_api.py` 内或新建 `reporting.py`）
   - 汇总数据：
     - total_stars, fish, growth
     - completed_steps, total_steps
     - 每步尝试次数、通过状态
     - 错误点/漏答点聚合
     - review_queue 中的步骤
   - LLM prompt：根据错题和薄弱点写鼓励+复习建议

4. **前端层**（`extension/content/bilibili.js`）
   - 在 `submitAndShow()` 中检测 `result.passed && !result.next_step`
   - 自动调用 `fetchLessonReport(session_id, lesson_id)`
   - 用 `appendMessage` 或 `appendCatReport` 在消息区渲染报告卡片

5. **样式**（`extension/content/style.css`）
   - 新增 `.mm-report-card` 样式：突出显示、分段、可点击时间戳

### 报告示例
```
🎉 全部通关！
⭐ 总星数：12 / 15
🐟 小鱼干：+15

📊 薄弱点：起因条件、时间条件

💡 妙喵建议：
你容易把「假想防卫」和「事后防卫」混淆。建议回跳 0:30 和 1:30 再看两遍。

⏪ 推荐回看：
- 起因条件：0:30
- 时间条件：1:30
```

---

## 三、文件改动清单

| 功能 | 文件 | 改动类型 |
|------|------|----------|
| 视频查询 | `server/ewa/website/repository.py` | 新增查询方法 |
| 视频查询 | `server/ewa/website/service.py` | 新增 video_query 分支 |
| 视频查询 | `server/frontend/components/pet-assistant.tsx` | 传入 video_id/current_time_ms |
| 视频查询 | `server/frontend/src/lib/api.ts` | 确认请求类型 |
| 学习报告 | `server/ewa/extension/store.py` | 新增 load_attempts |
| 学习报告 | `server/ewa/extension/lesson_api.py` | 新增报告端点 |
| 学习报告 | `extension/content/bilibili.js` | 自动触发 + 渲染报告 |
| 学习报告 | `extension/content/style.css` | 报告样式 |
| 通用 | `docs/` | 更新说明文档 |

---

## 四、验收标准

1. 网站妙喵输入「BV1mJ4m147PG 讲了什么」能返回内容摘要并跳转视频
2. 输入不存在的视频标题时返回友好提示
3. 插件完成课程最后一关后自动弹出学习报告
4. 报告包含薄弱点、推荐回看时间戳、LLM 指导语
5. 所有改动部署后前端能正常构建、后端无报错
