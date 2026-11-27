"""Pinned model registry and downloader.

Every model is pinned by exact revision (Hugging Face commit) or exact release asset + SHA-256.
Formats are ONNX, CTranslate2, safetensors or GGUF (via Ollama) only - no pickle checkpoints.
"""

from __future__ import annotations

import hashlib
import os
import tarfile
from dataclasses import dataclass
from pathlib import Path

MODELS_DIR = Path(os.environ.get("SEMRAA_SPIKE_MODELS", Path(__file__).resolve().parents[2] / ".models"))


@dataclass(frozen=True)
class HfModel:
    key: str
    repo: str
    revision: str
    licence: str
    note: str = ""
    gated: bool = False
    allow_patterns: tuple[str, ...] = ()

    @property
    def path(self) -> Path:
        return MODELS_DIR / self.key


@dataclass(frozen=True)
class UrlModel:
    key: str
    url: str
    sha256: str
    licence: str
    note: str = ""
    archive: bool = False  # .tar.bz2 to extract

    @property
    def path(self) -> Path:
        return MODELS_DIR / self.key


_SHERPA = "https://github.com/k2-fsa/sherpa-onnx/releases/download"

WHISPER_TURBO = HfModel(
    "faster-whisper-large-v3-turbo",
    "mobiuslabsgmbh/faster-whisper-large-v3-turbo",
    "0a363e9161cbc7ed1431c9597a8ceaf0c4f78fcf",
    "MIT",
    "CTranslate2 conversion of openai/whisper-large-v3-turbo",
)
WHISPER_MEDIUM = HfModel(
    "faster-whisper-medium",
    "Systran/faster-whisper-medium",
    "08e178d48790749d25932bbc082711ddcfdfbc4f",
    "MIT",
)
WHISPER_SMALL = HfModel(
    "faster-whisper-small",
    "Systran/faster-whisper-small",
    "536b0662742c02347bc0e980a01041f333bce120",
    "MIT",
)
INDIC_CONFORMER = HfModel(
    "indic-conformer-600m",
    "ai4bharat/indic-conformer-600m-multilingual",
    "2a77d305038dfc502fd9464e7d028b90381976cb",
    "MIT",
    "ONNX export; gated on Hugging Face (accept terms, set HF_TOKEN)",
    gated=True,
)
INDIC_PARLER = HfModel(
    "indic-parler-tts",
    "ai4bharat/indic-parler-tts",
    "660bc53c64ae83150613264111708a0465211237",
    "Apache-2.0",
    "safetensors; gated on Hugging Face (accept terms, set HF_TOKEN)",
    gated=True,
)
SILERO_VAD = UrlModel(
    "silero_vad.onnx",
    "https://raw.githubusercontent.com/snakers4/silero-vad/v6.2.3/src/silero_vad/data/silero_vad.onnx",
    "1a153a22f4509e292a94e67d6f9b85e8deb25b4988682b7e174c65279d8788e3",
    "MIT",
    "Silero VAD v6.2.3",
)
_KOKORO_ONNX = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0"
KOKORO_ONNX = UrlModel(
    "kokoro-onnx-v1.0/kokoro-v1.0.onnx",
    f"{_KOKORO_ONNX}/kokoro-v1.0.onnx",
    "7d5df8ecf7d4b1878015a32686053fd0eebe2bc377234608764cc0ef3636a6c5",
    "Apache-2.0",
    "hexgrad/Kokoro-82M v1.0, ONNX export by kokoro-onnx (fp32)",
)
KOKORO_ONNX_INT8 = UrlModel(
    "kokoro-onnx-v1.0/kokoro-v1.0.int8.onnx",
    f"{_KOKORO_ONNX}/kokoro-v1.0.int8.onnx",
    "6e742170d309016e5891a994e1ce1559c702a2ccd0075e67ef7157974f6406cb",
    "Apache-2.0",
    "hexgrad/Kokoro-82M v1.0, int8-quantised ONNX",
)
KOKORO_VOICES = UrlModel(
    "kokoro-onnx-v1.0/voices-v1.0.bin",
    f"{_KOKORO_ONNX}/voices-v1.0.bin",
    "bca610b8308e8d99f32e6fe4197e7ec01679264efed0cac9140fe9c29f1fbf7d",
    "Apache-2.0",
    "Kokoro v1.0 voice style vectors (.npz of float arrays, loaded with allow_pickle=False)",
)
CAPTIONS_EN = UrlModel(
    "sherpa-onnx-streaming-zipformer-en-2023-06-26",
    f"{_SHERPA}/asr-models/sherpa-onnx-streaming-zipformer-en-2023-06-26.tar.bz2",
    "639e25b578e9e997131402199419c13a941f8e4e198e2da1ce57dbf5cf401282",
    "Apache-2.0",
    "icefall streaming Zipformer transducer (LibriSpeech + GigaSpeech)",
    archive=True,
)

ALL_MODELS: tuple[HfModel | UrlModel, ...] = (
    SILERO_VAD,
    WHISPER_TURBO,
    WHISPER_MEDIUM,
    WHISPER_SMALL,
    KOKORO_ONNX,
    KOKORO_ONNX_INT8,
    KOKORO_VOICES,
    CAPTIONS_EN,
    INDIC_CONFORMER,
    INDIC_PARLER,
)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _download_url(model: UrlModel) -> None:
    import httpx

    model.path.parent.mkdir(parents=True, exist_ok=True)
    tmp = MODELS_DIR / (model.key + (".tar.bz2" if model.archive else "") + ".part")
    with httpx.stream("GET", model.url, follow_redirects=True, timeout=60.0) as r:
        r.raise_for_status()
        with tmp.open("wb") as f:
            for chunk in r.iter_bytes(1 << 20):
                f.write(chunk)
    digest = sha256_file(tmp)
    if model.sha256 and digest != model.sha256:
        tmp.unlink()
        raise RuntimeError(f"{model.key}: SHA-256 mismatch (got {digest})")
    if not model.sha256:
        print(f"  {model.key}: sha256 {digest} (not pinned yet - pin it in models.py)")
    if model.archive:
        with tarfile.open(tmp, "r:bz2") as tar:
            tar.extractall(MODELS_DIR, filter="data")  # 'data' filter blocks path traversal and links out
        tmp.unlink()
    else:
        tmp.replace(model.path)


def _download_hf(model: HfModel) -> None:
    from huggingface_hub import snapshot_download

    snapshot_download(
        repo_id=model.repo,
        revision=model.revision,
        local_dir=model.path,
        allow_patterns=list(model.allow_patterns) or None,
    )


def is_present(model: HfModel | UrlModel) -> bool:
    return model.path.exists()


def ensure(model: HfModel | UrlModel) -> Path:
    if not is_present(model):
        if isinstance(model, HfModel) and model.gated and not os.environ.get("HF_TOKEN"):
            raise PermissionError(f"{model.repo} is gated: accept its terms on Hugging Face and set HF_TOKEN")
        print(f"downloading {model.key} ...")
        if isinstance(model, HfModel):
            _download_hf(model)
        else:
            _download_url(model)
    return model.path
