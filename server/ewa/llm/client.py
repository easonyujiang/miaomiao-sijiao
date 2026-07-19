"""统一的 LLM 客户端

封装 Kimi (Moonshot) 和 DeepSeek 的 API 调用。
提供 chat() 和 chat_json() 两个主要接口。

优先级：Kimi → DeepSeek → 返回 None
"""

from __future__ import annotations

import json
import re
from typing import Any

from ewa.config import MOONSHOT_API_KEY, DEEPSEEK_API_KEY
from ewa.core.logging import get_logger

logger = get_logger(__name__)

# 最小 API Key 长度（过滤 sk-... 等占位符）
_MIN_KEY_LENGTH = 10


def _is_valid_key(key: str) -> bool:
    """校验 API Key 是否有效（非空且不是占位符）。"""
    if not key:
        return False
    if len(key) < _MIN_KEY_LENGTH:
        return False
    # 过滤明显占位符: "sk-..." 等
    if key.endswith("...") and len(key) <= 8:
        return False
    return True


class LLMClient:
    """统一的 LLM 调用客户端。

    >>> client = LLMClient()
    >>> answer = await client.chat("你是猫娘", "你好")
    >>> result = await client.chat_json("你是JSON评分助手", "{...}")
    """

    # Provider 配置
    _PROVIDERS = [
        {
            "name": "kimi",
            "api_key_attr": "kimi_key",
            "api_url": "https://api.moonshot.cn/v1/chat/completions",
            "model": "moonshot-v1-8k",
        },
        {
            "name": "deepseek",
            "api_key_attr": "deepseek_key",
            "api_url": "https://api.deepseek.com/v1/chat/completions",
            "model": "deepseek-chat",
        },
    ]

    def __init__(self) -> None:
        self._kimi_key = MOONSHOT_API_KEY
        self._deepseek_key = DEEPSEEK_API_KEY

    @property
    def is_available(self) -> bool:
        """是否有可用的 LLM provider（API Key 有效）。"""
        return _is_valid_key(self._kimi_key) or _is_valid_key(self._deepseek_key)

    async def chat(
        self,
        system: str,
        user: str,
        max_tokens: int = 600,
        temperature: float = 0.1,
        timeout: int | None = None,
    ) -> str | None:
        """发送聊天请求，返回文本回复。

        Args:
            system: 系统提示词
            user: 用户消息
            max_tokens: 最大输出 token 数
            temperature: 生成温度
            timeout: 请求总超时秒数（None=使用默认 connect:5s read:15s）

        Returns:
            LLM 返回的文本内容，或 None（所有 provider 不可用）
        """
        for provider in self._PROVIDERS:
            api_key = self._kimi_key if provider["name"] == "kimi" else self._deepseek_key
            if not _is_valid_key(api_key):
                continue

            result = await self._call(
                api_url=provider["api_url"],
                api_key=api_key,
                model=provider["model"],
                system=system,
                user=user,
                max_tokens=max_tokens,
                temperature=temperature,
                timeout=timeout,
            )
            if result is not None:
                return result

        return None

    async def chat_json(
        self,
        system: str,
        user: str,
        max_tokens: int = 300,
        timeout: int = 20,
    ) -> dict[str, Any] | None:
        """发送聊天请求，返回解析后的 JSON 对象。

        自动处理 LLM 返回的各种 JSON 格式：
        - 纯 JSON
        - ```json ... ``` 代码块
        - 文本中的 { ... }

        Returns:
            解析后的 dict，或 None
        """
        text = await self.chat(
            system=system,
            user=user,
            max_tokens=max_tokens,
            temperature=0.1,
            timeout=timeout,
        )
        if text is None:
            return None
        return self._parse_json(text)

    @staticmethod
    async def _call(
        api_url: str,
        api_key: str,
        model: str,
        system: str,
        user: str,
        max_tokens: int,
        temperature: float,
        timeout: int | None,
    ) -> str | None:
        """执行实际的 HTTP 调用。

        timeout=None 时使用细分超时：connect=5s, read=15s, write=5s。
        传入 int 时覆盖全部超时（向后兼容）。
        """
        try:
            import httpx

            if timeout is not None:
                timeout_config = httpx.Timeout(
                    connect=min(timeout, 10.0),
                    read=float(timeout),
                    write=min(timeout, 10.0),
                    pool=5.0,
                )
            else:
                timeout_config = httpx.Timeout(
                    connect=5.0, read=15.0, write=5.0, pool=5.0,
                )

            async with httpx.AsyncClient(timeout=timeout_config) as client:
                res = await client.post(
                    api_url,
                    headers={"Authorization": f"Bearer {api_key}"},
                    json={
                        "model": model,
                        "messages": [
                            {"role": "system", "content": system},
                            {"role": "user", "content": user},
                        ],
                        "max_tokens": max_tokens,
                        "temperature": temperature,
                    },
                )
                if res.status_code == 200:
                    return res.json()["choices"][0]["message"]["content"]
                logger.warning("LLM 返回非 200 [%s] %s: %s", res.status_code, api_url, res.text[:200])
        except Exception as e:
            logger.warning("LLM 调用失败 %s: %s", api_url, e)

        return None

    @staticmethod
    def _parse_json(text: str) -> dict[str, Any] | None:
        """从 LLM 返回文本中提取 JSON 对象。"""
        # 直接解析
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # 提取 ```json ... ``` 块
        m = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(1))
            except json.JSONDecodeError:
                pass

        # 提取 { ... }
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                pass

        return None
