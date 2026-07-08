"""Extension 框架 — 抽象接口定义。

使用方式（生产阶段）：
    from ewa.production.extension import SubtitleProvider

    class YouTubeSubtitleProvider(SubtitleProvider):
        async def fetch(self, video_id: str, platform: str) -> list[dict]:
            ...
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class SubtitleProvider(ABC):
    """字幕获取抽象。

    替换 demo/subtitle.py 的本地 JSON 缓存：
    - YouTube / Bilibili API 实时获取
    - Whisper ASR 流水线
    - 第三方字幕服务
    """

    @abstractmethod
    async def fetch(self, video_id: str, platform: str) -> list[dict[str, Any]]: ...

    @abstractmethod
    async def search(
        self, video_id: str, query: str, top_k: int = 5
    ) -> list[dict[str, Any]]: ...


class VideoMatcher(ABC):
    """跨平台视频匹配抽象。

    替换 demo/subtitle.py 的字符重叠启发式算法：
    - Embedding 语义匹配
    - 视频指纹（DP-MIR）
    - 平台 API 交叉引用
    """

    @abstractmethod
    async def match(self, title: str, source_platform: str) -> dict[str, Any] | None: ...


class QAService(ABC):
    """视频问答服务抽象。

    替换 demo/ext.py chat 端点的三层回退逻辑：
    - RAG 流水线（向量检索 + LLM 生成）
    - 多模态问答（视频帧 + 字幕）
    """

    @abstractmethod
    async def answer(
        self, question: str, video_id: str, platform: str, current_time_sec: int = 0
    ) -> dict[str, Any]: ...
