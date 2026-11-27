"""Render benchmark JSON as Markdown tables (pasted into docs/spikes/M1-voice-spike.md)."""

from __future__ import annotations

from typing import Any

from semraa_spike.timing import STAGES

LABELS = {
    "vad_detect_ms": "VAD end-of-turn (incl. silence wait)",
    "stt_final_ms": "STT final",
    "llm_first_token_ms": "LLM first token",
    "llm_full_ms": "LLM full reply",
    "tts_first_audio_ms": "TTS first sentence",
    "eot_to_first_audio_ms": "**End-of-turn -> first AI audio**",
    "speech_end_to_first_audio_ms": "Last word -> first AI audio",
}


def _ms(v: float) -> str:
    return f"{v:,.0f}"


def _pct(v: float) -> str:
    return f"{100 * v:.1f}%"


def to_markdown(r: dict[str, Any]) -> str:
    out: list[str] = []
    m = r.get("machine", {})
    out.append(f"Machine: {m.get('gpu', '?')} ({m.get('gpu_total_mb', '?')} MB), {m.get('platform', '?')}\n")

    for p in r.get("pipeline", []):
        out.append(
            f"### Turn latency - {p['lang']} - LLM {p['llm']} - STT {p['stt_variant']} "
            f"({p['turns']} turns, silence {p['eot_silence_ms']:.0f} ms)\n"
        )
        out.append("| Stage | p50 ms | p95 ms | max ms |")
        out.append("|---|---:|---:|---:|")
        lat = p["latency"]
        for stage in STAGES:
            if stage in lat:
                s = lat[stage]
                out.append(f"| {LABELS[stage]} | {_ms(s['p50'])} | {_ms(s['p95'])} | {_ms(s['max'])} |")
        out.append("")
        out.append(
            f"WER {_pct(p['wer'])}, CER {_pct(p['cer'])}; JSON valid {p['json_valid']}; "
            f"LLM on GPU {p['llm_gpu_share']}; "
            f"GPU peak {p['gpu_peak_used_mb']:,} / {p['gpu_total_mb']:,} MB\n"
        )

    if r.get("stt"):
        out.append("### STT accuracy and latency\n")
        out.append("| Lang | Model | WER | CER | p50 ms | p95 ms | VRAM MB |")
        out.append("|---|---|---:|---:|---:|---:|---:|")
        for s in r["stt"]:
            lat = s["latency"]["stt_final_ms"]
            out.append(
                f"| {s['lang']} | {s['model']} | {_pct(s['wer'])} | {_pct(s['cer'])} | "
                f"{_ms(lat['p50'])} | {_ms(lat['p95'])} | {s['vram_mb']:,} |"
            )
        out.append("")

    if r.get("llm"):
        out.append("### LLM sizing (Ollama, num_ctx 4096, temperature 0, seed 42)\n")
        out.append(
            "| Model | Quant | On GPU | First token p50/p95 ms | Full p50/p95 ms | tok/s | JSON | VRAM MB |"
        )
        out.append("|---|---|---:|---:|---:|---:|---:|---:|")
        for s in r["llm"]:
            ft = s["latency"]["llm_first_token_ms"]
            full = s["latency"]["llm_full_ms"]
            out.append(
                f"| {s['model']} | {s['quant']} | {s['gpu_share']} | {_ms(ft['p50'])} / {_ms(ft['p95'])} | "
                f"{_ms(full['p50'])} / {_ms(full['p95'])} | {s['tokens_per_s_mean']:.1f} | "
                f"{s['json_valid']} | "
                f"{s['vram_mb']:,} |"
            )
        out.append("")

    c = r.get("captions")
    if c:
        d = c["partial_delay"]["caption_partial_delay_ms"]
        k = c["chunk_compute"]["chunk_compute_ms"]
        out.append("### Live captions (English)\n")
        out.append(
            f"{c['model']}, {c['chunk_ms']:.0f} ms chunks: partial delay p50 {_ms(d['p50'])} ms, "
            f"p95 {_ms(d['p95'])} ms (n={d['n']} tokens); chunk compute p95 {k['p95']:.1f} ms; "
            f"WER {_pct(c['wer'])}\n"
        )
    for note in r.get("skipped", []):
        out.append(f"- Skipped: {note}")
    return "\n".join(out) + "\n"
