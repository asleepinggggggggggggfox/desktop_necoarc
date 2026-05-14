from __future__ import annotations

import os
import base64
import sys
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.config import AppConfig
from core.deepseek_client import DeepSeekClient
from core.xunfei_speech_to_text import XunfeiSpeechToText
from backend.dashscope_tts import DashScopeTtsClient


class ChatRequest(BaseModel):
    text: str


app = FastAPI(title="Desktop Neco-Arc API Proxy")
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ALLOW_ORIGINS", "*").split(","),
    allow_credentials=False,
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)


def build_config() -> AppConfig:
    cfg = AppConfig()
    cfg.deepseek_api_key = os.getenv("DEEPSEEK_API_KEY", "")
    cfg.deepseek_base_url = os.getenv("DEEPSEEK_BASE_URL", cfg.deepseek_base_url)
    cfg.deepseek_model = os.getenv("DEEPSEEK_MODEL", cfg.deepseek_model)
    cfg.xunfei_app_id = os.getenv("XUNFEI_APP_ID", "")
    cfg.xunfei_api_key = os.getenv("XUNFEI_API_KEY", "")
    cfg.xunfei_api_secret = os.getenv("XUNFEI_API_SECRET", "")
    cfg.xunfei_iat_url = os.getenv("XUNFEI_IAT_URL", cfg.xunfei_iat_url)
    cfg.xunfei_language = os.getenv("XUNFEI_LANGUAGE", cfg.xunfei_language)
    cfg.xunfei_accent = os.getenv("XUNFEI_ACCENT", cfg.xunfei_accent)
    cfg.sample_rate = int(os.getenv("SAMPLE_RATE", str(cfg.sample_rate)))
    return cfg


@app.get("/health")
def health() -> dict[str, bool]:
    cfg = build_config()
    return {
        "ok": True,
        "deepseek_configured": bool(cfg.deepseek_api_key),
        "xunfei_configured": bool(
            cfg.xunfei_app_id and cfg.xunfei_api_key and cfg.xunfei_api_secret
        ),
        "dashscope_tts_configured": DashScopeTtsClient().configured,
    }


@app.post("/v1/chat")
def chat(request: ChatRequest) -> dict[str, str]:
    text = request.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="text is required")
    try:
        reply = DeepSeekClient(build_config()).chat(text)
        return {"reply": reply}
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.post("/v1/transcribe")
async def transcribe(audio: UploadFile = File(...)) -> dict[str, str]:
    wav_path = await _save_upload(audio)
    try:
        text = XunfeiSpeechToText(build_config()).transcribe(wav_path)
        return {"text": text}
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    finally:
        wav_path.unlink(missing_ok=True)


@app.post("/v1/voice-chat")
async def voice_chat(audio: UploadFile = File(...)) -> dict[str, str]:
    wav_path = await _save_upload(audio)
    try:
        cfg = build_config()
        text = XunfeiSpeechToText(cfg).transcribe(wav_path)
        reply = DeepSeekClient(cfg).chat(text)
        response = {"text": text, "reply": reply}
        tts = DashScopeTtsClient()
        if tts.configured:
            try:
                wav = tts.synthesize_wav(reply)
                response["audio_base64"] = base64.b64encode(wav).decode("ascii")
                response["audio_format"] = "wav"
            except Exception as exc:
                response["tts_error"] = str(exc)
        return response
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    finally:
        wav_path.unlink(missing_ok=True)


async def _save_upload(audio: UploadFile) -> Path:
    suffix = Path(audio.filename or "audio.wav").suffix or ".wav"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp:
        temp.write(await audio.read())
        return Path(temp.name)
