from __future__ import annotations

import io

import sounddevice as sd
import soundfile as sf


class AudioPlayer:
    def play_wav_bytes(self, audio: bytes) -> None:
        if not audio:
            return
        data, sample_rate = sf.read(io.BytesIO(audio), dtype="float32")
        sd.play(data, sample_rate)
        sd.wait()
