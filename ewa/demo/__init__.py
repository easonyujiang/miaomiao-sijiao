"""妙喵私教 — DEMO 模块

当前演示阶段使用的具体实现：
- scoring: 关键词 + LLM 混合评分引擎
- store: SQLite 学习状态持久化
- feedback: 猫咪反馈消息生成
- faq: 离线 FAQ 知识库
- subtitle: 字幕加载、缓存、搜索与视频匹配

这些模块在 DEMO 阶段被 api/lesson.py 和 api/ext.py 引用。
生产阶段将被 production/ 下的对应实现替换。
"""
