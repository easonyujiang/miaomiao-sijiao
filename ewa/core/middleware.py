"""核心中间件

- CORS 中间件（环境变量可配置）
- SPA 静态文件服务
- 全局异常处理
"""

from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException


def configure_cors(app: FastAPI) -> None:
    """配置 CORS 中间件。

    通过环境变量 EWA_CORS_ORIGINS 控制允许的 origins：
    - 未设置：默认允许 localhost 开发 origin
    - 设为 "*"：允许全部来源（仅用于调试）
    - 设为逗号分隔列表：如 "https://example.com,https://app.example.com"
    """
    origins_env = os.getenv("EWA_CORS_ORIGINS", "")

    if origins_env == "*":
        origins = ["*"]
        methods = ["*"]
        headers = ["*"]
    elif origins_env:
        origins = [o.strip() for o in origins_env.split(",") if o.strip()]
        methods = ["GET", "POST", "PUT", "DELETE"]
        headers = ["Content-Type", "Authorization"]
    else:
        # 默认：仅允许本地开发
        origins = [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:8000",
            "http://127.0.0.1:8000",
        ]
        methods = ["GET", "POST", "PUT", "DELETE"]
        headers = ["Content-Type", "Authorization"]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_methods=methods,
        allow_headers=headers,
    )


class SPAStaticFiles(StaticFiles):
    """Serve index.html for client-side routes (e.g. /blog/:slug)."""

    async def get_response(self, path: str, scope):
        try:
            response = await super().get_response(path, scope)
            if response.status_code != 404:
                return response
        except StarletteHTTPException as exc:
            if exc.status_code != 404:
                raise
        return await super().get_response("index.html", scope)


# ── 请求限流 ────────────────────────────────────────────────

class RateLimiter:
    """简单的内存请求限流器。

    DEMO 阶段使用进程内存，生产阶段应替换为 Redis 等分布式方案。
    """

    def __init__(self, requests_per_minute: int = 60):
        self._requests_per_minute = requests_per_minute
        self._window: dict[str, list[float]] = {}

    def is_allowed(self, key: str, now: float) -> bool:
        """检查 key 是否在限流窗口内。"""
        window_start = now - 60.0
        # 清理过期记录
        if key in self._window:
            self._window[key] = [t for t in self._window[key] if t > window_start]
        else:
            self._window[key] = []

        if len(self._window[key]) >= self._requests_per_minute:
            return False

        self._window[key].append(now)
        return True

    def remaining(self, key: str, now: float) -> int:
        """返回剩余可用请求数。"""
        window_start = now - 60.0
        if key not in self._window:
            return self._requests_per_minute
        valid = [t for t in self._window[key] if t > window_start]
        return max(0, self._requests_per_minute - len(valid))


# 全局限流器实例
rate_limiter = RateLimiter(requests_per_minute=60)


def create_rate_limit_middleware():
    """创建请求限流 ASGI 中间件。

    对 /api/lesson/quiz_submit 和 /api/ext/chat 端点
    限制每分钟 20 次请求（可能触发 LLM 调用，需控制成本）。

    其他 API 端点限制每分钟 60 次。
    """
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.responses import JSONResponse

    class RateLimitMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request, call_next):
            import time

            path = request.url.path
            now = time.time()

            # 对可能调用 LLM 的端点使用更严格的限流
            if path in ("/api/lesson/quiz_submit", "/api/ext/chat"):
                limit = 20
            else:
                limit = 60

            # 使用客户端 IP 作为限流 key
            forwarded = request.headers.get("X-Forwarded-For")
            client_ip = forwarded.split(",")[0].strip() if forwarded else (
                request.client.host if request.client else "unknown"
            )
            key = f"{client_ip}:{path}"

            # 临时覆盖限流器配置
            limiter = RateLimiter(requests_per_minute=limit)
            if not limiter.is_allowed(key, now):
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": "rate_limited",
                        "message": "请求过于频繁，请稍后再试",
                        "retry_after_sec": 60,
                    },
                )

            return await call_next(request)

    return RateLimitMiddleware
