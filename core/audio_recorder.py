from __future__ import annotations

from pathlib import Path
from time import strftime

import numpy as np
import sounddevice as sd
import soundfile as sf

from core.config import AppConfig, ROOT


class AudioRecorder:
    def __init__(self, config: AppConfig):
        self.config = config
        self._stream: sd.InputStream | None = None
        self._chunks: list[np.ndarray] = []
        self._channels = 1

    @property
    def is_recording(self) -> bool:
        return self._stream is not None

    def start(self) -> None:
        self.reset()
        self._chunks = []
        self._stream = sd.InputStream(
            samplerate=self.config.sample_rate,
            channels=self._channels,
            dtype="int16",
            callback=self._callback,
        )
        self._stream.start()

    def stop(self) -> Path:
        if self._stream is None:
            raise RuntimeError("录音尚未开始。")
        try:
            self._stream.stop()
            self._stream.close()
        finally:
            self._stream = None

        if not self._chunks:
            raise RuntimeError("没有检测到有效语音，请重试。")

        audio = np.concatenate(self._chunks, axis=0)
        if audio.size == 0 or np.max(np.abs(audio)) < 20:
            raise RuntimeError("没有检测到有效语音，请重试。")

        temp_dir = ROOT / self.config.temp_dir
        temp_dir.mkdir(parents=True, exist_ok=True)
        path = temp_dir / f"recording_{strftime('%Y%m%d_%H%M%S')}.wav"
        sf.write(path, audio, self.config.sample_rate, subtype="PCM_16")
        return path

    def reset(self) -> None:
        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            finally:
                self._stream = None
        self._chunks = []

    def _callback(self, indata, frames, time, status) -> None:
        if status:
            pass
        self._chunks.append(indata.copy())
