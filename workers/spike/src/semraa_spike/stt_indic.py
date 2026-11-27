"""AI4Bharat IndicConformer 600M multilingual (MIT, ONNX export) for Tamil final transcription.

The model repo is gated on Hugging Face; its ONNX graphs are run directly with onnxruntime here
(no `trust_remote_code`, no NeMo, no pickle checkpoints).
"""

from __future__ import annotations

from pathlib import Path

from semraa_spike.audio import Audio


class IndicConformerStt:
    def __init__(self, model_dir: Path, language: str = "ta") -> None:
        if not (model_dir / "assets" / "encoder.onnx").exists():
            raise FileNotFoundError(f"IndicConformer ONNX assets missing in {model_dir}")
        self.language = language
        self.name = f"indic-conformer-600m ({language})"
        raise NotImplementedError("IndicConformer adapter lands once the gated model files can be inspected")

    def transcribe(self, audio: Audio) -> str:
        raise NotImplementedError
