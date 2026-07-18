"""妙喵私教统一配置 —— 所有路径和密钥从环境变量读取。

使用方式:
    from ewa.config import MIAOMIAO_DIR, LESSONS_DIR, MOONSHOT_API_KEY
"""

from __future__ import annotations

import os
from pathlib import Path

# 加载 .env 文件（必须在所有 os.getenv 之前调用）
from dotenv import load_dotenv
_project_root = Path(__file__).resolve().parent.parent
_dotenv_path = _project_root / ".env"
if _dotenv_path.exists():
    load_dotenv(_dotenv_path)

# ── 项目根目录 ──────────────────────────────────────────
PROJECT_ROOT = _project_root

# ── 数据目录 ────────────────────────────────────────────
DATA_DIR = Path(os.getenv("EWA_DATA_DIR", PROJECT_ROOT / "data"))
MIAOMIAO_DIR = Path(os.getenv("MIAOMIAO_DATA_DIR", DATA_DIR / "miaomiao"))
LESSONS_DIR = Path(os.getenv("LESSONS_DATA_DIR", MIAOMIAO_DIR / "lessons"))
SUBTITLE_DIR = Path(os.getenv("SUBTITLE_DATA_DIR", MIAOMIAO_DIR / "subtitles"))
SCORED_VIDEOS = MIAOMIAO_DIR / "scored_videos.json"
VIDEO_LIST = MIAOMIAO_DIR / "video_list.json"

# ── 数据库 ──────────────────────────────────────────────
SITE_DB_PATH = Path(os.getenv("EWA_SITE_DB_PATH", DATA_DIR / "miaomiao.db"))
SITE_SCHEMA_PATH = Path(
    os.getenv("EWA_SITE_SCHEMA_PATH", PROJECT_ROOT / "docs" / "schema.sql")
)

# ── LLM API Keys ────────────────────────────────────────
MOONSHOT_API_KEY = os.getenv("MOONSHOT_API_KEY", os.getenv("KIMI_API_KEY", ""))
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
