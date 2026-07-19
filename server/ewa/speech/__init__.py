"""语音识别模块（百度 ASR）"""

from ewa.speech.providers import get_speech_provider, SpeechProvider
from ewa.speech.api import router

__all__ = ["get_speech_provider", "SpeechProvider", "router"]
