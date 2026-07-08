"""Auth 框架 — 认证与授权接口。

DEMO 阶段使用 session_id 字符串标识用户，无需认证。
生产阶段通过此模块接入真实身份系统（JWT、OAuth2、API Key 等）。
"""

from ewa.production.auth.interfaces import AuthProvider, TokenValidator

__all__ = ["AuthProvider", "TokenValidator"]
