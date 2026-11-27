"""End-of-turn rule on top of Silero VAD frame probabilities.

The rule (pure, unit-tested) is separate from the ONNX model wrapper so it can be tuned without models.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import numpy as np
    import numpy.typing as npt

SAMPLE_RATE = 16_000
FRAME_SAMPLES = 512  # Silero VAD v5 window at 16 kHz = 32 ms


@dataclass(frozen=True)
class EndOfTurnConfig:
    frame_ms: float = FRAME_SAMPLES * 1000 / SAMPLE_RATE
    speech_threshold: float = 0.5  # prob >= this starts / continues speech
    silence_threshold: float = 0.35  # prob < this counts as silence (hysteresis between the two)
    min_speech_ms: float = 250.0  # shorter bursts (coughs, clicks) never open a turn
    end_silence_ms: float = 1800.0  # silence that closes the answer; brief range is 1500-2500

    def __post_init__(self) -> None:
        if not 0.0 < self.silence_threshold <= self.speech_threshold < 1.0:
            raise ValueError("need 0 < silence_threshold <= speech_threshold < 1")
        if self.end_silence_ms <= 0 or self.frame_ms <= 0 or self.min_speech_ms < 0:
            raise ValueError("durations must be positive")


class TurnEventKind(Enum):
    SPEECH_START = "speech_start"
    END_OF_TURN = "end_of_turn"


@dataclass(frozen=True)
class TurnEvent:
    kind: TurnEventKind
    at_ms: float  # stream time when the event was decided (end of the frame that triggered it)
    speech_start_ms: float
    last_speech_end_ms: float  # end of the last voiced frame (== speech end)


class EndOfTurnDetector:
    """Feed one VAD probability per frame; emits SPEECH_START once and END_OF_TURN after enough silence."""

    def __init__(self, config: EndOfTurnConfig | None = None) -> None:
        self.config = config or EndOfTurnConfig()
        self._t = 0.0
        self.reset()

    def reset(self) -> None:
        self._in_speech = False  # inside a voiced stretch
        self._turn_open = False  # speech lasted >= min_speech_ms
        self._speech_ms = 0.0
        self._silence_ms = 0.0
        self._speech_start = 0.0
        self._last_speech_end = 0.0

    @property
    def now_ms(self) -> float:
        return self._t

    def update(self, prob: float) -> TurnEvent | None:
        cfg = self.config
        frame_start = self._t
        self._t += cfg.frame_ms
        voiced = prob >= cfg.speech_threshold or (self._in_speech and prob >= cfg.silence_threshold)

        if voiced:
            if not self._in_speech and self._speech_ms == 0.0:
                self._speech_start = frame_start
            self._in_speech = True
            self._speech_ms += cfg.frame_ms
            self._silence_ms = 0.0
            self._last_speech_end = self._t
            if not self._turn_open and self._speech_ms >= cfg.min_speech_ms:
                self._turn_open = True
                return TurnEvent(
                    TurnEventKind.SPEECH_START, self._t, self._speech_start, self._last_speech_end
                )
            return None

        self._in_speech = False
        if self._speech_ms == 0.0:
            return None
        self._silence_ms += cfg.frame_ms
        if not self._turn_open:
            # A burst too short to count, followed by silence: forget it.
            if self._silence_ms >= cfg.end_silence_ms:
                self.reset()
            return None
        if self._silence_ms >= cfg.end_silence_ms:
            event = TurnEvent(TurnEventKind.END_OF_TURN, self._t, self._speech_start, self._last_speech_end)
            self.reset()
            return event
        return None


class SileroVad:
    """Silero VAD v5 ONNX model (MIT). Returns speech probability per 512-sample frame at 16 kHz."""

    _CONTEXT = 64

    def __init__(self, model_path: Path) -> None:
        import numpy as np
        import onnxruntime as ort

        opts = ort.SessionOptions()
        opts.inter_op_num_threads = 1
        opts.intra_op_num_threads = 1
        self._session = ort.InferenceSession(str(model_path), opts, providers=["CPUExecutionProvider"])
        self._np = np
        self.reset()

    def reset(self) -> None:
        np = self._np
        self._state = np.zeros((2, 1, 128), dtype=np.float32)
        self._context = np.zeros((1, self._CONTEXT), dtype=np.float32)

    def __call__(self, frame: npt.NDArray[np.float32]) -> float:
        np = self._np
        if frame.shape != (FRAME_SAMPLES,):
            raise ValueError(f"frame must have {FRAME_SAMPLES} samples")
        x = np.concatenate([self._context, frame.reshape(1, -1)], axis=1)
        out, self._state = self._session.run(
            None, {"input": x, "state": self._state, "sr": np.array(SAMPLE_RATE, dtype=np.int64)}
        )
        self._context = x[:, -self._CONTEXT :]
        return float(out[0][0])
