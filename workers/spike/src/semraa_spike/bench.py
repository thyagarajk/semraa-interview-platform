"""Benchmarks: STT accuracy/latency, LLM sizing, full turn latency per language, caption delay, VRAM.

Results are written as JSON (machine-readable, for the re-run on the GPU machine) plus a Markdown summary.
Only synthetic fixture texts appear in results; nothing is logged.
"""

from __future__ import annotations

import gc
import json
import platform
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any

from semraa_spike import models
from semraa_spike.audio import load_wav
from semraa_spike.fixtures import Fixture, load_fixtures
from semraa_spike.gpu import GpuMemorySampler
from semraa_spike.llm import OllamaClient, load_prompt, user_message
from semraa_spike.stt import Stt, WhisperConfig, WhisperStt
from semraa_spike.timing import Clock, summarize
from semraa_spike.tts import KokoroConfig, KokoroTts, Tts
from semraa_spike.vad import EndOfTurnConfig, SileroVad
from semraa_spike.wer import error_rates

RESULTS_DIR = Path(__file__).resolve().parents[2] / "results"


def _available(fixtures: list[Fixture]) -> list[Fixture]:
    return [f for f in fixtures if f.audio_path.exists()]


def _summary(turns: list[dict[str, float | None]]) -> dict[str, Any]:
    return {k: asdict(v) for k, v in summarize(turns).items()}


def machine_info() -> dict[str, Any]:
    info: dict[str, Any] = {"platform": platform.platform(), "python": platform.python_version()}
    try:
        with GpuMemorySampler() as g:
            info["gpu"] = g.name
            info["gpu_total_mb"] = round(g.total_mb)
    except Exception as exc:  # no NVIDIA GPU / driver
        info["gpu"] = f"unavailable ({exc})"
    return info


def load_stt(lang: str, variant: str) -> Stt:
    """variant: turbo-fp16 | turbo-int8 | medium-int8 | small-int8 | indic-conformer"""
    if variant == "indic-conformer":
        from semraa_spike.stt_indic import IndicConformerStt

        stt: Stt = IndicConformerStt(models.ensure(models.INDIC_CONFORMER), language=lang)
        return stt
    size, compute = variant.split("-")
    whisper = {"turbo": models.WHISPER_TURBO, "medium": models.WHISPER_MEDIUM, "small": models.WHISPER_SMALL}
    model = whisper[size]
    compute_type = {"fp16": "float16", "int8": "int8_float16"}[compute]
    return WhisperStt(WhisperConfig(models.ensure(model), language=lang, compute_type=compute_type))


def load_tts(lang: str, int8_tts: bool = False) -> Tts:
    if lang == "ta":
        from semraa_spike.tts_parler import ParlerConfig, ParlerSentenceTts, ParlerTts

        return ParlerSentenceTts(ParlerTts(ParlerConfig(models.ensure(models.INDIC_PARLER))), "Kavitha")
    model = models.KOKORO_ONNX_INT8 if int8_tts else models.KOKORO_ONNX
    return KokoroTts(KokoroConfig(models.ensure(model), models.ensure(models.KOKORO_VOICES)))


def bench_stt(lang: str, variant: str, fixtures: list[Fixture]) -> dict[str, Any]:
    clock = Clock()
    audios = [load_wav(f.audio_path) for f in fixtures]
    with GpuMemorySampler() as gpu:
        stt = load_stt(lang, variant)
        stt.transcribe(audios[0])  # warm-up (CUDA kernels, allocator)
        hyps: list[str] = []
        lat: list[dict[str, float | None]] = []
        for audio in audios:
            t0 = clock.now_ms()
            hyps.append(stt.transcribe(audio))
            lat.append({"stt_final_ms": clock.now_ms() - t0})
        peak = gpu.peak_mb - gpu.start_mb
    rates = error_rates([f.text for f in fixtures], hyps)
    name = stt.name
    del stt
    gc.collect()
    return {
        "lang": lang,
        "variant": variant,
        "model": name,
        "wer": rates.wer,
        "cer": rates.cer,
        "n": rates.n_utterances,
        "ref_words": rates.ref_words,
        "latency": _summary(lat),
        "vram_mb": round(peak),
        "hypotheses": {f.id: h for f, h in zip(fixtures, hyps, strict=True)},
    }


