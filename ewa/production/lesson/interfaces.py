"""Lesson 框架 — 抽象接口定义。

使用方式（生产阶段）：
    from ewa.production.lesson import ScoringEngine

    class BertScoringEngine(ScoringEngine):
        async def score(self, answer, question, context=None) -> dict:
            ...
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class LessonRepository(ABC):
    """课程数据访问抽象。

    替换 demo/store.py 的文件系统 JSON 加载：
    - PostgreSQL / MySQL 课程目录
    - CMS 后端课程内容
    - 版本化课程发布
    """

    @abstractmethod
    async def get(self, lesson_id: str) -> dict[str, Any] | None: ...

    @abstractmethod
    async def list_by_creator(self, creator_id: str) -> list[dict[str, Any]]: ...

    @abstractmethod
    async def find_by_video(self, video_id: str, platform: str) -> dict[str, Any] | None: ...


class ScoringEngine(ABC):
    """评分引擎抽象。

    替换 demo/scoring.py 的关键词 + LLM 混合方案：
    - 微调 BERT/RoBERTa 语义相似度
    - 多模态评分（文本 + 语音 + 代码）
    - 加权评分标准与部分得分
    """

    @abstractmethod
    async def score(
        self,
        answer: str,
        question: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]: ...


class SessionStore(ABC):
    """学习会话持久化抽象。

    替换 demo/store.py 的原始 SQLite：
    - Redis 热数据 + PostgreSQL 冷存储
    - 分布式会话状态（水平扩展）
    - CQRS 会话事件流
    """

    @abstractmethod
    async def load(self, session_id: str) -> dict[str, Any] | None: ...

    @abstractmethod
    async def save(self, session: dict[str, Any]) -> None: ...

    @abstractmethod
    async def delete(self, session_id: str) -> None: ...
