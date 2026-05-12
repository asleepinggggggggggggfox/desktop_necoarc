from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


@dataclass
class AppConfig:
    window_width: int = 1000
    window_height: int = 520
    always_on_top: bool = True
    character_image: str = "assets/character.png"
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"
    deepseek_api_key: str = ""
    xunfei_iat_url: str = "wss://iat-api.xfyun.cn/v2/iat"
    xunfei_app_id: str = ""
    xunfei_api_key: str = ""
    xunfei_api_secret: str = ""
    xunfei_language: str = "zh_cn"
    xunfei_accent: str = "mandarin"
    sample_rate: int = 16000
    temp_dir: str = "temp"


def load_config() -> AppConfig:
    values = _read_simple_yaml(ROOT / "config.yaml")
    secrets = _read_api_md(ROOT / "plan" / "api.md")
    cfg = AppConfig()

    for field in cfg.__dataclass_fields__:
        if field in values:
            setattr(cfg, field, _coerce(values[field], getattr(cfg, field)))

    cfg.deepseek_api_key = (
        os.getenv("DEEPSEEK_API_KEY")
        or secrets.get("deepseek_api_key", "")
        or cfg.deepseek_api_key
    )
    cfg.xunfei_app_id = (
        os.getenv("XUNFEI_APP_ID")
        or secrets.get("xunfei_app_id", "")
        or cfg.xunfei_app_id
    )
    cfg.xunfei_api_key = (
        os.getenv("XUNFEI_API_KEY")
        or secrets.get("xunfei_api_key", "")
        or cfg.xunfei_api_key
    )
    cfg.xunfei_api_secret = (
        os.getenv("XUNFEI_API_SECRET")
        or secrets.get("xunfei_api_secret", "")
        or cfg.xunfei_api_secret
    )
    return cfg


def _read_simple_yaml(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    data: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        data[key.strip()] = value.strip().strip('"').strip("'")
    return data


def _read_api_md(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8", errors="ignore")
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    result: dict[str, str] = {}
    section = ""

    for index, line in enumerate(lines):
        low = line.lower()
        if "deepseek" in low:
            section = "deepseek"
            continue
        if "讯飞" in line or "xunfei" in low:
            section = "xunfei"
            continue

        next_value = lines[index + 1].strip() if index + 1 < len(lines) else ""
        if section == "xunfei":
            if low == "appid" and next_value:
                result["xunfei_app_id"] = next_value
            elif low == "apikey" and next_value:
                result["xunfei_api_key"] = next_value
            elif low == "apisecret" and next_value:
                result["xunfei_api_secret"] = next_value
        elif section == "deepseek" and line.startswith("sk-"):
            result["deepseek_api_key"] = line

    return result


def _coerce(value: str, current):
    if isinstance(current, bool):
        return value.lower() in {"1", "true", "yes", "on"}
    if isinstance(current, int):
        try:
            return int(value)
        except ValueError:
            return current
    return value