def bench_llm(model: str, fixtures: list[Fixture], lang: str, num_gpu: int | None = None) -> dict[str, Any]:
    client = OllamaClient()
    prompt = load_prompt(language=lang)
    for m in client.ps():
        client.unload(m["name"])
    time.sleep(1.0)
    with GpuMemorySampler() as gpu:
        client.load(model, num_ctx=4096, num_gpu=num_gpu)
        loaded = next((m for m in client.ps() if m["name"] == model), {})
        client.chat(model, prompt, user_message(fixtures[0].question, fixtures[0].text), num_gpu=num_gpu)
        turns: list[dict[str, float | None]] = []
        valid = 0
        tps: list[float] = []
        replies: dict[str, str] = {}
        for f in fixtures:
            r = client.chat(model, prompt, user_message(f.question, f.text), num_gpu=num_gpu)
            turns.append({"llm_first_token_ms": r.first_token_ms, "llm_full_ms": r.full_ms})
            valid += int(r.parsed is not None)
            tps.append(r.eval_tokens_per_s)
            replies[f.id] = r.reply
        peak = gpu.peak_mb - gpu.start_mb
    details = client.show(model).get("details", {})
    client.close()
    size = float(loaded.get("size", 0))
    size_vram = float(loaded.get("size_vram", 0))
    return {
        "model": model,
        "lang": lang,
        "quant": details.get("quantization_level"),
        "params": details.get("parameter_size"),
        "num_gpu": num_gpu,
        "loaded_mb": round(size / 2**20),
        "gpu_share": round(size_vram / size, 3) if size else None,
        "latency": _summary(turns),
        "tokens_per_s_mean": sum(tps) / len(tps),
        "json_valid": f"{valid}/{len(fixtures)}",
        "vram_mb": round(peak),
        "replies": replies,
    }


def bench_pipeline(
    lang: str, llm_model: str, stt_variant: str, fixtures: list[Fixture], repeats: int, eot: EndOfTurnConfig
) -> dict[str, Any]:
    from semraa_spike.pipeline import Components, run_turn

    client = OllamaClient()
    for m in client.ps():
        if m["name"] != llm_model:
            client.unload(m["name"])
    audios = [load_wav(f.audio_path) for f in fixtures]
    with GpuMemorySampler() as gpu:
        # Load order matters on a small GPU: STT + TTS first, then the LLM takes what is left.
        stt = load_stt(lang, stt_variant)
        tts = load_tts(lang)
        client.load(llm_model, num_ctx=4096)
        comp = Components(
            vad=SileroVad(models.ensure(models.SILERO_VAD)),
            eot=eot,
            stt=stt,
            llm=client,
            llm_model=llm_model,
            prompt=load_prompt(language=lang),
            tts=tts,
        )
        run_turn(comp, audios[0], fixtures[0].question)  # warm-up, not counted
        loaded = next((m for m in client.ps() if m["name"] == llm_model), {})
        turns: list[dict[str, float | None]] = []
        hyps: dict[str, str] = {}
        json_ok = 0
        closed = 0
        for rep in range(repeats):
            for f, audio in zip(fixtures, audios, strict=True):
                r = run_turn(comp, audio, f.question)
                turns.append(r.timings)
                json_ok += int(r.llm_json_valid)
                closed += int(bool(r.extra.get("closed_by_silence")))
                if rep == 0:
                    hyps[f.id] = r.transcript
        peak = gpu.peak_mb
        total = gpu.total_mb
    client.close()
    names = {"stt": stt.name, "tts": tts.name}
    del comp, stt, tts
    gc.collect()
    rates = error_rates([f.text for f in fixtures], [hyps[f.id] for f in fixtures])
    size = float(loaded.get("size", 0))
    return {
        "lang": lang,
        "llm": llm_model,
        "stt_variant": stt_variant,
        **names,
        "eot_silence_ms": eot.end_silence_ms,
        "turns": len(turns),
        "eot_closed_by_silence": f"{closed}/{len(turns)}",
        "json_valid": f"{json_ok}/{len(turns)}",
        "llm_gpu_share": round(float(loaded.get("size_vram", 0)) / size, 3) if size else None,
        "latency": _summary(turns),
        "wer": rates.wer,
        "cer": rates.cer,
        "gpu_peak_used_mb": round(peak),
        "gpu_total_mb": round(total),
    }


def bench_captions(fixtures: list[Fixture], chunk_ms: float = 100.0) -> dict[str, Any]:
    from semraa_spike.captions import StreamingCaptioner

    cap = StreamingCaptioner(models.ensure(models.CAPTIONS_EN))
    delays: list[float] = []
    compute: list[float] = []
    hyps: list[str] = []
    for f in fixtures:
        run = cap.run(load_wav(f.audio_path), chunk_ms=chunk_ms)
        delays += run.token_delays_ms
        compute += run.chunk_compute_ms
        hyps.append(run.text)
    rates = error_rates([f.text for f in fixtures], hyps)
    return {
        "model": cap.name,
        "chunk_ms": chunk_ms,
        "partial_delay": _summary([{"caption_partial_delay_ms": d} for d in delays]),
        "chunk_compute": _summary([{"chunk_compute_ms": c} for c in compute]),
        "wer": rates.wer,
    }


def write_results(results: dict[str, Any], out_dir: Path = RESULTS_DIR) -> Path:
    from semraa_spike.report import to_markdown

    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    path = out_dir / f"{stamp}.json"
    path.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    (out_dir / "latest.json").write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    (out_dir / "latest.md").write_text(to_markdown(results), encoding="utf-8")
    return path


def fixtures_for(lang: str) -> list[Fixture]:
    return _available(load_fixtures(lang))
