from __future__ import annotations

import base64
import html
import io
import os
import re
import threading
import wave
from collections.abc import Mapping

import requests


DEFAULT_TTS_MODEL = "cosyvoice-v3.5-plus"
DEFAULT_TTS_URL = "wss://dashscope.aliyuncs.com/api-ws/v1/realtime"
DEFAULT_TTS_VOICE = "cosyvoice-v3.5-plus-bailian-7aa8479594894dfca48fb4a6d57cf6bc"


class DashScopeTtsClient:
    def __init__(self) -> None:
        self.api_key = os.getenv("DASHSCOPE_API_KEY", "")
        self.model = os.getenv("DASHSCOPE_TTS_MODEL", DEFAULT_TTS_MODEL)
        self.url = os.getenv("DASHSCOPE_TTS_URL", DEFAULT_TTS_URL)
        self.voice = os.getenv("DASHSCOPE_TTS_VOICE", DEFAULT_TTS_VOICE)
        self.instructions = os.getenv("DASHSCOPE_TTS_INSTRUCTIONS", "").strip()

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    def synthesize_wav(self, text: str) -> bytes:
        if not self.api_key:
            raise RuntimeError("缺少 DASHSCOPE_API_KEY。")
        text = text.strip()
        if not text:
            raise RuntimeError("TTS 文本为空。")
        text = _prepare_spoken_text(text)
        if len(text) > 220:
            text = text[:220].rstrip("，。！？~ ") + "。"

        if self._should_use_cosyvoice_v2():
            return self._synthesize_cosyvoice_v2(text)
        if self._should_use_non_realtime():
            return self._synthesize_non_realtime(text)
        return self._synthesize_realtime(text)

    def _should_use_cosyvoice_v2(self) -> bool:
        return self.model.lower().startswith("cosyvoice-")

    def _should_use_non_realtime(self) -> bool:
        model = self.model.lower()
        return "-vc-" in model or "-vd-" in model

    def _synthesize_non_realtime(self, text: str) -> bytes:
        import dashscope

        dashscope.api_key = self.api_key
        dashscope.base_http_api_url = os.getenv(
            "DASHSCOPE_HTTP_BASE_URL",
            "https://dashscope.aliyuncs.com/api/v1",
        )
        response = dashscope.MultiModalConversation.call(
            model=self.model,
            api_key=self.api_key,
            text=text,
            voice=self.voice,
            language_type="Chinese",
            stream=False,
        )
        data = _dashscope_response_to_dict(response)
        if data.get("status_code") and data.get("status_code") != 200:
            raise RuntimeError(f"DashScope 非实时 TTS 失败：{data}")

        audio_url = _find_audio_url(data)
        if not audio_url:
            raise RuntimeError(f"DashScope 非实时 TTS 未返回音频地址：{data}")

        audio_response = requests.get(audio_url, timeout=60)
        audio_response.raise_for_status()
        return audio_response.content

    def _synthesize_cosyvoice_v2(self, text: str) -> bytes:
        import dashscope
        from dashscope.audio.tts_v2 import SpeechSynthesizer

        dashscope.api_key = self.api_key
        dashscope.base_websocket_api_url = os.getenv(
            "DASHSCOPE_TTS_V2_URL",
            "wss://dashscope.aliyuncs.com/api-ws/v1/inference",
        )
        synthesizer = SpeechSynthesizer(model=self.model, voice=self.voice)
        ssml = _to_cat_arc_ssml(text)
        try:
            audio = synthesizer.call(ssml)
        finally:
            try:
                synthesizer.get_duplex_api().close(1000, "bye")
            except Exception:
                pass
        if not audio:
            raise RuntimeError("CosyVoice TTS 未返回音频。")
        return bytes(audio)

    def _synthesize_realtime(self, text: str) -> bytes:
        import dashscope
        from dashscope.audio.qwen_tts_realtime import (
            AudioFormat,
            QwenTtsRealtime,
            QwenTtsRealtimeCallback,
        )

        dashscope.api_key = self.api_key

        class Callback(QwenTtsRealtimeCallback):
            def __init__(self) -> None:
                super().__init__()
                self.complete_event = threading.Event()
                self.audio = bytearray()
                self.error: Exception | None = None
                self.events: list[str] = []

            def on_close(self, close_status_code, close_msg) -> None:
                self.events.append(f"closed:{close_status_code}:{close_msg}")
                self.complete_event.set()

            def on_event(self, response) -> None:
                try:
                    event_type = response.get("type")
                    if event_type:
                        self.events.append(event_type)
                    if response.get("error"):
                        self.error = RuntimeError(str(response["error"]))
                        self.complete_event.set()
                        return
                    if event_type in {"error", "response.error"}:
                        self.error = RuntimeError(str(response))
                        self.complete_event.set()
                        return
                    if event_type == "response.audio.delta":
                        self.audio.extend(base64.b64decode(response["delta"]))
                    elif event_type in {"response.done", "session.finished"}:
                        self.complete_event.set()
                except Exception as exc:
                    self.error = exc
                    self.complete_event.set()

            def wait_done(self) -> None:
                if not self.complete_event.wait(timeout=60):
                    raise RuntimeError(
                        "DashScope TTS 等待音频超时，已收到事件："
                        + ", ".join(self.events[-8:])
                    )
                if self.error:
                    raise self.error

        callback = Callback()
        qwen_tts = QwenTtsRealtime(
            model=self.model,
            callback=callback,
            url=self.url,
        )
        try:
            qwen_tts.connect()
            session_args = {
                "voice": self.voice,
                "response_format": AudioFormat.PCM_24000HZ_MONO_16BIT,
                "mode": "commit",
            }
            if self.instructions:
                session_args["instructions"] = self.instructions
                session_args["optimize_instructions"] = True
            qwen_tts.update_session(**session_args)
            qwen_tts.append_text(text)
            qwen_tts.commit()
            callback.wait_done()
        finally:
            try:
                qwen_tts.finish()
            except Exception:
                pass

        if not callback.audio:
            events = ", ".join(callback.events[-8:]) or "无事件"
            raise RuntimeError(f"DashScope TTS 未返回音频，已收到事件：{events}")
        return _pcm_24k_mono_16bit_to_wav(bytes(callback.audio))


