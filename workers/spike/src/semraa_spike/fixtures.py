"""Synthetic interview-answer fixtures (no personal data): reference texts in fixtures/<lang>.jsonl,
audio rendered to fixtures/audio/<id>.wav (16 kHz mono, 0.5 s lead, 3 s trailing silence for the VAD).

English audio comes from built-in Windows OneCore voices (incl. Indian English Ravi / Heera), so the STT is
not scored on the same TTS the spike uses. Tamil audio comes from Indic Parler-TTS (two named speakers).
Self-recorded audio can replace any file: keep the same id and 16 kHz mono WAV.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from semraa_spike.audio import load_wav, pad_silence, resample, save_wav

FIXTURES_DIR = Path(__file__).resolve().parents[2] / "fixtures"
AUDIO_DIR = FIXTURES_DIR / "audio"
SCRIPTS_DIR = Path(__file__).resolve().parents[2] / "scripts"
LEAD_S = 0.5
TAIL_S = 3.0


@dataclass(frozen=True)
class Fixture:
    id: str
    lang: str
    voice: str
    question: str
    text: str

    @property
    def audio_path(self) -> Path:
        return AUDIO_DIR / f"{self.id}.wav"


def load_fixtures(lang: str) -> list[Fixture]:
    lines = (FIXTURES_DIR / f"{lang}.jsonl").read_text(encoding="utf-8").splitlines()
    return [Fixture(lang=lang, **json.loads(line)) for line in lines if line.strip()]


def make_english(fixtures: list[Fixture], overwrite: bool = False) -> None:
    if sys.platform != "win32":
        raise RuntimeError("English fixture voices use Windows OneCore TTS; record WAVs manually elsewhere")
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    script = SCRIPTS_DIR / "sapi_tts.ps1"
    for fx in fixtures:
        if fx.audio_path.exists() and not overwrite:
            continue
        with tempfile.TemporaryDirectory() as tmp:
            raw = Path(tmp) / "raw.wav"
            args = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script),
                    "-Voice", fx.voice, "-Text", fx.text, "-Out", str(raw)]  # fmt: skip
            # Fixed local script and Windows PowerShell from PATH; no shell, texts come from our fixtures.
            subprocess.run(args, check=True, capture_output=True)  # noqa: S603
            audio = load_wav(raw)
        save_wav(fx.audio_path, pad_silence(audio, LEAD_S, TAIL_S))
        print(f"  {fx.id}: {fx.voice}")


def make_tamil(fixtures: list[Fixture], overwrite: bool = False) -> None:
    from semraa_spike import models
    from semraa_spike.tts_parler import ParlerConfig, ParlerTts

    pending = [fx for fx in fixtures if overwrite or not fx.audio_path.exists()]
    if not pending:
        return
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    tts = ParlerTts(ParlerConfig(model_dir=models.ensure(models.INDIC_PARLER)))
    for fx in pending:
        audio, rate = tts.synth(fx.text, speaker=fx.voice)
        save_wav(fx.audio_path, pad_silence(resample(audio, rate), LEAD_S, TAIL_S))
        print(f"  {fx.id}: {fx.voice}")
