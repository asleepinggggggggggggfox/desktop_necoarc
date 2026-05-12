from __future__ import annotations

import requests

from core.config import AppConfig


class DeepSeekClient:
    def __init__(self, config: AppConfig):
        self.config = config

    def chat(self, user_text: str) -> str:
        if not self.config.deepseek_api_key:
            raise RuntimeError("缺少 DeepSeek API Key，请检查 plan/api.md 或环境变量。")

        url = self.config.deepseek_base_url.rstrip("/") + "/chat/completions"
        payload = {
            "model": self.config.deepseek_model,
            "messages": [
                {
                    "role": "system",
                    "content": "你是一个简洁、友好的桌面宠物助手。回答要自然，尽量短一点。",
                },
                {"role": "user", "content": user_text},
            ],
            "temperature": 0.7,
        }
        headers = {
            "Authorization": f"Bearer {self.config.deepseek_api_key}",
            "Content-Type": "application/json",
        }
        response = requests.post(url, json=payload, headers=headers, timeout=45)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()

