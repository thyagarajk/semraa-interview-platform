"""Final (end-of-turn) speech-to-text adapters."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from semraa_spike.audio import Audio


class Stt(Protocol):
    name: str

    def transcribe(self, audio: Audio) -> str: ...


@dataclass(frozen=True)
class WhisperConfig:
    model_dir: Path
    language: str  # "en" or "ta"
    device: str = "cuda"
    compute_type: str = "float16"  # float16 | int8_float16 | int8
    beam_size: int = 1


class WhisperStt:
    """faster-whisper (CTranslate2). Greedy decoding, no previous-text conditioning, our own VAD upstream."""

    def __init__(self, cfg: WhisperConfig) -> None:
        from semraa_spike.cuda import add_nvidia_dll_dirs

        add_nvidia_dll_dirs()
        from faster_whisper import WhisperModel

        self.cfg = cfg
        self.name = f"faster-whisper/{cfg.model_dir.name} ({cfg.device}, {cfg.compute_type})"
        self._model = WhisperModel(str(cfg.model_dir), device=cfg.device, compute_type=cfg.compute_type)

    def transcribe(self, audio: Audio) -> str:
        segments, _info = self._model.transcribe(
            audio,
            language=self.cfg.language,
            beam_size=self.cfg.beam_size,
            temperature=0.0,
            condition_on_previous_text=False,
            vad_filter=False,
            without_timestamps=True,
        )
        return " ".join(s.text.strip() for s in segments).strip()
