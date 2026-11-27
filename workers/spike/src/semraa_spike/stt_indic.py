"""AI4Bharat IndicConformer 600M multilingual (MIT) for Tamil final transcription, run directly on ONNX.

The upstream wrapper needs `trust_remote_code` and loads a TorchScript preprocessor (pickle-based). Instead:
- the log-mel front end is re-implemented in NumPy from the TorchScript graph's source (pre-emphasis 0.97,
  reflect pad 256, 512-point STFT, hop 160, 400-sample window, 80 mels, log(x + 2^-24), per-feature
  normalisation), and its window and mel filterbank are read as raw float32 tensors from the archive;
- the encoder and CTC head run in onnxruntime; greedy CTC over the Tamil vocabulary mask.
Nothing is unpickled and no downloaded Python code is executed.
"""

from __future__ import annotations

import json
import zipfile
from pathlib import Path
from typing import Any

import numpy as np
import numpy.typing as npt

from semraa_spike.audio import Audio

N_FFT = 512
HOP = 160
WIN = 400
N_MELS = 80
PREEMPH = 0.97
LOG_GUARD = 5.960464477539063e-08  # 2**-24
STD_EPS = 1e-5
BLANK_ID = 256

_TS_PREFIX = "preprocessor/constants/"


def _ts_tensor(archive: Path, index: int, shape: tuple[int, ...]) -> npt.NDArray[np.float32]:
    """Read a raw little-endian float32 constant from a TorchScript zip without unpickling anything."""
    with zipfile.ZipFile(archive) as z:
        raw = z.read(f"{_TS_PREFIX}{index}")
    arr = np.frombuffer(raw, dtype="<f4")
    if arr.size != int(np.prod(shape)):
        raise ValueError(f"constant {index}: expected {shape}, got {arr.size} values")
    return arr.reshape(shape).astype(np.float32)


class LogMel:
    def __init__(self, preprocessor_ts: Path) -> None:
        window = _ts_tensor(preprocessor_ts, 3, (WIN,))
        pad = (N_FFT - WIN) // 2
        self.window = np.zeros(N_FFT, dtype=np.float32)
        self.window[pad : pad + WIN] = window
        self.filterbank = _ts_tensor(preprocessor_ts, 4, (N_FFT // 2 + 1, N_MELS))

    def __call__(self, audio: Audio) -> tuple[npt.NDArray[np.float32], int]:
        prev = np.concatenate([np.zeros(1, np.float32), audio[:-1].astype(np.float32)])
        x = (audio.astype(np.float32) - np.float32(PREEMPH) * prev).astype(np.float32)
        xp = np.pad(x, N_FFT // 2, mode="reflect")
        n_frames = 1 + (len(xp) - N_FFT) // HOP
        frames = np.lib.stride_tricks.sliding_window_view(xp, N_FFT)[::HOP][:n_frames] * self.window
        power = np.abs(np.fft.rfft(frames, n=N_FFT, axis=-1)) ** 2
        feats = np.log(power.astype(np.float32) @ self.filterbank + LOG_GUARD).T  # (80, T)
        length = len(x) // HOP + 1
        valid = feats[:, :length]
        mean = valid.mean(axis=1, keepdims=True)
        var = ((valid - mean) ** 2).sum(axis=1, keepdims=True) / max(length - 1, 1)
        std = np.sqrt(np.maximum(var, LOG_GUARD))
        out = (feats - mean) / (std + STD_EPS)
        out[:, length:] = 0.0
        return out[np.newaxis].astype(np.float32), length


class IndicConformerStt:
    def __init__(self, model_dir: Path, language: str = "ta", provider: str = "CPUExecutionProvider") -> None:
        import onnxruntime as ort

        assets = model_dir / "assets"
        if not (assets / "encoder.onnx").exists():
            raise FileNotFoundError(f"IndicConformer ONNX assets missing in {model_dir}")
        self.language = language
        self._mel = LogMel(assets / "preprocessor.ts")
        opts = ort.SessionOptions()
        self._encoder: Any = ort.InferenceSession(str(assets / "encoder.onnx"), opts, providers=[provider])
        self._ctc: Any = ort.InferenceSession(str(assets / "ctc_decoder.onnx"), opts, providers=[provider])
        masks = json.loads((assets / "language_masks.json").read_text(encoding="utf-8"))
        self._mask = np.asarray(masks[language], dtype=bool)
        self._vocab: list[str] = json.loads((assets / "vocab.json").read_text(encoding="utf-8"))[language]
        self.name = f"indic-conformer-600m ({language}, ctc, {provider.replace('ExecutionProvider', '')})"

    def transcribe(self, audio: Audio) -> str:
        feats, length = self._mel(audio)
        enc, _enc_len = self._encoder.run(
            ["outputs", "encoded_lengths"], {"audio_signal": feats, "length": np.array([length], np.int64)}
        )
        logits = self._ctc.run(["logprobs"], {"encoder_output": enc})[0][0][:, self._mask]
        return ctc_greedy(logits.argmax(axis=-1).tolist(), self._vocab)


def ctc_greedy(path: list[int], vocab: list[str], blank: int = BLANK_ID) -> str:
    """Collapse repeats, drop blanks, join SentencePiece pieces ('▁' marks a word start)."""
    out: list[str] = []
    prev = None
    for tok in path:
        if tok != prev and tok != blank:
            out.append(vocab[tok])
        prev = tok
    return "".join(out).replace("▁", " ").strip()
