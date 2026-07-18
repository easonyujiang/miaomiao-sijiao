# 前端重构计划：社区/博客分离 + 视频分支 + 语音清理

## 前置操作：Git 备份

```bash
git add -A && git commit -m "backup: pre-refactor snapshot" && git push origin master
```

## Context

用户要求三项改动：
1. **社区和博客完全拆开** — 社区是统一的独立页面，博客做成个人主页风格有机融合
2. **题目是视频的branch** — 社区帖子要关联到视频，按视频分组展示
3. **删掉语音系统** — 语音系统暂不完善，全部删除相关代码，后续重做

**重要约束：**
- 保留所有 AI 宣传文案（妙喵🐱、端点验证描述、日记页提示等）不删
- 只调整页面结构/区块组合，不改动现有前端样式（CSS class、动画、组件外观全部保留）

当前状态：EWA 已部署在 8.130.190.169:8000，服务正常运行，MC 服务器不受影响。

---

## Part 1: 删除语音系统

删除所有语音相关代码，包括组件、Context、命令系统和 UI 提示文案。

### 删除文件
- `context/voice-context.tsx` — VoiceProvider + Web Speech API
- `lib/voice-commands.ts` — 语音命令定义和匹配
- `components/voice/voice-indicator.tsx` — 左下角浮动麦克风按钮
- `components/voice/voice-help-panel.tsx` — 语音命令帮助面板

### 修改文件（仅移除语音相关代码，保留所有样式）
- **`components/app-wrapper.tsx`** — 移除 VoiceProvider/VoiceIndicator/VoiceHelpPanel，变成简单的 children 包装或直接删除
- **`components/community/content-feed.tsx`** — 移除 `useVoice`/`buildContentCommands` 导入、语音命令注册 `useEffect`、蓝色语音提示 banner
- **`components/community/content-detail.tsx`** — 移除返回按钮中的 `（或说「返回」）` 文案、底部语音控制提示文案
- **`components/community/comment-section.tsx`** — 移除 `useVoice`/`buildCommentCommands` 导入和语音命令注册 `useEffect`、收起按钮中的 `（或说「返回」）` 文案
- **`components/community/content-card.tsx`** — 移除 `（或说「打开」）` 文案

---

## Part 2: 社区帖子关联视频（视频分支）

### 3.1 数据库迁移
在服务器上执行 SQL：
```sql
ALTER TABLE community_topics ADD COLUMN video_id TEXT REFERENCES videos(id);
```

### 3.2 后端修改
- **`ewa/community/api.py`** — `list_topics()` 支持 `video_id` 查询参数过滤
- **`ewa/admin/api.py`** — topic CRUD 支持 `video_id` 字段

### 3.3 前端修改
- **`lib/community-data.ts`** — `ContentItem` 类型添加 `videoId?: string`
- **`lib/community-api.ts`** — `fetchTopics()` 添加 `videoId` 参数；`topicToContentItem()` 映射 `video_id`
- **`components/community/content-feed.tsx`** — 添加「按视频」筛选标签（从 videos 列表获取），显示视频关联 badge
- **`components/community/content-card.tsx`** — 当 topic 有关联视频时显示视频缩略图/标题 badge

---

## Part 3: 首页结构调整

仅调整首页区块的顺序和组合，不改动任何组件样式。

当前首页结构：Hero → 最近在做什么(diary) → Selected work → Recent writing(blog)

调整为：Hero → 最近在写(blog) → 在做的项目(diary) → 社区动态(新增,从API获取最新3-5条) → 全部文章链接

### 修改文件
- **`app/page.tsx`** — 调整区块顺序，在项目之后添加「社区动态」区块（从 `/api/community/topics?limit=5` 获取最新话题卡片，链接到 /community）

---

## Part 4: 构建部署

1. 本地提交 + 推送到 GitHub
2. 服务器 git pull
3. 数据库迁移（ALTER TABLE community_topics ADD COLUMN video_id TEXT）
4. 重新构建前端 `npm run build`
5. 重启 miaomiao.service
6. 验证所有页面

---

## 验证方案

1. 首页加载正常，无 JS 错误
2. `/community` 页面正常，帖子可按视频筛选
3. `/blog` 页面正常
4. 所有语音相关 UI 元素已消失（无左下角麦克风、无语音提示 banner、无"说xxx"文案）
5. AI 宣传文案保留完整（妙喵🐱、端点验证描述等）
6. 浏览器 Console 无报错