def _pcm_24k_mono_16bit_to_wav(pcm: bytes) -> bytes:
    output = io.BytesIO()
    with wave.open(output, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(24000)
        wav.writeframes(pcm)
    return output.getvalue()


def _dashscope_response_to_dict(response) -> dict:
    if isinstance(response, Mapping):
        return response
    to_dict = getattr(type(response), "to_dict", None)
    if callable(to_dict):
        return to_dict(response)
    return dict(response)


def _find_audio_url(value) -> str | None:
    if isinstance(value, dict):
        for key in ("audio_url", "url", "audio"):
            item = value.get(key)
            if isinstance(item, str) and item.startswith(("http://", "https://")):
                return item
        for item in value.values():
            found = _find_audio_url(item)
            if found:
                return found
    elif isinstance(value, list):
        for item in value:
            found = _find_audio_url(item)
            if found:
                return found
    return None


def _prepare_spoken_text(text: str) -> str:
    text = text.strip()
    # Do not read stage directions or asides such as "（歪头）" or "(小声)".
    text = re.sub(r"（[^（）]*）", "", text)
    text = re.sub(r"\([^()]*\)", "", text)
    text = re.sub(r"【[^【】]*】", "", text)
    text = re.sub(r"\[[^\[\]]*\]", "", text)
    text = text.replace("~", "～")
    text = re.sub(r"\s+", "，", text)
    text = re.sub(r"，{2,}", "，", text)
    text = text.strip("，。！？、；： ")
    if not text:
        text = "本猫懂了喵。"
    if not text.endswith(("。", "！", "？", "～")):
        text += "喵。"
    return text


def _to_cat_arc_ssml(text: str) -> str:
    text = _prepare_spoken_text(text)
    text = html.escape(text, quote=True)
    text = _add_ssml_breaks(text)
    # A slightly faster and higher voice tends to feel closer to the tiny chaotic
    # desktop-pet tone without relying on stage directions.
    return f'<speak rate="1.18" pitch="1.18" volume="62">{text}</speak>'


def _add_ssml_breaks(text: str) -> str:
    text = re.sub(r"([。！？])", r"\1<break time=\"180ms\"/>", text)
    text = re.sub(r"([，、；])", r"\1<break time=\"80ms\"/>", text)
    text = text.replace("喵。", "喵！<break time=\"120ms\"/>")
    text = text.replace("哼哼", "哼哼<break time=\"90ms\"/>")
    text = text.replace("nya", "nya<break time=\"90ms\"/>")
    return text
