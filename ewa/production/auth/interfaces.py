"""Auth 框架 — 抽象接口定义。

使用方式（生产阶段）：
    from ewa.production.auth import AuthProvider

    class JWTProvider(AuthProvider):
        async def validate_token(self, token: str) -> dict | None:
            ...
        async def create_session(self, user_id: str) -> str:
            ...
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class AuthProvider(ABC):
    """可插拔的认证提供者。

    替换 DEMO 阶段的 session_id 方式：
    - JWT token 验证
    - OAuth2 流程（GitHub、Google）
    - API Key 验证（Chrome 插件客户端）
    """

    @abstractmethod
    async def validate_token(self, token: str) -> dict | None:
        """验证凭据，返回用户身份信息或 None。"""
        ...

    @abstractmethod
    async def create_session(self, user_id: str) -> str:
        """为用户创建新会话，返回 session token。"""
        ...


class TokenValidator(ABC):
    """独立的 token 验证器（更轻量的接口）。"""

    @abstractmethod
    async def validate(self, token: str) -> bool:
        """验证 token 是否有效。"""
        ...
