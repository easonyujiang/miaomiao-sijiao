# Known Issues

已知问题清单。修复日期标注在对应条目后。

## 已修复 (2026-07-18)

### BUG-001: starlette/fastapi 版本不兼容
- **现象**: pytest 无法收集测试，`TypeError: Router.__init__() got an unexpected keyword argument 'on_startup'`
- **原因**: starlette 1.3.1 移除了 `on_startup` 参数，但 fastapi 0.115.0 仍使用它
- **修复**: 升级 fastapi 到 0.139.2，锁定 starlette>=1.0

### BUG-002: lesson_sessions FOREIGN KEY 约束失败
- **现象**: `sqlite3.IntegrityError: FOREIGN KEY constraint failed`，session/attempt 无法持久化
- **原因**: `lesson_sessions.profile_id` 引用 `profiles(id)`，但插件直接创建 session 不经过 profiles 表
- **修复**: 移除 `lesson_sessions` 对 `profiles` 的外键约束（schema.sql + store.py）

### BUG-003: schema.sql 语法错误
- **现象**: `sqlite3.OperationalError: near ")": syntax error`
- **原因**: 移除 FK 后遗留了尾逗号
- **修复**: 移除 `updated_at` 行尾逗号

### BUG-004: 测试断言与实际行为不匹配
- **现象**: 3 个测试用例失败（test_load_default_fallback, test_chat_offline_faq, test_unknown_lesson_falls_back）
- **原因**: 测试假设了不存在的降级行为，或假设 LLM 不可用（实际 DeepSeek 可用）
- **修复**: 更新测试断言匹配实际 API 行为

### BUG-005 (EXT): XSS via innerHTML — cat_message
- **现象**: `div.innerHTML = result.cat_message.replace(/\n/g, "<br>")` 直接注入服务端返回内容
- **文件**: `extension/content/bilibili.js:278`, `extension/content/douyin.js:310`
- **修复**: 改用 `textContent`

### BUG-006 (EXT): lesson load 真值判断错误
- **现象**: `if (lesson)` 在 API 返回 error 对象时仍为 truthy，导致渲染空课程
- **文件**: `extension/content/bilibili.js:545`
- **修复**: 改为 `if (lesson && lesson.lesson_id)`

### BUG-007 (EXT): quizTimer 定时器泄漏
- **现象**: `scheduleQuiz()` 每次调用只清除 `setTimeout`，但内部 `setInterval` 未清除
- **文件**: `extension/content/bilibili.js:211-221`
- **修复**: 添加 `quizCheckInterval` 变量跟踪并清除 interval

### BUG-008 (EXT): step 编号显示错误
- **现象**: `step.id.replace("step_0", "")` 无法正确提取编号
- **文件**: `extension/content/bilibili.js:204`
- **修复**: 改为 `step.id.replace("step_", "")`

### BUG-009 (EXT): ts.innerHTML XSS 风险
- **现象**: `ts.innerHTML` 拼接格式化时间字符串
- **文件**: `extension/content/bilibili.js:474`, `extension/content/douyin.js:310`
- **修复**: 改用 `textContent`

## 已知问题（低优先级，暂不修复）

### ISSUE-001: 硬编码通关消息
- **文件**: `extension/content/bilibili.js:306`
- **描述**: 全部通关时显示固定文案 "罗翔老师的正当防卫精讲你已掌握"，应改为动态课程标题
- **优先级**: 低 — 目前只有一门课，影响有限

### ISSUE-002: douyin.js 缺少课程学习模式
- **文件**: `extension/content/douyin.js`
- **描述**: 抖音脚本没有 lesson/quiz 学习流程，只有自由问答
- **优先级**: 低 — 抖音暂无课程数据

### ISSUE-003: extension localhost 硬编码
- **文件**: `extension/content/bilibili.js:7`, `extension/content/douyin.js:6`
- **描述**: `API_BASE` 硬编码为 `http://localhost:8000`，生产环境需改为可配置
- **优先级**: 中 — 云部署前需处理

### ISSUE-004: FastAPI/Starlette deprecation warnings
- **描述**: `HTTP_422_UNPROCESSABLE_ENTITY` deprecated，httpx testclient deprecated
- **优先级**: 低 — 不影响功能，后续升级时处理
