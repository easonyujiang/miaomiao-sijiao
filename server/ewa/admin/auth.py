"""管理后台 Token 认证

简单 Bearer Token 验证，从 ADMIN_TOKEN 环境变量读取。
未设置时随机生成并打印到日志，防止弱口令暴露。
"""

from __future__ import annotations

import os
import secrets
import logging

from fastapi import HTTPException, Request

_logger = logging.getLogger("ewa.admin.auth")

_env_token = os.getenv("ADMIN_TOKEN", "").strip()
if _env_token:
    _ADMIN_TOKEN = _env_token
else:
    _ADMIN_TOKEN = secrets.token_urlsafe(32)
    _logger.warning(
        "ADMIN_TOKEN 未设置，已随机生成。请在环境变量中设置 ADMIN_TOKEN 以保持稳定。"
        " 生成的 token: %s", _ADMIN_TOKEN
    )


def verify_token(request: Request) -> str:
    """验证请求中的 Bearer Token，返回 token 值或抛出 401。"""
    auth_header = request.headers.get("Authorization", "")
    # 严格前缀判断（此前用 replace 会放过 "xxBearer yy" 这类畸形头）
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Unauthorized — Header: Authorization: Bearer <token>",
        )
    token = auth_header[len("Bearer "):].strip()

    # compare_digest：时序安全比较，避免逐字节短路泄露前缀信息
    if not token or not secrets.compare_digest(token, _ADMIN_TOKEN):
        raise HTTPException(
            status_code=401,
            detail="Unauthorized — Header: Authorization: Bearer <token>",
        )
    return token
