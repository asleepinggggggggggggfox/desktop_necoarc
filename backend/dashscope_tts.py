from __future__ import annotations

import base64
import io
import os
import threading
import wave


DEFAULT_TTS_MODEL = "qwen3-tts-flash-realtime"
DEFAULT_TTS_URL = "wss://dashscope.aliyuncs.com/api-ws/v1/realtime"
DEFAULT_TTS_VOICE = "Cherry"


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
        if len(text) > 220:
            text = text[:220].rstrip() + "。"

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

            def on_event(self, response) -> None:
                try:
                    event_type = response.get("type")
                    if event_type == "response.audio.delta":
                        self.audio.extend(base64.b64decode(response["delta"]))
                    elif event_type in {"response.done", "session.finished"}:
                        self.complete_event.set()
                except Exception as exc:
                    self.error = exc
                    self.complete_event.set()

            def wait_done(self) -> None:
                self.complete_event.wait(timeout=60)
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
            raise RuntimeError("DashScope TTS 未返回音频。")
        return _pcm_24k_mono_16bit_to_wav(bytes(callback.audio))


def _pcm_24k_mono_16bit_to_wav(pcm: bytes) -> bytes:
    output = io.BytesIO()
    with wave.open(output, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(24000)
        wav.writeframes(pcm)
    return output.getvalue()
