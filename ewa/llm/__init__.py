"""妙喵私教 — LLM 客户端抽象层

提供统一的 LLM 调用接口，封装 Kimi (Moonshot) 和 DeepSeek 的 API 调用。

使用方式:
    from ewa.llm import LLMClient

    client = LLMClient()
    answer = await client.chat(system_prompt, user_message)
    result = await client.chat_json(system_prompt, user_message)  # 返回解析后的 dict
"""

from .client import LLMClient

__all__ = ["LLMClient"]
