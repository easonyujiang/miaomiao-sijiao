"""Analytics 框架 — 抽象接口定义。

使用方式（生产阶段）：
    from ewa.production.analytics import AnalyticsBackend, AnalyticsEvent

    class PostHogBackend(AnalyticsBackend):
        async def track(self, event: AnalyticsEvent) -> None:
            ...
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class AnalyticsEvent:
    """单条分析事件。"""
    event_type: str                        # e.g. "quiz_submit", "lesson_complete"
    user_id: str | None = None
    session_id: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)
    timestamp: str = ""                    # ISO-8601；空值时由后端填充


class AnalyticsBackend(ABC):
    """可插拔的分析后端。

    替换 DEMO 阶段的 SQLite visitor_events 表：
    - PostHog / Segment / Amplitude
    - BigQuery streaming insert
    - 自定义数据仓库
    """

    @abstractmethod
    async def track(self, event: AnalyticsEvent) -> None:
        """持久化单条事件。"""
        ...
