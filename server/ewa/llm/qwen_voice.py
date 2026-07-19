"""通义千问多模态语音模型客户端（Qwen3.5-Omni）

直接接受音频输入，由模型同时完成语音理解、转写和回复。
使用阿里云 DashScope OpenAI 兼容接口：
- endpoint: {base_url}/chat/completions
- 认证: Authorization: Bearer {api_key}
- 音频输入字段: {"type": "input_audio", "input_audio": {"data": "base64", "format": "wav"}}

文档参考: https://www.qianwenai.com/models/qwen3.5-omni-plus
"""

from __future__ import annotations

import base64
from typing import Any

import httpx

from ewa.config import QWEN_API_BASE, QWEN_API_KEY, QWEN_VOICE_MODEL

_MIN_KEY_LENGTH = 10


def _is_valid_key(key: str) -> bool:
    if not key:
        return False
    if len(key) < _MIN_KEY_LENGTH:
        return False
    if key.endswith("...") and len(key) <= 8:
        return False
    return True


class QwenVoiceClient:
    """Qwen3.5-Omni 语音多模态客户端。

    >>> client = QwenVoiceClient()
    >>> answer = await client.chat_with_audio("你是猫娘", audio_bytes)
    """

    def __init__(self) -> None:
        self._api_key = QWEN_API_KEY
        self._base_url = QWEN_API_BASE.rstrip("/")
        self._model = QWEN_VOICE_MODEL

    @property
    def is_available(self) -> bool:
        return _is_valid_key(self._api_key) and bool(self._model)

    async def chat_with_audio(
        self,
        system: str,
        audio_bytes: bytes,
        user_text: str = "",
        max_tokens: int = 600,
        temperature: float = 0.7,
        timeout: float = 60.0,
    ) -> str | None:
        """发送系统提示 + 音频输入，返回模型文本回复。

        Args:
            system: 系统提示词（宠物人设、风格、知识库等）。
            audio_bytes: WAV/MP3 等音频二进制数据。
            user_text: 可选的伴随文本提示（如 "请回答我的问题"）。
            max_tokens: 最大输出 token 数。
            temperature: 生成温度。
            timeout: 请求总超时秒数。

        Returns:
            模型回复文本，或 None（调用失败或配置不可用）。
        """
        if not self.is_available or not audio_bytes:
            return None

        audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")

        user_content: list[dict[str, Any]] = [
            {
                "type": "input_audio",
                "input_audio": {"data": audio_b64, "format": "wav"},
            }
        ]
        if user_text:
            user_content.append({"type": "text", "text": user_text})

        payload: dict[str, Any] = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user_content},
            ],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        url = f"{self._base_url}/chat/completions"

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(
                    url,
                    headers={
                        "Authorization": f"Bearer {self._api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
                if resp.status_code != 200:
                    return None

                data = resp.json()
                choices = data.get("choices", [])
                if not choices:
                    return None

                return str(choices[0].get("message", {}).get("content", "")).strip()
        except Exception:
            return None


__all__ = ["QwenVoiceClient"]
