from __future__ import annotations

import base64
import hashlib
import hmac
import json
import ssl
from datetime import datetime, timezone
from pathlib import Path
from time import sleep
from urllib.parse import urlencode, urlparse
from wsgiref.handlers import format_date_time

import soundfile as sf
import websocket

from core.config import AppConfig


class XunfeiSpeechToText:
    def __init__(self, config: AppConfig):
        self.config = config

    def transcribe(self, wav_path: Path) -> str:
        if not all(
            [
                self.config.xunfei_app_id,
                self.config.xunfei_api_key,
                self.config.xunfei_api_secret,
            ]
        ):
            raise RuntimeError("缺少讯飞 API 配置，请检查 plan/api.md 或环境变量。")

        pcm = self._load_pcm(wav_path)
        ws_url = self._authorized_url()
        ws = websocket.create_connection(
            ws_url,
            timeout=30,
            sslopt={"cert_reqs": ssl.CERT_NONE},
        )
        try:
            self._send_audio(ws, pcm)
            return self._receive_text(ws)
        finally:
            ws.close()

    def _load_pcm(self, wav_path: Path) -> bytes:
        audio, sample_rate = sf.read(wav_path, dtype="int16", always_2d=False)
        if sample_rate != self.config.sample_rate:
            raise RuntimeError(
                f"录音采样率为 {sample_rate}，当前讯飞配置要求 {self.config.sample_rate}。"
            )
        return audio.tobytes()

    def _authorized_url(self) -> str:
        parsed = urlparse(self.config.xunfei_iat_url)
        host = parsed.netloc
        path = parsed.path or "/v2/iat"
        date = format_date_time(datetime.now(timezone.utc).timestamp())
        signature_origin = f"host: {host}\ndate: {date}\nGET {path} HTTP/1.1"
        signature_sha = hmac.new(
            self.config.xunfei_api_secret.encode("utf-8"),
            signature_origin.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).digest()
        signature = base64.b64encode(signature_sha).decode("utf-8")
        authorization_origin = (
            f'api_key="{self.config.xunfei_api_key}", '
            f'algorithm="hmac-sha256", headers="host date request-line", '
            f'signature="{signature}"'
        )
        authorization = base64.b64encode(
            authorization_origin.encode("utf-8")
        ).decode("utf-8")
        query = urlencode(
            {"authorization": authorization, "date": date, "host": host}
        )
        return f"{self.config.xunfei_iat_url}?{query}"

    def _send_audio(self, ws, pcm: bytes) -> None:
        frame_size = 1280
        offset = 0
        first = True
        while offset < len(pcm):
            chunk = pcm[offset : offset + frame_size]
            offset += frame_size
            status = 0 if first else 1
            if offset >= len(pcm):
                status = 2
            payload = {
                "data": {
                    "status": status,
                    "format": "audio/L16;rate=16000",
                    "encoding": "raw",
                    "audio": base64.b64encode(chunk).decode("utf-8"),
                }
            }
            if first:
                payload["common"] = {"app_id": self.config.xunfei_app_id}
                payload["business"] = {
                    "language": self.config.xunfei_language,
                    "domain": "iat",
                    "accent": self.config.xunfei_accent,
                    "vad_eos": 3000,
                }
                first = False
            ws.send(json.dumps(payload))
            sleep(0.04)

    def _receive_text(self, ws) -> str:
        parts: list[str] = []
        while True:
            message = json.loads(ws.recv())
            code = message.get("code", 0)
            if code != 0:
                raise RuntimeError(message.get("message", "讯飞语音识别失败。"))
            data = message.get("data", {})
            result = data.get("result", {})
            for ws_item in result.get("ws", []):
                for cw in ws_item.get("cw", []):
                    word = cw.get("w", "")
                    if word:
                        parts.append(word)
            if data.get("status") == 2:
                break
        text = "".join(parts).strip()
        if not text:
            raise RuntimeError("讯飞没有返回有效识别文本。")
        return text

