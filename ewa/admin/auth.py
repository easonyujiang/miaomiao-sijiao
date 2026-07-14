"""管理后台 Token 认证

简单 Bearer Token 验证，从 ADMIN_TOKEN 环境变量读取。
"""

from __future__ import annotations

import os

from fastapi import HTTPException, Request

_ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "admin-secret-change-me")


def verify_token(request: Request) -> str:
    """验证请求中的 Bearer Token，返回 token 值或抛出 401。"""
    auth_header = request.headers.get("Authorization", "")
    token = auth_header.replace("Bearer ", "").strip()

    if not token or token != _ADMIN_TOKEN:
        raise HTTPException(
            status_code=401,
            detail="Unauthorized — Header: Authorization: Bearer <token>",
        )
    return token
