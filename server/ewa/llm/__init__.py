"""妙喵私教 — LLM 客户端抽象层

提供统一的 LLM 调用接口，封装 Kimi (Moonshot)、DeepSeek 和通义千问多模态语音模型。

使用方式:
    from ewa.llm import LLMClient

    client = LLMClient()
    answer = await client.chat(system_prompt, user_message)
    result = await client.chat_json(system_prompt, user_message)  # 返回解析后的 dict

语音多模态:
    from ewa.llm import QwenVoiceClient
    answer = await client.chat_with_audio(system_prompt, audio_bytes)
"""

from .client import LLMClient
from .qwen_voice import QwenVoiceClient

__all__ = ["LLMClient", "QwenVoiceClient"]
