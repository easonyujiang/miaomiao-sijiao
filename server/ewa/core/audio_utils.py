"""音频工具函数（跨模块复用）

提供 ffmpeg 转换等通用音频处理能力。
"""

from __future__ import annotations

import asyncio
import subprocess
from pathlib import Path


async def convert_to_wav(input_path: Path, output_path: Path, sample_rate: int = 16000) -> None:
    """用 ffmpeg 把任意输入音频转成指定采样率单声道 WAV。

    Args:
        input_path: 输入音频文件路径。
        output_path: 输出 WAV 文件路径。
        sample_rate: 输出采样率（默认 16kHz）。
    """
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(input_path),
        "-ar",
        str(sample_rate),
        "-ac",
        "1",
        "-acodec",
        "pcm_s16le",
        str(output_path),
    ]
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg 转换失败: {stderr.decode('utf-8', errors='ignore')}")


__all__ = ["convert_to_wav"]
