"""Audio I/O helpers: 16 kHz mono float32 everywhere inside the spike."""

from __future__ import annotations

from math import gcd
from pathlib import Path

import numpy as np
import numpy.typing as npt
import soundfile as sf

from semraa_spike.vad import FRAME_SAMPLES, SAMPLE_RATE

Audio = npt.NDArray[np.float32]


def resample(audio: Audio, src_rate: int, dst_rate: int = SAMPLE_RATE) -> Audio:
    if src_rate == dst_rate:
        return audio.astype(np.float32, copy=False)
    from scipy.signal import resample_poly

    g = gcd(src_rate, dst_rate)
    return np.asarray(resample_poly(audio, dst_rate // g, src_rate // g), dtype=np.float32)


def load_wav(path: Path) -> Audio:
    data, rate = sf.read(str(path), dtype="float32", always_2d=True)
    mono = np.asarray(data.mean(axis=1), dtype=np.float32)
    return resample(mono, int(rate))


def save_wav(path: Path, audio: Audio, rate: int = SAMPLE_RATE) -> None:
    sf.write(str(path), audio, rate, subtype="PCM_16")


def frames(audio: Audio, size: int = FRAME_SAMPLES) -> list[Audio]:
    """Split into fixed frames; the last partial frame is zero-padded."""
    n = -(-len(audio) // size)
    padded = np.zeros(n * size, dtype=np.float32)
    padded[: len(audio)] = audio
    return [padded[i * size : (i + 1) * size] for i in range(n)]


def pad_silence(audio: Audio, lead_s: float, tail_s: float, rate: int = SAMPLE_RATE) -> Audio:
    return np.concatenate(
        [np.zeros(int(lead_s * rate), np.float32), audio, np.zeros(int(tail_s * rate), np.float32)]
    )
