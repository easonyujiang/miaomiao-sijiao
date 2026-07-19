"""妙喵私教 TTS 服务 —— edge-tts 封装

支持音频缓存，命中缓存时直接返回文件，避免重复调用 edge-tts。
"""

from __future__ import annotations

import asyncio
import hashlib
from pathlib import Path

import edge_tts

from ewa.config import MIAOMIAO_DIR

# 默认使用 Xiaoxiao 中文女声；后续可从配置/请求参数切换
DEFAULT_VOICE = "zh-CN-XiaoxiaoNeural"

TTS_CACHE_DIR = MIAOMIAO_DIR / "tts_cache"
TTS_CACHE_DIR.mkdir(parents=True, exist_ok=True)


class TTSOptions:
    """TTS 可选参数"""

    def __init__(
        self,
        voice: str | None = None,
        rate: str = "+0%",
        volume: str = "+0%",
        pitch: str = "+0Hz",
    ) -> None:
        self.voice = voice or DEFAULT_VOICE
        self.rate = rate
        self.volume = volume
        self.pitch = pitch


def _cache_key(text: str, options: TTSOptions) -> str:
    """生成缓存 key：文本 + 语音参数 MD5"""
    content = f"{text}|{options.voice}|{options.rate}|{options.volume}|{options.pitch}"
    return hashlib.md5(content.encode("utf-8")).hexdigest()


def _cached_path(cache_key: str) -> Path:
    """缓存文件路径"""
    return TTS_CACHE_DIR / f"{cache_key}.mp3"


async def synthesize(text: str, options: TTSOptions | None = None) -> bytes:
    """合成语音，返回 MP3 字节。

    若缓存存在则直接读取，否则调用 edge-tts 生成并写入缓存。
    """
    opts = options or TTSOptions()
    key = _cache_key(text, opts)
    path = _cached_path(key)

    if path.exists():
        return path.read_bytes()

    communicate = edge_tts.Communicate(text, opts.voice, rate=opts.rate, volume=opts.volume)

    # edge-tts 流式写入临时文件
    temp_path = path.with_suffix(".tmp")
    await communicate.save(str(temp_path))

    # 移动到最终路径
    temp_path.rename(path)
    return path.read_bytes()


async def synthesize_to_file(text: str, options: TTSOptions | None = None) -> Path:
    """合成语音并返回缓存文件路径"""
    opts = options or TTSOptions()
    key = _cache_key(text, opts)
    path = _cached_path(key)

    if path.exists():
        return path

    communicate = edge_tts.Communicate(text, opts.voice, rate=opts.rate, volume=opts.volume)
    temp_path = path.with_suffix(".tmp")
    await communicate.save(str(temp_path))
    temp_path.rename(path)
    return path


# 兼容同步调用（测试或简单脚本）
def synthesize_sync(text: str, options: TTSOptions | None = None) -> bytes:
    return asyncio.run(synthesize(text, options))
