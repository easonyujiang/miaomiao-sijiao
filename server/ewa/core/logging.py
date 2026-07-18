"""统一日志配置

初始化 Python logging，输出到：控制台 + 文件 + SQLite 审计日志表。

使用方式:
    from ewa.core.logging import setup_logging, get_logger
    logger = get_logger(__name__)
    logger.info("something happened")
"""

from __future__ import annotations

import logging
import os
import sqlite3
import time
from logging.handlers import RotatingFileHandler
from pathlib import Path

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

# 全局 logger 缓存
_loggers: dict[str, logging.Logger] = {}
_db_path: str | None = None
_initialized: bool = False


def get_db_path() -> str:
    global _db_path
    if not _db_path:
        _db_path = os.getenv("EWA_SITE_DB_PATH", "data/miaomiao.db")
    return _db_path


def set_db_path(path: str) -> None:
    global _db_path
    _db_path = path


class SQLiteLogHandler(logging.Handler):
    """将 WARNING+ 级别日志写入 admin_audit_log 表。

    使用模块级连接复用，避免每条日志都创建新连接。
    """

    _connection: sqlite3.Connection | None = None

    def _get_connection(self) -> sqlite3.Connection:
        if self._connection is None:
            self._connection = sqlite3.connect(get_db_path(), timeout=5.0)
            self._connection.execute("PRAGMA journal_mode=WAL")
        return self._connection

    def emit(self, record: logging.LogRecord) -> None:
        try:
            db = self._get_connection()
            db.execute(
                """INSERT INTO admin_audit_log
                   (timestamp, level, module, action, table_name, record_id, detail, ip)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(record.created)),
                    record.levelname,
                    record.name,
                    getattr(record, "action", "LOG"),
                    getattr(record, "table_name", None),
                    getattr(record, "record_id", None),
                    record.getMessage()[:500],
                    getattr(record, "ip", None),
                ),
            )
            db.commit()
        except Exception:
            pass  # 日志记录失败不应影响主流程


def setup_logging(db_path: str | None = None, log_dir: str | None = None) -> None:
    """初始化日志系统。

    Args:
        db_path: SQLite 数据库路径
        log_dir: 日志文件目录（默认项目根目录）
    """
    global _initialized
    if _initialized:
        return
    _initialized = True

    if db_path:
        set_db_path(db_path)

    root = logging.getLogger()
    root.setLevel(logging.INFO)

    # 控制台 handler
    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG)
    console.setFormatter(
        logging.Formatter("%(asctime)s | %(levelname)-7s | %(name)s | %(message)s", datefmt="%H:%M:%S")
    )
    root.addHandler(console)

    # 文件 handler（按大小轮转，10MB）
    project_root = Path(__file__).resolve().parents[2]
    log_dir = Path(log_dir or project_root)
    log_file = log_dir / "ewa.log"
    try:
        file_handler = RotatingFileHandler(
            str(log_file), maxBytes=10 * 1024 * 1024, backupCount=3, encoding="utf-8"
        )
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
                datefmt="%Y-%m-%dT%H:%M:%S",
            )
        )
        root.addHandler(file_handler)
    except Exception:
        pass  # 文件不可写时回退到仅控制台

    # SQLite handler（延迟连接，首次写入时连接）
    sqlite_handler = SQLiteLogHandler()
    sqlite_handler.setLevel(logging.WARNING)
    root.addHandler(sqlite_handler)


def get_logger(name: str) -> logging.Logger:
    """获取或创建模块级 logger。"""
    if name not in _loggers:
        _loggers[name] = logging.getLogger(name)
    return _loggers[name]


def log_admin_action(
    module: str,
    action: str,
    table_name: str | None = None,
    record_id: str | None = None,
    detail: str = "",
    ip: str | None = None,
    level: str = "INFO",
) -> None:
    """记录一条管理操作到审计日志。"""
    logger = get_logger(f"admin.{module}")
    extra = {"action": action, "table_name": table_name, "record_id": record_id, "ip": ip}
    msg = detail or f"{action} {table_name or ''} {record_id or ''}".strip()
    getattr(logger, level.lower(), logger.info)(msg, extra=extra)


# ── 请求日志中间件 ──────────────────────────────────────────────


def create_request_logging_middleware():
    """记录每个 API 请求的方法、路径、状态码、耗时。"""

    class RequestLoggingMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request: Request, call_next):
            start = time.time()
            response = await call_next(request)
            elapsed_ms = round((time.time() - start) * 1000)

            path = request.url.path
            if path.startswith("/api/"):
                logger = get_logger("api.request")
                forwarded = request.headers.get("X-Forwarded-For", "")
                client_ip = forwarded.split(",")[0].strip() if forwarded else (
                    request.client.host if request.client else "unknown"
                )
                logger.info(
                    "%s %s → %s (%dms)",
                    request.method,
                    path,
                    response.status_code,
                    elapsed_ms,
                    extra={
                        "action": "REQUEST",
                        "table_name": path,
                        "record_id": str(response.status_code),
                        "ip": client_ip,
                    },
                )

            return response

    return RequestLoggingMiddleware
