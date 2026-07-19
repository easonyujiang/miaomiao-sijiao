from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, HTTPException, UploadFile

from ewa.core.audio_utils import convert_to_wav
from ewa.speech import get_speech_provider

router = APIRouter(prefix="/api", tags=["speech"])


@router.post("/speech-to-text")
async def speech_to_text(audio: UploadFile = File(...)) -> dict[str, Any]:
    provider = get_speech_provider()
    if not provider.configured():
        raise HTTPException(
            503,
            "语音服务未配置：请设置 BAIDU_API_KEY / BAIDU_SECRET_KEY",
        )

    suffix = Path(audio.filename or "audio.webm").suffix or ".webm"

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            input_path = tmp / f"input{suffix}"
            output_path = tmp / "output.wav"

            content = await audio.read()
            input_path.write_bytes(content)

            await convert_to_wav(input_path, output_path)
            wav_bytes = output_path.read_bytes()

            text = await provider.transcribe(wav_bytes)
    except RuntimeError as exc:
        raise HTTPException(500, f"语音识别失败: {exc}") from exc
    except Exception as exc:
        raise HTTPException(500, f"处理音频失败: {exc}") from exc

    return {"text": text}
