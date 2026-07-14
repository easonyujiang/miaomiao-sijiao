# 妙喵私教 · 用户反馈排查报告

> 排查日期：2026-07-13 | 版本：0.2.0 | 基于用户反馈的四项问题 + 一项 Bug

---

## 0. 🔴 Bug 排查：「第一个问题回答没有反应」

> 用户追加反馈：答题后界面卡在「猫猫正在认真判卷…」无响应。

### 0.1 根因分析

经过完整链路追踪（Chrome Extension → API → 评分引擎 → LLM → 返回），定位到 **3 个导致问题的连锁缺陷**：

---

#### 缺陷 A：API Key 为占位符，LLM 调用全部失败

- **文件**：[.env:2-7](.env#L2-L7)
- **问题**：所有 LLM API Key 都是 `sk-...` 占位符，不是真实密钥
  ```
  MOONSHOT_API_KEY=sk-...
  DEEPSEEK_API_KEY=sk-...
  ```
- **影响链路**：
  1. 用户提交答案 → `score_answer_with_llm()` 先做关键词匹配
  2. 如果关键词匹配**不达标**（用户答案没命中足够的 answer_key 词汇），触发 LLM 回退
  3. `_llm_judge()` → `LLMClient.chat_json()` → `_call()` 用假 key 调用 API
  4. API 返回 401 / 连接超时 → 返回 None → 用关键词结果兜底
- **关键代码**：[ewa/llm/client.py:72-73](ewa/llm/client.py#L72-L73)
  ```python
  api_key = self._kimi_key if provider["name"] == "kimi" else self._deepseek_key
  if not api_key:    # ← "sk-..." 是非空字符串，不会被跳过！
      continue
  ```
  假 key `sk-...` 长度 > 0，所以 `continue` 不会触发，LLM 调用被真实发起。

---

#### 缺陷 B：LLM HTTP 超时 20 秒/Provider，总计可达 40 秒

- **文件**：[ewa/llm/client.py:134](ewa/llm/client.py#L134)
- **问题**：`httpx.AsyncClient(timeout=20)` — 连接超时、读取超时、写入超时全部设为 20 秒
- **影响**：如果 Moonshot/DeepSeek API 不可达（DNS 解析慢、防火墙拦截、网络不通），每个 provider 最多等待 20 秒
- **链路**：Kimi 超时 20s → DeepSeek 超时 20s → **总计 40 秒无响应**
- **用户体感**：点击「提交答案」→ 界面显示「猫猫正在认真判卷…」→ 40 秒无变化 → 用户认为「没有反应」

```python
# 第 134 行 — timeout=20 覆盖 connect/read/write，未单独设 connect timeout
async with httpx.AsyncClient(timeout=timeout) as client:
    res = await client.post(api_url, ...)
```

---

#### 缺陷 C：评分 LLM System Prompt 绑定法学，与用户实际场景可能不匹配

- **文件**：[ewa/demo/scoring.py:156](ewa/demo/scoring.py#L156)
- **问题**：`_llm_judge()` 的 system prompt 硬编码 `"你是一名法学私教评分助手"`
- **影响**：即便 LLM 能连通，非法律课程也会被当作法律题评分，准确性差

---

### 0.2 触发场景

| 条件 | 结果 |
|------|------|
| 用户答案命中 ≥ 2 个关键词 | ✅ 秒过（纯关键词匹配，不调 LLM） |
| 用户答案命中 < 2 个关键词 | ❌ 触发 LLM 回退 → 假 key → 超时 40s |
| 用户答案短（< 10 字） | ❌ 前端拦截，显示提示但不提交 |

**所以「第一次就答对的人」可能完全遇不到 Bug，但「答案写得偏了/表达不同的用户」会卡死 40 秒。** 这解释了为什么问题不是必现的。

### 0.3 根因三连

```
前端提交答案
  ↓
score_answer_with_llm()
  ↓
关键词匹配不达标 (用户表达与 answer_key 差异大)
  ↓
触发 LLM 语义判断 _llm_judge()
  ↓
LLMClient 用假 key "sk-..." 调 Kimi API
  ↓ httpx timeout=20s 无响应
  ↓
LLMClient 用假 key "sk-..." 调 DeepSeek API
  ↓ httpx timeout=20s 无响应
  ↓
返回关键词匹配结果（可能 0 分）
  ↓
前端收到响应 → renderFailResult() 渲染
  ↓
⏱️ 用户已等了 40+ 秒，早就关面板了
```

### 0.4 修复方案

**立即修复（P0）：**

1. **LLM 调用加 connect timeout**：[ewa/llm/client.py](ewa/llm/client.py)
   ```python
   # 改为分别设置 connect/read/write timeout
   timeout_config = httpx.Timeout(connect=5.0, read=15.0, write=5.0, pool=5.0)
   async with httpx.AsyncClient(timeout=timeout_config) as client:
   ```

2. **API Key 有效性校验**：[ewa/llm/client.py](ewa/llm/client.py)
   ```python
   # 过滤明显无效的 key
   if not api_key or len(api_key) < 10 or api_key.startswith("sk-..."):
       continue
   ```

3. **评分引擎 quick-reject**：[ewa/demo/scoring.py](ewa/demo/scoring.py)
   ```python
   # 如果 LLM 不可用，直接返回关键词结果，不尝试 LLM
   # 在 score_answer_with_llm() 开头检查 LLMClient.is_available
   ```

**连带发现（P1）：**

4. **限流器完全失效**：[ewa/core/middleware.py:141](ewa/core/middleware.py#L141)
   ```python
   # BUG: 每次请求创建新的 RateLimiter 实例，_window 为空，永远不会限流
   limiter = RateLimiter(requests_per_minute=limit)  # ← 每次 new！
   if not limiter.is_allowed(key, now):
   ```
   全局 `rate_limiter`（第 106 行）从未被使用。应该改为复用全局实例。

5. **Session 持久化静默失败**：[ewa/demo/store.py:181-182](ewa/demo/store.py#L181-L182)
   ```python
   except sqlite3.OperationalError:
       pass  # ← 任何 DB 写入失败被完全吞掉
   ```

6. **用户答案输入提示不够明显**：[extension/content_script.js:460-462](extension/content_script.js#L460-L462)
   - 短答案 (<10 字) 只显示一行小字提示，用户容易错过
   - 建议：弹出 toast / 按钮变灰 + 数字统计

---

## 问题总览

| # | 问题 | 严重程度 | 类型 |
|---|------|---------|------|
| 1 | 不够灵活 | 🔴 架构级 | 架构设计 |
| 2 | 前端太丑 | 🟡 体验级 | UI/UX |
| 3 | 博主涩话缺失 | 🔴 产品核心 | 功能缺失 |
| 4 | 缺少共创社区 + 效果验证 | 🟠 功能缺失 | 功能缺失 |

---

## 1. 不够灵活

### 1.1 问题现状

整个系统围绕「钟笑咪 + 罗翔刑法课」这一个硬编码场景构建，换一个博主或领域就完全不可用。

### 1.2 具体发现

#### 后端评分系统绑定法学场景

- **文件**：[ewa/demo/scoring.py:156](ewa/demo/scoring.py#L156)
- **问题**：`_llm_judge()` 的 system prompt 硬编码为 **"你是一名法学私教评分助手"**
- **影响**：评分引擎只能用于法学领域，无法扩展到其他学科（编程、音乐、设计…）
- **现状代码**：
  ```python
  system = """你是一名法学私教评分助手。你的任务是判断学生的回答是否涵盖了参考答案中的要点。
  请严格按以下 JSON 格式返回，不要加任何其他文字：..."""
  ```

#### 离线 FAQ 知识库硬编码

- **文件**：[ewa/demo/faq.py:8](ewa/demo/faq.py#L8)
- **问题**：`OFFLINE_FAQ` 只有 6 条硬编码的刑法条目（正当防卫、假想防卫、防卫过当、特殊防卫、互殴、挑拨防卫）
- **影响**：离线模式只对法学课程有效，其他视频完全无法回答

#### 猫咪反馈消息模板硬编码

- **文件**：[ewa/demo/feedback.py:9-44](ewa/demo/feedback.py#L9-L44)
- **问题**：`build_cat_message()` 中所有消息模板硬编码，无法按博主风格定制
- **现状代码**：
  ```python
  def build_cat_message(passed, matched, missed, wrong_hits, attempt_num, step_title, key_point):
      if passed:
          if attempt_num == 1:
              return f"完美！第一次就答对了 🌟\n核心要点你都掌握了：..."
  ```

#### 课程数据单一路径

- **文件**：[ewa/api/lesson.py:32](ewa/api/lesson.py#L32)
- **问题**：`load_lesson()` 只从本地 JSON 文件加载，无数据库存储、无多课程管理
- **影响**：目前只有一份课程 `lesson_luoxiang_001.json`，无法扩展课程库

#### 前端数据全部硬编码

- **文件**：[frontend/src/data/siteProfile.ts](frontend/src/data/siteProfile.ts)
- **问题**：**500+ 行**硬编码数据——项目、FAQ、视频、日记、链接全部写死在 TypeScript 文件中
- **影响**：换一个博主需要改源码并重新构建部署

#### 字幕匹配靠字符集交集

- **文件**：[ewa/demo/subtitle.py:48-79](ewa/demo/subtitle.py#L48-L79)
- **问题**：视频匹配算法是简单的字符集交集算分（`len(title_chars & v_chars)`），无向量检索或语义匹配
- **影响**：标题稍微不同就匹配不到，准确率低

#### 数据库已有表但未使用

- **文件**：[docs/schema.sql:162-172](docs/schema.sql#L162-L172)
- **问题**：`creator_style_examples` 表定义了 6 种风格示例类型（开场白/解释/幽默/过渡/结尾/边界），但代码中完全没用
- **影响**：数据结构已经考虑到灵活性，但业务代码没跟上

### 1.3 改进方向

1. **评分引擎可配置化**：system prompt 从课程 JSON 中读取，每个课程自带领域设定
2. **FAQ 知识库数据库化**：从 SQLite 读取，而非硬编码 dict
3. **反馈消息模板化**：消息模板从 `pet_personas.style_rules_json` 读取
4. **课程管理系统**：支持上传/编辑/管理多门课程
5. **前端数据 API 化**：完全从后端 API 获取（目前已支持但 fallback 太重）
6. **字幕检索升级**：使用 embedding 向量做语义匹配

---

## 2. 前端有点太丑了

### 2.1 问题现状

前端基本就是 Next.js 默认模板 + Tailwind 最小配置，视觉设计投入几乎为零。

### 2.2 具体发现

#### 色彩系统缺失

- **文件**：[frontend/app/globals.css](frontend/app/globals.css)
- **问题**：
  - 全站只有 neutral 灰色系（`--background: 0 0% 98%` 等）
  - 没有任何品牌色、强调色、辅助色
  - 橙色 `#f59e0b` 只在 Chrome 插件中出现，前端完全没有

#### Dark Mode 只有空壳

- **文件**：[frontend/tailwind.config.ts:4](frontend/tailwind.config.ts#L4) + [frontend/app/globals.css](frontend/app/globals.css)
- **问题**：`tailwind.config.ts` 配了 `darkMode: ['class']`，但 CSS 中只有 `:root` 变量，没有 `.dark` 对应的变量
- **影响**：切换 dark mode 不会有任何效果

#### 布局单调

- **文件**：[frontend/app/layout.tsx:17](frontend/app/layout.tsx#L17)
- **问题**：经典单列居中博客模板，`max-w-3xl` 限制宽度，全站一个布局走到底
- **影响**：首页、日记、项目、博客全部是同一个文字列表风格

#### 猫咪助手 UI 简陋

- **文件**：[frontend/components/pet-assistant.tsx:78](frontend/components/pet-assistant.tsx#L78)
- **问题**：
  - 用 emoji 🐱 代替品牌形象，没有自定义 SVG/动画
  - 聊天窗气泡是纯灰白配色，无个性
  - 快捷问题按钮是最基础的 pill 样式
- **对比**：Chrome 插件的猫咪气泡反而更好看（有渐变色、弹跳动画、emoji 表情变化）

#### Tailwind 配置极简

- **文件**：[frontend/tailwind.config.ts](frontend/tailwind.config.ts)
- **问题**：只扩展了 4 个颜色 token（border/background/foreground/primary/muted），无字体、间距、动画等自定义

#### 缺少视觉元素

- 没有品牌 logo（只有文字 "钟笑咪"）
- 没有插画/装饰元素
- 没有过渡动画（除了 BlurFade）
- 卡片没有 hover 效果（除了 project 卡片有一个简单的 hover:border）
- 首页头像是一个纯色圆角 div 里放字母 "ZXM"

### 2.3 改进方向

1. **建立色彩系统**：基于猫咪/品牌主色调（暖橙色系）+ 辅助色 + 语义色
2. **实现 Dark Mode**：补全 `.dark` CSS 变量，支持系统主题跟随
3. **猫咪形象升级**：设计 SVG 猫咪组件，支持表情/状态切换动画
4. **丰富视觉层次**：渐变背景、卡片阴影、装饰元素、微交互动效
5. **页面差异化**：首页 hero、日记时间线、项目卡片网格——每个页面应有自己的视觉特征
6. **响应式优化**：目前只有基础的 Tailwind 响应式，需要针对移动端优化

---

## 3. 交互博主的涩话没有加上

### 3.1 问题现状

这是**产品最核心的缺失**。README 明确说目标是「为每位视频博主生成一个有个人色彩的宠物 Agent」，但实际代码中完全没有注入博主个人风格。

### 3.2 具体发现

#### 聊天系统完全不用 LLM 生成回复

- **文件**：[ewa/site/service.py:67-122](ewa/site/service.py#L67-L122)
- **问题**：`chat()` 方法完全基于 FAQ 关键词匹配 + 硬编码模板返回，**从未调用 LLM 来生成带博主风格的回复**
- **流程**：用户消息 → 关键词匹配 FAQ → 直接返回预定义的 `faq["answer"]` 文本
- **影响**：所有回答都是预先写死的，毫无「对话感」和「个人色彩」

#### 博主人设已定义但未注入

- **文件**：[frontend/src/data/siteProfile.ts:130-135](frontend/src/data/siteProfile.ts#L130-L135)
- **已定义的风格规则**（但代码中完全未使用）：
  ```typescript
  pet: {
    traits: ['有博主个人色彩', '先回答再带路', '能定位视频片段', '不冒充本人', '只使用有依据资料', '记得主人最近在做什么'],
    styleBasis: '直接、重视实际复用、用具体场景解释抽象想法、相信记忆要握在自己手里。',
  }
  ```

#### 数据库已有风格表但未使用

- **文件**：[docs/schema.sql:162-172](docs/schema.sql#L162-L172)
- **问题**：`creator_style_examples` 表已定义（6 种类型：opening/explanation/humor/transition/closing/boundary），但代码中完全没有读写这张表
- **影响**：连数据基础设施都做好了，就是业务代码没接上

#### 评分反馈无个性

- **文件**：[ewa/demo/feedback.py](ewa/demo/feedback.py)
- **问题**：`build_cat_message()` 生成的消息是官方模板风格，无博主语气：
  - `"完美！第一次就答对了 🌟"`
  - `"猫猫看了你的答案，差一点点~"`
- **缺失的钟笑咪风格**：
  - 口头禅：「记忆要握在自己手里」
  - 语气：直接、不绕弯子、偶尔自嘲
  - 梗：宋知秋、Emerge甬现、《献书》、Cline 记忆中枢

#### Chrome 插件猫咪消息同样无个性

- **文件**：[extension/content_script.js:503-506](extension/content_script.js#L503-L506)
- **问题**：`CAT_EMOJI` 和 `CAT_LABEL` 是固定的 6 种状态表情，没有和博主关联
- **现状**：
  ```javascript
  const CAT_EMOJI = { idle: "🐱", watching: "🐱💭", listening: "🐱👂", analyzing: "🐱🔍", correcting: "🐱📝", celebrating: "🐱🎉" };
  ```

#### LLM 聊天端点有基础设施但未被 chat 流程使用

- **文件**：[ewa/api/ext.py](ewa/api/ext.py)
- **现状**：视频时间戳问答端点 (`POST /api/ext/chat`) 已经接了 LLM，但博主网站的 chat 端点 (`POST /api/site/{slug}/chat`) 仍然只用关键词匹配

### 3.3 钟笑咪可提取的人设要素

从日记和 profile 中可以提取出以下可用于 system prompt 的个性化要素：

| 维度 | 内容 |
|------|------|
| **口头禅** | "记忆要握在自己手里" |
| **风格** | 直接、实干、不绕弯子、用具体场景解释抽象想法 |
| **身份标签** | AI 应用开发者 · 校园创业者 · 黑客松组织者 |
| **个人梗** | 宋知秋（梦中少女）、《献书》（东晋游戏）、Emerge甬现（高校社群）、Cline 记忆中枢 |
| **态度** | 相信代码和文字是同一件事——把转瞬即逝的瞬间留下来 |
| **习惯** | 写日记、跨平台记忆同步、GitHub 私有仓库 |
| **边界** | 不冒充本人、只使用有依据的资料 |

### 3.4 改进方向

1. **LLM 聊天接入博主风格**：`chat()` 方法改为调用 LLM，system prompt 注入博主 `styleBasis` + `traits` + `creator_style_examples`
2. **风格示例库建设**：使用 `creator_style_examples` 表收集博主在不同场景下的真实表达
3. **反馈消息个性化**：`build_cat_message()` 支持从配置/数据库读取个性化的消息模板
4. **猫咪表情联动**：根据博主设定的宠物性格调整猫咪表情和语气
5. **Chrome 插件接入**：插件的 `CAT_EMOJI`/`CAT_LABEL`/`cat_message` 从后端拉取博主个性化配置

---

## 4. 缺少共创社区 + 话题效果验证

### 4.1 问题现状

目前项目中**完全没有社区功能**。现有交互模型是单向的：

```
访客 → 聊天(FAQ 关键词匹配) → 预设回答
学生 → 答题(关键词+LLM 评分) → 猫咪反馈
```

没有用户间交流、没有 UGC、没有反馈闭环。

### 4.2 现有数据基础设施

schema.sql 有 17 张表，但全部围绕**博主个人数据管理**：

| 表 | 用途 | 是否社区相关 |
|----|------|:--:|
| profiles | 博主信息 | ❌ |
| pet_personas | 宠物人设 | ❌ |
| projects | 博主项目 | ❌ |
| faqs | FAQ 问答对 | ❌ |
| profile_links | 博主链接 | ❌ |
| knowledge_sources | 知识来源 | ❌ |
| videos | 博主视频 | ❌ |
| video_segments | 视频片段 | ❌ |
| video_relations | 视频关系 | ❌ |
| creator_style_examples | 风格示例 | ❌ |
| content_chunks | 内容块 | ❌ |
| visitors | 匿名访客 | ⚠️ 有基础但仅追踪 |
| visitor_sessions | 访客会话 | ⚠️ 有基础但仅追踪 |
| viewer_video_progress | 观看进度 | ⚠️ 个人数据 |
| conversation_messages | 对话记录 | ⚠️ 个人数据 |
| visitor_events | 访客事件 | ⚠️ 有基础但仅追踪 |
| visitor_memories | 访客记忆 | ⚠️ 个人数据 |

没有以下社区相关表：
- 话题/帖子（topics/posts）
- 评论/回复（comments/replies）
- 点赞/收藏（likes/bookmarks）
- 用户关注（follows）
- 反馈/评分（feedback/ratings）
- 课程评价（lesson_reviews）

### 4.3 「话题点效果验证」完全空白

目前**没有任何反馈闭环**来验证回答质量：

| 应该验证的 | 当前状态 |
|-----------|---------|
| FAQ 回答是否帮到用户？ | ❌ 无收集 |
| 课程关卡设计是否合理？ | ❌ 只存 attempt，不存满意度 |
| LLM 评分是否准确？ | ❌ 无人工校验通道 |
| 猫咪回答是否符合博主风格？ | ❌ 无法衡量 |
| 视频片段定位是否准确？ | ❌ 无反馈 |
| 社区话题是否解决了用户问题？ | ❌ 无此功能 |

### 4.4 改进方向

#### 短期：效果验证闭环

1. **回答反馈按钮**：每条猫咪回答后加 👍/👎 + 可选原因
2. **答题满意度**：每关完成后加「这个题目有帮助吗？」
3. **评分申诉**：用户觉得 LLM 判错了可以点「申诉」，进入人工复核队列
4. **匿名统计面板**：博主端展示 FAQ 命中率、用户满意度趋势

#### 中期：共创社区

1. **话题系统**：
   - 用户可以发起话题（围绕视频/课程/博主内容）
   - 其他用户可以回复讨论
   - 猫咪可以参与话题（基于博主知识库生成回答）

2. **课程共创**：
   - 用户可以为视频创建/完善课程关卡
   - 众包标注：标记视频中的知识点、常见误区
   - 审核机制：博主或社区管理员审核后上线

3. **用户体系**：
   - 从匿名访客升级为注册用户
   - 个人主页：学习记录、贡献的课程、社区参与
   - 积分/等级：激励高质量贡献

4. **交流功能**：
   - 评论区（视频下、课程下、话题下）
   - 私信（用户间、用户与猫咪）
   - @提及通知

#### 数据库扩展建议

```sql
-- 社区话题
CREATE TABLE community_topics (
    id TEXT PRIMARY KEY,
    author_visitor_id TEXT NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    category TEXT NOT NULL,  -- question / discussion / showcase / feedback
    related_video_id TEXT,
    related_lesson_id TEXT,
    tags_json TEXT NOT NULL DEFAULT '[]',
    view_count INTEGER NOT NULL DEFAULT 0,
    reply_count INTEGER NOT NULL DEFAULT 0,
    like_count INTEGER NOT NULL DEFAULT 0,
    is_pinned INTEGER NOT NULL DEFAULT 0,
    is_resolved INTEGER NOT NULL DEFAULT 0,  -- 问题是否已解决
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (author_visitor_id) REFERENCES visitors(id),
    FOREIGN KEY (related_video_id) REFERENCES videos(id)
);

-- 话题回复
CREATE TABLE community_replies (
    id TEXT PRIMARY KEY,
    topic_id TEXT NOT NULL,
    author_visitor_id TEXT NOT NULL,
    parent_reply_id TEXT,  -- 支持嵌套回复
    content TEXT NOT NULL,
    is_pet_reply INTEGER NOT NULL DEFAULT 0,  -- 是否为猫咪自动回复
    like_count INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (topic_id) REFERENCES community_topics(id) ON DELETE CASCADE,
    FOREIGN KEY (author_visitor_id) REFERENCES visitors(id),
    FOREIGN KEY (parent_reply_id) REFERENCES community_replies(id)
);

-- 效果反馈
CREATE TABLE answer_feedback (
    id TEXT PRIMARY KEY,
    message_id TEXT NOT NULL,  -- 关联到 conversation_messages
    visitor_id TEXT NOT NULL,
    rating TEXT NOT NULL CHECK (rating IN ('helpful', 'not_helpful', 'inaccurate', 'off_topic')),
    comment TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (message_id) REFERENCES conversation_messages(id),
    FOREIGN KEY (visitor_id) REFERENCES visitors(id)
);

-- 答题满意度
CREATE TABLE quiz_feedback (
    id TEXT PRIMARY KEY,
    attempt_id INTEGER NOT NULL,
    session_id TEXT NOT NULL,
    rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
    comment TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (attempt_id) REFERENCES lesson_attempts(id),
    FOREIGN KEY (session_id) REFERENCES lesson_sessions(id)
);
```

---

## 总结：优先级排序

| 优先级 | 问题 | 理由 |
|:--:|------|------|
| **P0** | 🔴 答题无响应 | LLM 超时 40s 阻断核心功能，必须立即修 |
| **P0** | 博主涩话缺失 | 这是产品的核心差异化——"有博主个人色彩的宠物 Agent"。没有这个，产品和其他 AI 聊天没区别 |
| **P0** | 不够灵活（评分/FAQ/课程） | 不做通用化就无法扩展到其他博主，产品愿景落不了地 |
| **P1** | 话题效果验证 | 没有反馈闭环就无法迭代优化，也无法向博主证明价值 |
| **P1** | 前端太丑 | 用户第一印象差，但可以后期迭代（产品价值验证优先） |
| **P2** | 共创社区 | 需要前四项有一定基础后再建设，否则社区没有内容可交流 |

---

## 附录 A：Bug 修复清单

| # | 文件 | 行号 | 问题 | 修复 |
|---|------|------|------|------|
| 1 | [ewa/llm/client.py](ewa/llm/client.py) | 120-134 | LLM 超时笼统设为 20s，无细分 connect timeout | 改用 `httpx.Timeout(connect=5, read=15, write=5)` |
| 2 | [ewa/llm/client.py](ewa/llm/client.py) | 72-73 | 假 key `sk-...` 未被过滤 | 加最小长度校验 `len(api_key) >= 10` |
| 3 | [ewa/core/middleware.py](ewa/core/middleware.py) | 141 | 每次请求 new RateLimiter，限流完全失效 | 复用全局 `rate_limiter` 实例 |
| 4 | [ewa/demo/store.py](ewa/demo/store.py) | 181-182 | `except OperationalError: pass` 静默吞异常 | 至少加 warning log |
| 5 | [ewa/demo/scoring.py](ewa/demo/scoring.py) | 156 | System prompt 硬编码法学 | 从课程 JSON 读取领域设定 |
| 6 | [extension/content_script.js](extension/content_script.js) | 460 | 短答案提示不明显 | 改为 toast 或按钮禁用 + 字数统计 |

## 附录 B：当前模块与问题对应关系

```
ewa/
├── ewa/demo/scoring.py       ← Bug0(LLM超时) + 问题1(法学硬编码) + 问题3(无风格)
├── ewa/demo/feedback.py      ← 问题3（消息模板无个性）
├── ewa/demo/faq.py           ← 问题1（知识库硬编码）
├── ewa/demo/store.py         ← Bug0(静默吞异常)
├── ewa/llm/client.py         ← Bug0(超时+假key过滤)
├── ewa/core/middleware.py    ← Bug0(限流器失效)
├── ewa/site/service.py       ← 问题3（chat 不用 LLM）
├── ewa/api/lesson.py         ← 问题1（课程数据单一路径）
├── extension/content_script.js ← Bug0(短答案提示) + 问题3(猫咪消息无风格)
├── frontend/app/globals.css  ← 问题2（色彩/主题缺失）
├── frontend/components/      ← 问题2（UI 简陋）
├── frontend/src/data/        ← 问题1（数据硬编码）
└── docs/schema.sql           ← 问题4（缺少社区表）
```
