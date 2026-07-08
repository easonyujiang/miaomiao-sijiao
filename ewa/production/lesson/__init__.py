"""Lesson 框架 — 课程领域抽象接口。

DEMO 阶段使用关键词 + LLM 混合评分和 SQLite 存储。
生产阶段通过此模块接入专业评分引擎和分布式存储。
"""

from ewa.production.lesson.interfaces import (
    LessonRepository,
    ScoringEngine,
    SessionStore,
)

__all__ = ["LessonRepository", "ScoringEngine", "SessionStore"]
