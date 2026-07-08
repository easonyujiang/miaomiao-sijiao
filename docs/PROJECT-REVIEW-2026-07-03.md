# 妙喵私教（EWA）项目流水线与进度审查报告

**审查日期**：2026-07-03
**审查范围**：全栈代码库（后端 / 前端网站 / Chrome Extension 后端 / Schema）
**项目阶段**：端点验证完成 → 比赛 DEMO 冲刺
**定位**：抖音创变者大赛 · 赛道二：内容重构——让视频成为你的生活搭子

---

## 目录

1. [产品定位与愿景](#一产品定位与愿景)
2. [项目全景图谱](#二项目全景图谱)
3. [各模块完成度评估](#三各模块完成度评估)
4. [关键问题清单](#四关键问题清单)
5. [架构亮点](#五架构亮点)
6. [面向比赛 DEMO 的路线图](#六面向比赛-demo-的路线图)
7. [技术债务台账](#七技术债务台账)
8. [附录：完整文件清单](#八附录完整文件清单)

---

## 一、产品定位与愿景

### 赛题对应

| 赛道要求 | 妙喵实现 |
|----------|----------|
| 优质信息转化 | 视频 → ASR 字幕 → 时间轴 + 知识点 + 练习题 |
| 可学习 | 妙喵追问学习状态，AI 判卷，指出具体错误 |
| 可直接应用 | 一键回到对应片段，完成真实练习 |
| 游戏化和趣味性 | 猫咪宠物人格、6 种状态动画、星级/小鱼干/毛线团 |
| 生活搭子 | 博主个人色彩、学习进度记忆、长期陪伴 |

### 产品形态（两种模式）

```
┌─────────────────────────────────────────────────────────────────┐
│  Mode A: 博主互动站 (端点验证 ✅)                                  │
│  Lee Robinson 风格个人网站 → 展示项目/日记/视频/FAQ                  │
│  右下角 🐱 妙喵对话窗 → FAQ 问答 + 视频跳转                          │
│  用途: 验证"宠物 Agent + 博主数据"架构可行性                         │
├─────────────────────────────────────────────────────────────────┤
│  Mode B: 妙喵私教 Chrome Extension (比赛 DEMO 🎯)                  │
│  Chrome 插件注入 B站/抖音视频页 → 🐱 气泡悬浮播放器旁                │
│  点击"开始学习" → 5 关法学案例练习                                   │
│  AI 出题 → 用户作答 → 判卷评分 → 纠错 + 播放器自动跳转               │
│  用途: 比赛 3 分钟演示——把教学视频变成一对一私教                      │
└─────────────────────────────────────────────────────────────────┘
```

### DEMO 演示脚本（3 分钟）

> 场景：用户在 B站观看罗翔讲解"正当防卫"（BV1mJ4m147PG），妙喵插件自动介入。

| 时间 | 镜头 | 内容 |
|------|------|------|
| 0:00 | 痛点 | "教学视频播放完了，你真的学会了吗？" |
| 0:30 | 气泡出现 | 打开 B站视频，右下角出现 🐱 气泡，点击展开 |
| 1:00 | 出题作答 | 妙喵出题："张三持刀追赶李四，李四跑进死胡同后回身捅了张三，构成正当防卫吗？" |
| 1:30 | AI 判卷 | 妙喵："你答对了主观要件，但漏了'不法侵害正在进行'的时间节点。→ **跳到 03:42**" |
| 2:00 | 重新作答 | 补充回答后通过，展示第一次 vs 第二次答题对比 + 星级 |
| 2:30 | 收束 | "过去粉丝只能看视频；现在，视频里的知识可以练习、被纠错、被记住。" |

### 目标运行流程

```bash
# 1. 启动后端
cd ~/黑客松/ewa
source .venv/bin/activate
python run.py

# 2. Chrome 加载插件
# 目录: ~/Downloads/抖音创变AI_妙喵私教/miaomiao/extension/

# 3. 打开视频
# B站 BV1mJ4m147PG → 妙喵气泡自动出现 → 点击"开始学习" → 进入 5 关练习
```

---

## 二、项目全景图谱

```
┌──────────────────────────────────────────────────────────────────┐
│              Layer 0: 前端表现层                                    │
│                                                                   │
│  Mode A (✅ 完成): Next.js 15 个人网站                              │
│  app/ → Home / Blog / Projects / Diary / Resume                    │
│  components/ → PetAssistant SiteHeader ProjectVideo DiaryCard      │
│                                                                   │
│  Mode B (❌ 缺失): Chrome Extension MV3                            │
│  extension/ 目录不存在于当前代码库                                  │
│  需新建: content_script / popup / background / manifest.json        │
├──────────────────────────────────────────────────────────────────┤
│              Layer 1: API 网关 (FastAPI)                            │
│                                                                   │
│  Mode A 端点 (✅): /api/site/* 博主网站数据                         │
│  Mode B 端点 (⚠️): /api/ext/* 插件视频注册/问答                     │
│                  /api/lesson/* 课程加载/答题评分/步骤推进            │
├──────────────────────────────────────────────────────────────────┤
│              Layer 2: EWA 核心引擎                                  │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐   │
│  │ Agents           │  │ Harness          │  │ MCP              │   │
│  │ RouterAgent ✅   │  │ Rules ✅         │  │ McpServer ✅     │   │
│  │ BaseAgent ✅     │  │ HookRegistry ✅  │  │ McpClient ✅     │   │
│  │ @skill ✅        │  │ Blueprint ⚠️     │  │                  │   │
│  │ 6 Agent 实现 ❌  │  │                  │  │                  │   │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘   │
├──────────────────────────────────────────────────────────────────┤
│              Layer 3: 模型层                                        │
│  DeepSeek / Kimi (ext.py 实际使用) │ OpenAI / Anthropic (已封装)    │
│  Ollama qwen2.5:7b (路由决策)      │ edge-tts (语音合成，未实现)    │
├──────────────────────────────────────────────────────────────────┤
│              Layer 4: 数据层                                        │
│  SQLite (data/miaomiao.db) │ Lesson JSON │ 字幕 JSON               │
│  Schema 17 张表完备 │ 种子数据真实                                   │
└──────────────────────────────────────────────────────────────────┘
```

### 两条数据流（当前实际状态）

```
┌─ Flow A: 博主互动站 (✅ 完整) ─────────────────────────────────┐
│  Next.js 网站 → Site API → SQLite → FAQ 匹配                    │
│  右下角 🐱 → 问答 + 视频跳转                                     │
│  离线回退: API 不可用时用本地 siteProfile.ts 数据                │
└────────────────────────────────────────────────────────────────┘

┌─ Flow B: 妙喵私教插件 (⚠️ 链路有断点) ─────────────────────────┐
│  Chrome Extension (缺失) → /api/ext/register_video              │
│                          → /api/ext/chat (字幕上下文 LLM 问答)   │
│                          → /api/lesson/load (加载 Lesson JSON)  │
│                          → /api/lesson/quiz_submit (判卷评分)   │
│                          → /api/lesson/next_step (步骤推进)     │
│                                                                  │
│  ✅ 后端 API 全部就绪                                            │
│  ❌ Chrome Extension 前端代码不存在                              │
│  ❌ Lesson JSON 数据依赖于开发者本机 (~/Downloads/...)           │
│  ⚠️ 评分是关键词匹配算法，未接 LLM                               │
│  ⚠️ 学习状态存内存 dict，重启丢失                                │
└────────────────────────────────────────────────────────────────┘
```

---

## 三、各模块完成度评估

### ✅ 已完成 / 可运行（80%~100%）

| 模块 | 完成度 | 说明 |
|------|--------|------|
| **前端网站 (Mode A)** | 90% | 5 个页面 + Layout + SEO + MDX + 浮动猫咪 |
| **Site API** | 85% | 博主数据 / 视频 / 日记 / 会话 / 事件 |
| **SiteRepository + Seed** | 90% | 12 项目 / 9 FAQ / 6 日记 / 2 视频 / 7 知识源 |
| **数据 Schema** | 95% | 17 张表 + 完整索引 + 外键 + CHECK |
| **ext API (插件视频问答)** | 60% | 视频注册 + B站字幕匹配 + Kimi/DeepSeek LLM |
| **lesson API (课程评分)** | 55% | Lesson 加载 + 答题评分 + 步骤推进 + 游戏化 |
| **RouterAgent** | 95% | 输入分类 + 策略选择 + 模型路由 + 关键词回退 |
| **BaseAgent** | 90% | LLM 调用 + 缓存 + 成本追踪 + JSON 模式 |
| **@skill / SkillResult** | 95% | 工具注册 + MCP + 计时 + 结构化返回 |
| **ModelRouter** | 90% | 本地/云端/混合三种路由策略 |
| **MCP Server + Client** | 90% | JSON-RPC 2.0 + SSE |
| **KnowledgeBase + GitOps** | 85% | Git 版本 + 向量索引 + CRUD |
| **集成测试** | 60% | test_site_api.py 覆盖 Mode A 全链路 |

### 🔶 部分完成（40%~75%）

| 模块 | 完成度 | 缺失内容 |
|------|--------|----------|
| **Lesson 评分算法** | 65% | 关键词 + 子串匹配可用，但未接 LLM 做语义判断 |
| **ext API 字幕匹配** | 55% | 可用但依赖开发者本机字幕 JSON 库 |
| **Harness Blueprint** | 40% | 编排逻辑完整，但 `_agents` 字典为空 |
| **EmbeddingStore** | 70% | sqlite-vec 可用，但 embedding API 硬编码 localhost |

### ❌ 未开始 / 缺失（0%~20%）

| 模块 | 说明 |
|------|------|
| **Chrome Extension 前端** | `~/Downloads/.../extension/` 目录不存在于当前代码库 |
| **Lesson JSON 数据** | 罗翔刑法视频的 Lesson 数据（5 关练习）需编写 |
| **B站字幕 JSON** | BV1mJ4m147PG 的 ASR 字幕需准备 |
| **vision_agent** | 视频/图片理解 Agent |
| **document_agent** | 文档解析 Agent |
| **step_agent** | 步骤生成 Agent |
| **guide_agent** | 操作引导 Agent |
| **edge-tts 猫咪语音** | 项目介绍中列为 P1，未实现 |
| **无网络演示模式** | 项目介绍中列为 P0，预分析数据未打包 |
| **前端流式输出** | Chat 与 PetAssistant 均为等待完整响应 |
| **前端 Dockerfile** | 不存在 |

---

## 四、关键问题清单

### 🔴 P0 — 阻塞比赛 DEMO

#### P0-1: Chrome Extension 代码缺失

**期望路径**：`~/Downloads/抖音创变AI_妙喵私教/miaomiao/extension/`

当前代码库中**没有任何 Chrome Extension 代码**。`api/ext.py` 的端点已就绪，但调用这些端点的 content_script / popup / background 代码均不存在。

必须新建：
- `manifest.json` (MV3)
- `content_script.js` — 注入 B站/抖音视频页，检测视频 ID，显示 🐱 气泡
- `popup.html` / `popup.js` — 对话界面（或直接内嵌在 content_script 中）
- `background.js` — 跨页面消息传递

#### P0-2: Lesson JSON 数据缺失

**期望路径**：`~/Downloads/抖音创变AI_妙喵私教/miaomiao/data/lessons/`

`api/lesson.py` 加载的课程数据（BV1mJ4m147PG 罗翔刑法的 5 关练习）不存在于当前代码库。每条 Lesson JSON 包含：
- 步骤（steps）：title / start_ms / end_ms / instruction / key_point / quiz(question, answer_key, wrong_key)
- 游戏化配置（gamification）：fish_reward_per_step / growth_per_pass

**这个数据是 DEMO 的核心**——没有它，`/api/lesson/quiz_submit` 无法判卷。

#### P0-3: B站字幕 JSON 缺失

**期望路径**：`~/Downloads/抖音创变AI_妙喵私教/miaomiao/data/subtitles/`

`api/ext.py` 需要 `{bvid}.json` 字幕文件来做视频问答的时间戳上下文定位。需要：
- `BV1mJ4m147PG.json` — 罗翔刑法视频的 ASR 字幕

#### P0-4: 硬编码路径阻塞跨环境运行

**位置**：[api/ext.py:23-27](../ewa/api/ext.py#L23-L27) + [api/lesson.py:21](../ewa/api/lesson.py#L21)

```python
MIAOMIAO_DIR = Path.home() / "Downloads/抖音创变AI_妙喵私教/miaomiao"
LESSONS_DIR = Path.home() / "Downloads/抖音创变AI_妙喵私教/miaomiao/data/lessons"
```

当前是 macOS 路径，Windows 下 `Path.home()` 返回 `C:\Users\...`，整个路径不同。

#### P0-5: Lesson 评分状态不持久化

**位置**：[api/lesson.py:24](../ewa/api/lesson.py#L24)

```python
_session_state: dict[str, dict] = {}  # demo 用，生产换 SQLite
```

DEMO 演示中如果后端重启，学习进度全部丢失。Schema 中已有 `visitor_sessions` / `conversation_messages` 表可直接使用。

### 🟡 P1 — 影响体验但不阻塞基础流程

#### P1-1: Lesson 评分是关键词匹配，非 LLM 语义判断

**位置**：[api/lesson.py:65-113](../ewa/api/lesson.py#L65-L113)

当前 `score_answer()` 用关键词 + 子串匹配评分。对于法学案例分析，这可能漏判语义正确但措辞不同的回答。项目介绍明确说"确定性算法 + 置信度"，当前实现方向正确但需验证准确率。

#### P1-2: EWA Agent 引擎与产品代码未整合

后端有完整的 Agent/Harness/MCP 框架代码，但实际产品 API（ext.py、lesson.py）完全没用到它们。`POST /chat` 的 Blueprint 链路不通。

#### P1-3: 项目介绍中提到的技术栈与代码不一致

| 项目介绍 | 当前代码 |
|----------|----------|
| FAISS 向量检索 | sqlite-vec |
| MediaCrawler 数据采集 | 无 |
| Whisper / faster-whisper | 无（ext.py 使用的是预处理的字幕 JSON） |
| edge-tts 语音合成 | 无 |
| DeepSeek / Kimi LLM | ext.py 中已接入 Kimi + DeepSeek |

### 🟢 P2 — 长期优化

- 无 `.env.example`
- 无 CI/CD
- Agent/Router/MCP/Blueprint 无单元测试
- 无 LLM 可观测性（Langfuse / OpenTelemetry）

---

## 五、架构亮点

### 1. "端点验证 → 最终产品"的正确演进路径

```
Phase 1: 个人网站端点验证 ✅
  → 验证数据结构、API 设计、宠物 persona、离线回退

Phase 2: Chrome Extension 比赛 DEMO 🎯
  → 验证视频注入、字幕关联、答题评分、播放器控制

Phase 3: 平台化
  → 多博主、多平台、自动视频流水线
```

### 2. 猫咪状态机设计

项目介绍定义的 6 种状态直接映射到 [api/lesson.py `_calc_cat_state()`](../ewa/api/lesson.py#L336-L345)：

| 状态 | 触发条件 | 代码对应 |
|------|----------|----------|
| idle | 等待中 | 初始状态 |
| watching | 引导观看片段 | lesson_step 推进 |
| analyzing | 正在判卷 | quiz_submit 返回前 |
| correcting | 答错，纠错中 | `cat_message` 指出错误 |
| celebrating | 通过检查 | passed=True 时的反馈 |
| listening | 接收录音 | P1 功能（语音输入） |

### 3. 评分算法设计

[api/lesson.py `score_answer()`](../ewa/api/lesson.py#L65-L113) 的评分逻辑：
1. 从 answer_key 提取词语（跳过括号内补充说明）
2. 任意词命中 OR 3 字公共子串匹配即算通过
3. wrong_key 命中扣分 ×0.5
4. 主判断 = 匹配数 >= min_correct 且 无错误

这是确定性算法的合理实现，不依赖 LLM 打分。

### 4. ext.py 的多 LLM 回退链

```python
# ext.py call_llm()
Kimi (moonshot-v1-8k) → DeepSeek (deepseek-chat) → 本地回退
```

每个环节都有 try/except，任一成功即返回。这种容错设计适合 DEMO 场景。

### 5. 离线容错

前端 `PetAssistant` API 不可用时降级到本地 FAQ 匹配；`getSite()` API 不可用时返回静态 `siteProfile`。

---

## 六、面向比赛 DEMO 的路线图

### 目标定义

> **DEMO 交付物**：
> 1. 后端服务运行在 `localhost:8000`
> 2. Chrome Extension 加载后，打开 B站 BV1mJ4m147PG
> 3. 视频右下角自动出现 🐱 气泡
> 4. 点击"开始学习"→ 进入 5 关法学案例练习
> 5. 每关：看片段 → 答题 → AI 判卷 → 纠错 + 播放器跳转 → 下一关
> 6. 全部通过后展示星级/小鱼干/成长值

### Phase 1: 数据准备（Day 1，6-8h）

> 最重要的一步——没有数据，所有代码都跑不起来

#### 任务 1.1: 编写罗翔刑法 Lesson JSON（3h）

**新文件**：`data/miaomiao/lessons/lesson_luoxiang_001.json`

为 BV1mJ4m147PG（罗翔讲正当防卫）编写 5 关练习：

```json
{
  "id": "lesson_luoxiang_001",
  "title": "正当防卫的构成要件 — 罗翔刑法",
  "video_id": "BV1mJ4m147PG",
  "platform": "bilibili",
  "creator_name": "罗翔说刑法",
  "pass_threshold": 0.75,
  "gamification": {
    "fish_reward_per_step": 3,
    "growth_per_pass": 10,
    "perfect_bonus": 5
  },
  "steps": [
    {
      "id": "step_1",
      "title": "正当防卫的起因条件",
      "start_ms": 60000, "end_ms": 120000,
      "instruction": "观看这段视频，理解正当防卫的第一个要件：必须存在不法侵害。",
      "key_point": "不法侵害是正当防卫的起因条件，没有不法侵害就没有正当防卫。",
      "common_errors": ["假想防卫不构成正当防卫", "对合法行为不能正当防卫"],
      "quiz": {
        "question": "张三在街上看到李四拿着刀走向自己，张三先发制人将李四打伤。事后发现李四的刀是道具。张三的行为是否构成正当防卫？请说明理由。",
        "answer_key": ["不构成正当防卫", "不存在不法侵害", "假想防卫", "没有现实的不法侵害"],
        "wrong_key": ["构成正当防卫", "先发制人"],
        "min_correct": 2,
        "hint_seek_ms": 90000
      },
      "pass_threshold": 0.75
    }
    // ... 共 5 关
  ]
}
```

#### 任务 1.2: 准备 B站字幕 JSON（1h）

**新文件**：`data/miaomiao/subtitles/BV1mJ4m147PG.json`

```json
{
  "bvid": "BV1mJ4m147PG",
  "title": "罗翔：正当防卫的构成要件",
  "subtitles": [
    {"start": 0, "end": 5, "text": "今天我们来讲解正当防卫..."},
    {"start": 5, "end": 12, "text": "..."}
  ]
}
```

> 获取方式：使用 B站 API 下载字幕，或通过 Whisper 转写。

#### 任务 1.3: 数据目录迁移到项目内（1h）

将 Lesson JSON 和字幕 JSON 从 `~/Downloads/...` 迁移到 `e:\Create\Code\ewa\data\miaomiao\`，确保 `git clone` 后即可用。

#### 任务 1.4: 修复路径配置（1h）

**新建** `ewa/config.py`，将 [ext.py](../ewa/api/ext.py) 和 [lesson.py](../ewa/api/lesson.py) 的硬编码路径替换为环境变量 + 项目相对路径默认值。

---

### Phase 2: Chrome Extension 开发（Day 2-4，16-20h）

#### 任务 2.1: Extension 项目骨架（2h）

**新建目录**：`extension/`

```
extension/
├── manifest.json           # MV3 配置
├── content_script.js       # 注入视频页，显示气泡
├── content_style.css       # 气泡 + 对话框样式
├── background.js           # Service Worker
├── popup/
│   ├── popup.html          # 插件弹窗（可选）
│   └── popup.js
├── assets/
│   └── cat-idle.png        # 猫咪图标
└── README.md               # 加载说明
```

**manifest.json**：
```json
{
  "manifest_version": 3,
  "name": "妙喵私教",
  "version": "0.1.0",
  "description": "把教学视频变成一对一私教",
  "permissions": ["activeTab", "storage"],
  "host_permissions": [
    "*://*.bilibili.com/*",
    "*://*.douyin.com/*"
  ],
  "content_scripts": [{
    "matches": ["*://*.bilibili.com/video/*", "*://*.douyin.com/video/*"],
    "js": ["content_script.js"],
    "css": ["content_style.css"]
  }],
  "background": {
    "service_worker": "background.js"
  },
  "web_accessible_resources": [{
    "resources": ["assets/*"],
    "matches": ["*://*.bilibili.com/*", "*://*.douyin.com/*"]
  }],
  "icons": {
    "128": "assets/cat-idle.png"
  }
}
```

#### 任务 2.2: content_script — 视频检测 + 气泡注入（6h）

核心逻辑：
1. 检测当前页面是否为视频页
2. 从 URL 提取视频 ID（B站 BVid / 抖音 video_id）
3. 调用 `POST /api/ext/register_video` 注册视频 + 匹配字幕
4. 在播放器右下角注入 🐱 气泡按钮
5. 气泡反应：
   - 无匹配课程 → "妙喵还不认识这个视频，喵~"
   - 有课程未开始 → "🐱 开始学习" 按钮
   - 学习中 → 显示当前进度
   - 已完成 → 显示星级总结

#### 任务 2.3: content_script — 对话 + 答题界面（6h）

点击气泡展开面板：
1. **引导区**：显示当前关卡的 instruction，自动 seek 到 start_ms
2. **答题区**：显示 quiz.question，textarea 作答
3. **结果区**：调用 `POST /api/lesson/quiz_submit`
   - 通过：显示 cat_message + 星星动画 + "下一关" 按钮
   - 未通过：显示纠错 + "[SEEK:秒数]" 自动跳转按钮
4. **完成区**：5 关全部通过，展示 total_stars / fish / growth / review_queue

#### 任务 2.4: 播放器控制（2h）

通过 content_script 操作 B站/抖音播放器：
- `player.seek(seconds)` — 跳转到指定时间
- 高亮当前片段区间
- 监听 `player.currentTime` 更新气泡状态

#### 任务 2.5: 猫咪表情状态机（2h）

6 种表情切换：
- idle → watching（开始学习）
- watching → listening（出题等待作答）
- listening → analyzing（提交答案）
- analyzing → correcting（答错）
- analyzing → celebrating（答对）
- celebrating → idle（进入下一关）或 全部完成

---

### Phase 3: 后端打磨（Day 4-5，8-12h）

#### 任务 3.1: Lesson 评分升级（3h）

在关键词匹配基础上，添加 LLM 语义判断作为第二层：
1. 关键词匹配 ≥ min_correct → 直接通过
2. 关键词匹配 < min_correct → 调用 DeepSeek/Kimi 做语义判断
3. 保留确定性算法的优先级

#### 任务 3.2: 评分状态持久化（2h）

**修改** [api/lesson.py](../ewa/api/lesson.py)：
- `_session_state: dict` → `SiteRepository` / SQLite
- 复用 `visitor_sessions` 表
- 答题历史写入 `conversation_messages`
- 步骤推进写入 `visitor_events`

#### 任务 3.3: ext API 离线模式（1h）

在 ext.py 中添加离线判断：如果 LLM API 全部不可用，返回预设的 FAQ 风格回答（类似 PetAssistant 的离线回退）。

#### 任务 3.4: 配置统一 + .env.example（1h）

**新建** `.env.example`：
```bash
# LLM API Keys
MOONSHOT_API_KEY=sk-...      # 妙喵私教首选
DEEPSEEK_API_KEY=sk-...      # 回退
OPENAI_API_KEY=sk-...        # 可选

# 数据路径
EWA_DATA_DIR=./data
MIAOMIAO_DATA_DIR=./data/miaomiao

# 服务器
EWA_HOST=0.0.0.0
EWA_PORT=8000
```

---

### Phase 4: DEMO 联调与打磨（Day 5-6，8-12h）

#### 任务 4.1: 端到端联调（3h）

1. 启动后端 → 加载 Extension → 打开 BV1mJ4m147PG
2. 验证气泡自动出现
3. 走通完整 5 关流程
4. 验证播放器跳转
5. 验证全部通过后的总结

#### 任务 4.2: 比赛演示脚本预演（2h）

按 3 分钟演示脚本走 5 遍，确保每个环节节奏可控：
- 0:00-0:30 痛点引入（10 秒备选视频片段）
- 0:30-1:00 气泡出现 + 开始学习
- 1:00-1:30 第 1 关答题（故意答错一半）
- 1:30-2:00 纠错 + 播放器跳转 + 重新作答
- 2:00-2:30 通过 + 完成全部 5 关（加速展示）
- 2:30-3:00 收束 + 架构扩展性说明

#### 任务 4.3: 异常处理兜底（2h）

- [ ] 后端未启动 → Extension 气泡显示"后端未连接"
- [ ] LLM API 全部超时 → 回退到关键词评分
- [ ] 字幕文件缺失 → 使用 Lesson JSON 中的文本代替
- [ ] 视频不在 B站/抖音 → Extension 不注入

#### 任务 4.4: 赛后迭代规划（2h）

| 优先级 | 任务 | 说明 |
|--------|------|------|
| P0 | 语音输入 (listening 状态) | edge-tts 猫咪音色 |
| P0 | 无网络演示模式 | 预分析数据打包，离线全功能 |
| P1 | 抖音平台支持 | content_script 适配抖音视频页 |
| P1 | 视频自动分析流水线 | 上传 → Whisper → 场景切分 → Lesson JSON |
| P1 | 多博主支持 | profile 切换 + 宠物 persona 定制 |
| P2 | 数据仪表板 | 学习统计、答题分析 |

---

## 七、技术债务台账

| ID | 位置 | 描述 | 严重度 | 工时 |
|----|------|------|--------|------|
| D-01 | **缺失** | Chrome Extension 代码不存在 | 🔴 P0 | 16h |
| D-02 | **缺失** | Lesson JSON 数据（5 关练习）不存在 | 🔴 P0 | 3h |
| D-03 | **缺失** | B站字幕 JSON 不存在 | 🔴 P0 | 1h |
| D-04 | [ext.py:23](../ewa/api/ext.py#L23) | 硬编码 macOS 路径 | 🔴 P0 | 1h |
| D-05 | [lesson.py:24](../ewa/api/lesson.py#L24) | 学习状态存内存 dict | 🔴 P0 | 2h |
| D-06 | [lesson.py:65](../ewa/api/lesson.py#L65) | 评分纯关键词匹配，无语义判断 | 🟡 P1 | 3h |
| D-07 | [main.py:158](../ewa/api/main.py#L158) | EWA Chat API 非 rag_query 返回占位 | 🟡 P1 | 4h |
| D-08 | 缺失 | edge-tts 语音合成（项目介绍中 P1） | 🟡 P1 | 4h |
| D-09 | 缺失 | 无网络演示模式（项目介绍中 P0） | 🟡 P1 | 4h |
| D-10 | 缺失 | 无 `.env.example` | 🟢 P2 | 0.5h |
| D-11 | 缺失 | 无 CI/CD | 🟢 P2 | 4h |

---

## 八、附录：完整文件清单

```
项目根目录 (e:\Create\Code\ewa)
├── README.md                 # 中文 README
├── 项目介绍(1).html           # 比赛产品介绍页面（完整视觉设计）
├── 猫教.docx                  # 产品文档（Word 格式，二进制）
├── pyproject.toml             # Python 项目配置
├── Dockerfile                 # 后端镜像
├── docker-compose.yml         # 三服务编排（缺前端 Dockerfile）
├── run.py                     # 启动入口
├── .gitignore
│
├── ewa/                       # 后端 Python 包
│   ├── agents/                # Agent 框架
│   │   ├── base.py            # BaseAgent + AgentCache
│   │   ├── router.py          # RouterAgent + RoutingDecision
│   │   ├── skill.py           # @skill 装饰器
│   │   └── result.py          # SkillResult
│   ├── harness/               # 编排引擎
│   │   ├── rules.py           # Rules
│   │   ├── hooks.py           # HookRegistry
│   │   └── blueprint.py       # Blueprint
│   ├── mcp/                   # MCP 协议
│   │   ├── server.py          # JSON-RPC 2.0 Server
│   │   └── client.py          # MCP Client
│   ├── models/                # 模型封装
│   │   ├── local.py           # OllamaModel
│   │   ├── cloud.py           # CloudModel (OpenAI/Anthropic)
│   │   └── router.py          # ModelRouter
│   ├── rag/                   # 知识库
│   │   ├── knowledge_base.py  # Git + 向量 + 领域管理
│   │   ├── git_ops.py         # Git 操作
│   │   └── embeddings.py      # sqlite-vec 向量存储
│   ├── api/                   # HTTP API
│   │   ├── main.py            # FastAPI 主应用 + Mode A 端点
│   │   ├── ext.py             # 插件 API (视频注册/字幕/LLM问答)
│   │   └── lesson.py          # 私教 API (课程/答题/评分/游戏化)
│   └── site/                  # 博主站点业务逻辑
│       ├── repository.py      # Repository + 种子数据
│       ├── service.py         # Service 层
│       └── api.py             # 站点 API Router
│
├── frontend/                  # Mode A: 博主个人网站 (Next.js)
│   ├── app/                   # 页面路由 (Home/Blog/Projects/Diary/Resume)
│   ├── components/            # PetAssistant, SiteHeader, ProjectVideo...
│   ├── lib/                   # getSite(), posts(), utils()
│   └── src/                   # API 客户端, 静态数据, MDX 文章
│
├── extension/                 # Mode B: Chrome Extension (❌ 待新建)
│
├── docs/
│   ├── PROJECT-REVIEW-2026-07-03.md  # 本报告
│   └── personal-site-schema.sql      # 数据库 Schema (17 表)
│
├── tests/
│   └── test_site_api.py       # 集成测试 (Mode A 全链路)
│
└── data/                      # 运行时数据 (❌ 部分缺失)
    └── miaomiao/
        ├── lessons/           # Lesson JSON (❌ 待编写)
        ├── subtitles/         # 字幕 JSON (❌ 待准备)
        ├── scored_videos.json # B站视频评分索引
        └── video_list.json    # 视频列表
```

---

## 九、审查结论

### 当前状态

| 维度 | 状态 | 说明 |
|------|------|------|
| Mode A (博主网站) | ✅ 90% | 可独立演示，5 个页面 + 猫咪对话 |
| Mode B 后端 API | ✅ 75% | ext + lesson 端点全部就绪 |
| Mode B Extension 前端 | ❌ 0% | 代码不存在，需从零搭建 |
| Mode B 数据 | ❌ 20% | Lesson JSON + 字幕 JSON 均缺失 |
| EWA Agent 引擎 | ⚠️ 50% | 框架完整，Agent 实现为空壳 |

### DEMO 可行性

按 Phase 1-4 执行，**5-6 个工作日**可完成比赛 DEMO：

```
Day 1:    数据准备 (Lesson JSON + 字幕 JSON + 路径配置)
Day 2-3:  Chrome Extension content_script (气泡 + 对话 + 答题)
Day 4:    Extension 播放器控制 + 状态机 + 联调
Day 5:    后端打磨 (评分升级 + 持久化 + 离线模式)
Day 6:    全链路联调 + 3 分钟演示脚本预演
```

### 风险提示

1. **B站 BV1mJ4m147PG** — 需确认视频可访问、内容确实讲正当防卫、时长适合 5 关切分
2. **字幕获取** — B站 API 可能限流或需要登录态，建议提前下载好字幕文件
3. **播放器控制** — B站播放器 API 可能随版本变化，需实测验证 `player.seek()` 可用
4. **Extension 审核** — 比赛演示可加载未打包的扩展（开发者模式），无需商店审核

---

> **审查人**：Claude Code
> **参考文档**：README.md / 项目介绍(1).html / 猫教.docx / 全量源码
> **下次审查建议时间**：Phase 2 Extension 骨架完成后
