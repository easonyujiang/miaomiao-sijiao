"""妙喵私教 — 核心框架层

提供 FastAPI 应用工厂、CORS 中间件、SPA 静态文件服务等基础能力。
"""

from .app import create_app

__all__ = ["create_app"]
