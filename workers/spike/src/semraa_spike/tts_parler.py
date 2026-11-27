"""Indic Parler-TTS (Apache-2.0, safetensors) for Tamil. Needs the `tamil` extra (PyTorch + parler-tts)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from semraa_spike.audio import Audio

DESCRIPTION = (
    "{speaker} speaks at a moderate pace with a clear, close-sounding voice. "
    "The recording is of very high quality with no background noise."
)


@dataclass(frozen=True)
class ParlerConfig:
    model_dir: Path
    speaker: str = "Jaya"  # recommended Tamil speakers: Jaya, Kavitha
    device: str = "cuda"
    seed: int = 42


class ParlerTts:
    def __init__(self, cfg: ParlerConfig) -> None:
        import torch
        from parler_tts import ParlerTTSForConditionalGeneration
        from transformers import AutoTokenizer

        self._torch: Any = torch
        self.cfg = cfg
        dtype = torch.float16 if cfg.device.startswith("cuda") else torch.float32
        self._model: Any = ParlerTTSForConditionalGeneration.from_pretrained(
            str(cfg.model_dir), torch_dtype=dtype, use_safetensors=True
        ).to(cfg.device)
        self._tok: Any = AutoTokenizer.from_pretrained(str(cfg.model_dir))
        self._desc_tok: Any = AutoTokenizer.from_pretrained(self._model.config.text_encoder._name_or_path)
        self.rate = int(self._model.config.sampling_rate)
        self.name = f"indic-parler-tts ({cfg.device}, {dtype})"

    def synth(self, text: str, speaker: str | None = None) -> tuple[Audio, int]:
        torch = self._torch
        desc = DESCRIPTION.format(speaker=speaker or self.cfg.speaker)
        torch.manual_seed(self.cfg.seed)
        d = self._desc_tok(desc, return_tensors="pt").to(self.cfg.device)
        p = self._tok(text, return_tensors="pt").to(self.cfg.device)
        with torch.inference_mode():
            out = self._model.generate(
                input_ids=d.input_ids,
                attention_mask=d.attention_mask,
                prompt_input_ids=p.input_ids,
                prompt_attention_mask=p.attention_mask,
            )
        return np.asarray(out.to(torch.float32).cpu().numpy().squeeze(), dtype=np.float32), self.rate


class ParlerSentenceTts:
    """Adapter to the pipeline's Tts protocol (fixed speaker)."""

    def __init__(self, inner: ParlerTts, speaker: str = "Jaya") -> None:
        self._inner = inner
        self._speaker = speaker
        self.name = inner.name

    def synth(self, text: str) -> tuple[Audio, int]:
        return self._inner.synth(text, speaker=self._speaker)
