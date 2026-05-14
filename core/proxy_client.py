from __future__ import annotations

import base64
from pathlib import Path

import requests

from core.config import AppConfig


class ProxyClient:
    def __init__(self, config: AppConfig):
        self.config = config

    def voice_chat(self, wav_path: Path) -> tuple[str, str, bytes | None]:
        if not self.config.proxy_base_url:
            raise RuntimeError("缺少后端代理地址，请在 config.yaml 设置 proxy_base_url。")

        url = self.config.proxy_base_url.rstrip("/") + "/v1/voice-chat"
        try:
            with wav_path.open("rb") as audio:
                response = requests.post(
                    url,
                    files={"audio": (wav_path.name, audio, "audio/wav")},
                    timeout=120,
                )
            if not response.ok:
                detail = response.text
                try:
                    detail = response.json().get("detail", detail)
                except ValueError:
                    pass
                raise RuntimeError(f"后端代理请求失败：HTTP {response.status_code}，{detail}")
        except requests.RequestException as exc:
            raise RuntimeError(f"后端代理连接失败：{exc}") from exc
        data = response.json()
        audio_base64 = data.get("audio_base64")
        audio = base64.b64decode(audio_base64) if audio_base64 else None
        return data["text"].strip(), data["reply"].strip(), audio
