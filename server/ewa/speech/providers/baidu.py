"""百度短语音识别 Provider

文档：https://ai.baidu.com/ai-doc/SPEECH/Ek39uxgmj
流程：
1. 用 API_KEY + SECRET_KEY 换取 access_token
2. 把音频 Base64 + 时长，POST 到 /server_api

后端收到其他格式会用 ffmpeg 先转 WAV。
"""

from __future__ import annotations

import base64
import time
from typing import Any

import httpx

from ewa.speech.providers import SpeechProvider

_TOKEN_URL = "https://aip.baidubce.com/oauth/2.0/token"
_ASR_URL = "https://vop.baidu.com/server_api"


class BaiduSpeechProvider(SpeechProvider):
    """带内存缓存 access_token 的百度 ASR Provider。"""

    name = "baidu"

    def __init__(self, api_key: str, secret_key: str) -> None:
        self.api_key = api_key
        self.secret_key = secret_key
        self._token: str | None = None
        self._token_expires_at: float = 0.0

    def configured(self) -> bool:
        return bool(self.api_key and self.secret_key)

    async def _get_token(self) -> str:
        if self._token and time.time() < self._token_expires_at - 60:
            return self._token

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                _TOKEN_URL,
                params={
                    "grant_type": "client_credentials",
                    "client_id": self.api_key,
                    "client_secret": self.secret_key,
                },
                headers={"Content-Type": "application/json"},
            )
            resp.raise_for_status()
            data = resp.json()

        if "access_token" not in data:
            raise RuntimeError(f"百度 token 获取失败: {data}")

        self._token = data["access_token"]
        expires_in = data.get("expires_in", 2592000)
        self._token_expires_at = time.time() + int(expires_in)
        return self._token

    async def transcribe(self, audio_bytes: bytes, sample_rate: int = 16000) -> str:
        """识别单声道 16kHz PCM/WAV 音频，返回文本。"""
        if not audio_bytes:
            raise ValueError("音频为空")

        token = await self._get_token()
        speech_b64 = base64.b64encode(audio_bytes).decode("utf-8")

        payload: dict[str, Any] = {
            "format": "wav",
            "rate": sample_rate,
            "channel": 1,
            "cuid": "miaomiao-voice",
            "token": token,
            "speech": speech_b64,
            "len": len(audio_bytes),
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                _ASR_URL,
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            resp.raise_for_status()
            data = resp.json()

        err_no = data.get("err_no")
        if err_no != 0:
            err_msg = data.get("err_msg", "未知错误")
            raise RuntimeError(f"百度 ASR 错误 [{err_no}]: {err_msg}")

        result = data.get("result")
        if not result or not isinstance(result, list):
            raise RuntimeError("百度 ASR 返回结果为空")

        return "".join(str(item) for item in result).strip()
