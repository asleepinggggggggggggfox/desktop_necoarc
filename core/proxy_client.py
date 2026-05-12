from __future__ import annotations

from pathlib import Path

import requests

from core.config import AppConfig


class ProxyClient:
    def __init__(self, config: AppConfig):
        self.config = config

    def voice_chat(self, wav_path: Path) -> tuple[str, str]:
        if not self.config.proxy_base_url:
            raise RuntimeError("缺少后端代理地址，请在 config.yaml 设置 proxy_base_url。")

        url = self.config.proxy_base_url.rstrip("/") + "/v1/voice-chat"
        with wav_path.open("rb") as audio:
            response = requests.post(
                url,
                files={"audio": (wav_path.name, audio, "audio/wav")},
                timeout=90,
            )
        response.raise_for_status()
        data = response.json()
        return data["text"].strip(), data["reply"].strip()
