"""阿里云智能语音交互（NLS）Provider

使用 REST API 进行一句话识别：
1. 用 AccessKey + Secret 通过 nls-meta 服务换取 Token
2. 把 16kHz 单声道 WAV 音频 POST 到 NLS Gateway

需要的凭证：
- ALIYUN_ACCESS_KEY_ID
- ALIYUN_ACCESS_KEY_SECRET
- ALIYUN_APP_KEY
"""

from __future__ import annotations

import json
import time
from typing import Any

import httpx

from ewa.speech.providers import SpeechProvider

_TOKEN_ENDPOINT = "https://nls-meta.cn-shanghai.aliyuncs.com"
_ASR_ENDPOINT = "https://nls-gateway.cn-shanghai.aliyuncs.com/stream/v1/asr"


class AliyunSpeechProvider(SpeechProvider):
    """阿里云 NLS 语音识别 Provider。"""

    name = "aliyun"

    def __init__(self, access_key_id: str, access_key_secret: str, app_key: str) -> None:
        self.access_key_id = access_key_id
        self.access_key_secret = access_key_secret
        self.app_key = app_key
        self._token: str | None = None
        self._token_expires_at: float = 0.0

    def configured(self) -> bool:
        return bool(self.access_key_id and self.access_key_secret and self.app_key)

    def _get_token(self) -> str:
        """通过阿里云 SDK 创建 NLS Token。"""
        if self._token and time.time() < self._token_expires_at - 60:
            return self._token

        try:
            from aliyunsdkcore.client import AcsClient
            from aliyunsdknls_meta.request.v20190515 import CreateTokenRequest
        except ImportError as exc:
            raise RuntimeError("缺少阿里云 SDK，请安装 aliyun-python-sdk-core 和 aliyun-python-sdk-nls-meta") from exc

        client = AcsClient(self.access_key_id, self.access_key_secret, "cn-shanghai")
        request = CreateTokenRequest()
        request.set_accept_format("json")

        response = client.do_action_with_exception(request)
        data = json.loads(response)

        token = data.get("Token", {}).get("Id")
        expire_time = data.get("Token", {}).get("ExpireTime")
        if not token:
            raise RuntimeError(f"阿里云 token 获取失败: {data}")

        self._token = token
        # expire_time 是 Unix 秒级时间戳，默认约 1 小时
        self._token_expires_at = float(expire_time or (time.time() + 3600))
        return self._token

    async def transcribe(self, audio_bytes: bytes, sample_rate: int = 16000) -> str:
        """识别 16kHz 单声道 WAV 音频，返回文本。"""
        if not audio_bytes:
            raise ValueError("音频为空")

        token = self._get_token()

        params: dict[str, Any] = {
            "format": "wav",
            "sample_rate": sample_rate,
            "enable_punctuation_prediction": "true",
            "enable_inverse_text_normalization": "true",
            "disfluency": "true",
        }

        headers = {
            "X-NLS-Token": token,
            "Content-Type": "application/octet-stream",
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                _ASR_ENDPOINT,
                params=params,
                headers=headers,
                content=audio_bytes,
            )
            resp.raise_for_status()
            data = resp.json()

        status = data.get("status")
        if status != 20000000:
            message = data.get("message", "未知错误")
            raise RuntimeError(f"阿里云 ASR 错误 [{status}]: {message}")

        result = data.get("result")
        if not result:
            raise RuntimeError("阿里云 ASR 返回结果为空")

        return str(result).strip()
