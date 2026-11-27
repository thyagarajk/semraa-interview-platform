"""Text-to-speech adapters. Each returns (samples float32, sample_rate) for one sentence."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import numpy as np

from semraa_spike.audio import Audio


class Tts(Protocol):
    name: str

    def synth(self, text: str) -> tuple[Audio, int]: ...


@dataclass(frozen=True)
class KokoroConfig:
    model_path: Path  # kokoro-v1.0.onnx (fp32) or kokoro-v1.0.int8.onnx
    voices_path: Path  # voices-v1.0.bin (NumPy .npz of style vectors, loaded without pickle)
    voice: str = "af_heart"
    speed: float = 1.0
    threads: int = 4


class KokoroTts:
    """Kokoro-82M v1.0 (Apache-2.0) via kokoro-onnx on onnxruntime CPU; espeak-ng G2P handles unknown words.

    (sherpa-onnx 2.x also runs Kokoro, but its v1.0 frontend is lexicon-only and silently drops
    out-of-lexicon words such as "Kubernetes", which rules it out for technical interviews.)
    """

    def __init__(self, cfg: KokoroConfig) -> None:
        import onnxruntime as ort
        from kokoro_onnx import Kokoro

        opts = ort.SessionOptions()
        opts.intra_op_num_threads = cfg.threads
        session = ort.InferenceSession(str(cfg.model_path), opts, providers=["CPUExecutionProvider"])
        self._kokoro = Kokoro.from_session(session, str(cfg.voices_path))
        self._cfg = cfg
        self.name = f"kokoro-v1.0/{cfg.model_path.name} ({cfg.voice}, cpu x{cfg.threads})"

    def synth(self, text: str) -> tuple[Audio, int]:
        samples, rate = self._kokoro.create(text, voice=self._cfg.voice, speed=self._cfg.speed, lang="en-us")
        return np.asarray(samples, dtype=np.float32), int(rate)
