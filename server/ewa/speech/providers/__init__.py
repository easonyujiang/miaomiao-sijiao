"""语音识别 Provider 抽象与百度实现"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from ewa.config import BAIDU_API_KEY, BAIDU_SECRET_KEY


class SpeechProvider(ABC):
    """语音识别 Provider 抽象基类。"""

    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @abstractmethod
    def configured(self) -> bool:
        """是否已配置可用密钥。"""
        ...

    @abstractmethod
    async def transcribe(self, audio_bytes: bytes, sample_rate: int = 16000) -> str:
        """识别音频，返回文本。"""
        ...


_PROVIDER: SpeechProvider | None = None


def get_speech_provider() -> SpeechProvider:
    """获取百度 ASR Provider 实例。"""
    global _PROVIDER
    if _PROVIDER is None:
        from ewa.speech.providers.baidu import BaiduSpeechProvider
        _PROVIDER = BaiduSpeechProvider(
            api_key=BAIDU_API_KEY,
            secret_key=BAIDU_SECRET_KEY,
        )
    return _PROVIDER


__all__ = ["SpeechProvider", "get_speech_provider"]
