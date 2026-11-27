"""semraa-spike CLI.

semraa-spike bench                  # one command: download, fixtures, every benchmark, results/latest.md
semraa-spike run --wav answer.wav   # one turn on a recording
semraa-spike run --mic              # live loop on the microphone (Ctrl+C to stop)
"""

from __future__ import annotations

import argparse
import os
import sys
import traceback
from pathlib import Path
from typing import Any

DEFAULT_LLMS = ["qwen3:8b", "qwen3.5:9b", "qwen2.5:7b", "qwen3:14b"]
DEFAULT_PIPELINE_LLM = "qwen3:8b"


def _eot(args: argparse.Namespace) -> Any:
    from semraa_spike.vad import EndOfTurnConfig

    return EndOfTurnConfig(end_silence_ms=args.silence_ms)


def cmd_download(args: argparse.Namespace) -> int:
    from semraa_spike import models

    for m in models.ALL_MODELS:
        if isinstance(m, models.HfModel) and m.gated and not args.tamil:
            continue
        models.ensure(m)
    return 0


def cmd_fixtures(args: argparse.Namespace) -> int:
    from semraa_spike.fixtures import load_fixtures, make_english, make_tamil

    if "en" in args.lang:
        make_english(load_fixtures("en"), overwrite=args.overwrite)
    if "ta" in args.lang:
        make_tamil(load_fixtures("ta"), overwrite=args.overwrite)
    return 0


def _try(results: dict[str, Any], label: str, fn: Any, *a: Any, **kw: Any) -> Any:
    try:
        return fn(*a, **kw)
    except Exception as exc:
        print(f"  ! {label}: {type(exc).__name__}: {exc}")
        traceback.print_exc(limit=3)
        results.setdefault("skipped", []).append(f"{label}: {type(exc).__name__}: {exc}")
        return None


def cmd_bench(args: argparse.Namespace) -> int:
    from semraa_spike import bench, models
    from semraa_spike.fixtures import load_fixtures, make_english, make_tamil

    results: dict[str, Any] = {"machine": bench.machine_info(), "stt": [], "llm": [], "pipeline": []}
    print(f"machine: {results['machine']}")
    for m in models.ALL_MODELS:
        if isinstance(m, models.HfModel) and m.gated and not os.environ.get("HF_TOKEN"):
            continue
        _try(results, f"download {m.key}", models.ensure, m)
    if "en" in args.lang:
        _try(results, "fixtures en", make_english, load_fixtures("en"))
    if "ta" in args.lang:
        _try(results, "fixtures ta", make_tamil, load_fixtures("ta"))

    for lang in args.lang:
        fx = bench.fixtures_for(lang)
        if not fx:
            results.setdefault("skipped", []).append(f"{lang}: no fixture audio")
            continue
        variants = args.stt or (["turbo-fp16", "turbo-int8", "medium-int8", "small-int8"] if lang == "en"
                                else ["indic-conformer", "turbo-fp16"])  # fmt: skip
        if not args.skip_stt:
            for v in variants:
                print(f"stt {lang} {v} ...")
                r = _try(results, f"stt {lang} {v}", bench.bench_stt, lang, v, fx)
                if r:
                    results["stt"].append(r)
        if not args.skip_llm:
            for model in args.llm:
                print(f"llm {lang} {model} ...")
                r = _try(results, f"llm {lang} {model}", bench.bench_llm, model, fx, lang)
                if r:
                    results["llm"].append(r)
        pipe_stt = args.pipeline_stt or ("turbo-int8" if lang == "en" else "indic-conformer")
        for model in args.pipeline_llm:
            print(f"pipeline {lang} {model} {pipe_stt} x{args.repeats} ...")
            r = _try(results, f"pipeline {lang} {model}", bench.bench_pipeline, lang, model, pipe_stt,
                     fx, args.repeats, _eot(args), args.tts_threads, args.tts_int8)  # fmt: skip
            if r:
                results["pipeline"].append(r)
    if "en" in args.lang and not args.skip_captions:
        print("captions en ...")
        r = _try(results, "captions en", bench.bench_captions, bench.fixtures_for("en"))
        if r:
            results["captions"] = r
    path = bench.write_results(results, Path(args.out) if args.out else bench.RESULTS_DIR)
    print(f"results: {path}")
    print((path.parent / "latest.md").read_text(encoding="utf-8"))
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    import json

    from semraa_spike.report import to_markdown

    print(to_markdown(json.loads(Path(args.json).read_text(encoding="utf-8"))))
    return 0


def _components(args: argparse.Namespace) -> Any:
    from semraa_spike import bench, models
    from semraa_spike.llm import OllamaClient, load_prompt
    from semraa_spike.pipeline import Components
    from semraa_spike.vad import SileroVad

    stt = bench.load_stt(args.lang, args.stt or ("turbo-int8" if args.lang == "en" else "indic-conformer"))
    tts = bench.load_tts(args.lang, threads=8)
    client = OllamaClient()
    client.load(args.llm, num_ctx=4096)
    return Components(
        vad=SileroVad(models.ensure(models.SILERO_VAD)),
        eot=_eot(args),
        stt=stt,
        llm=client,
        llm_model=args.llm,
        prompt=load_prompt(language=args.lang),
        tts=tts,
    )


def _print_turn(r: Any, show_text: bool) -> None:
    for k, v in r.timings.items():
        print(f"  {k:32s} {'-' if v is None else f'{v:8.0f} ms'}")
    if show_text:  # opt-in only: transcripts are never logged
        print(f"  transcript: {r.transcript}\n  reply: {r.reply}")


def cmd_run(args: argparse.Namespace) -> int:
    from semraa_spike.audio import load_wav
    from semraa_spike.pipeline import run_turn

    comp = _components(args)
    if args.wav:
        audio = load_wav(Path(args.wav))
        run_turn(comp, audio, args.question)  # warm-up
        r = run_turn(comp, audio, args.question, on_audio=_player() if args.play else None)
        _print_turn(r, args.show_text)
        return 0
    return _mic_loop(comp, args)


def _player() -> Any:
    import sounddevice as sd

    def play(samples: Any, rate: int) -> None:
        sd.play(samples, rate)
        sd.wait()

    return play


def _mic_loop(comp: Any, args: argparse.Namespace) -> int:
    import queue

    import numpy as np
    import sounddevice as sd

    from semraa_spike.pipeline import DetectedTurn, LiveSegmenter, LiveTurn, run_turn
    from semraa_spike.vad import FRAME_SAMPLES, SAMPLE_RATE

    frames: queue.Queue[Any] = queue.Queue()

    def callback(indata: Any, _n: int, _t: Any, _s: Any) -> None:
        frames.put(indata[:, 0].copy())

    seg = LiveSegmenter(comp.eot)
    play = _player()
    print("warming up ...")  # one silent turn (nothing played) so the first real answer is not a cold start
    silence = np.zeros(SAMPLE_RATE, dtype=np.float32)
    run_turn(comp, silence, args.question, detected=DetectedTurn(0.0, 1000.0, 1000.0, 0.0, True))
    comp.vad.reset()
    print(f"listening (end of answer after {comp.eot.end_silence_ms:.0f} ms silence), Ctrl+C to stop")
    with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="float32", blocksize=FRAME_SAMPLES,
                        callback=callback):  # fmt: skip
        try:
            while True:
                frame = frames.get()
                ev = seg.push(frame, comp.vad(frame))
                if ev is None:
                    continue
                if not isinstance(ev, LiveTurn):  # TurnEventKind.SPEECH_START
                    print("  ... speech")
                    continue
                print("  ... thinking")
                try:
                    r = run_turn(comp, ev.audio, args.question, on_audio=play, detected=ev.detected)
                    _print_turn(r, args.show_text)
                except Exception as exc:  # one bad turn (Ollama hiccup, audio glitch) must not end it all
                    print(f"  ! turn failed: {type(exc).__name__}: {exc}")
                while not frames.empty():  # drop what the mic heard while the AI was speaking
                    frames.get_nowait()
                seg.clear()
                comp.vad.reset()
                print("listening")
        except KeyboardInterrupt:
            print("stopped")
            return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="semraa-spike", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)  # fmt: skip
    p.add_argument("--silence-ms", type=float, default=1800.0, help="end-of-answer silence (1500-2500)")
    sub = p.add_subparsers(dest="cmd", required=True)

    d = sub.add_parser("download", help="download pinned models")
    d.add_argument("--tamil", action="store_true", help="also gated AI4Bharat models (needs HF_TOKEN)")
    d.set_defaults(fn=cmd_download)

    f = sub.add_parser("fixtures", help="render synthetic fixture audio")
    f.add_argument("--lang", nargs="+", default=["en", "ta"], choices=["en", "ta"])
    f.add_argument("--overwrite", action="store_true")
    f.set_defaults(fn=cmd_fixtures)

    b = sub.add_parser("bench", help="run every benchmark and write results/latest.{json,md}")
    b.add_argument("--lang", nargs="+", default=["en", "ta"], choices=["en", "ta"])
    b.add_argument("--llm", nargs="+", default=DEFAULT_LLMS, help="models for the LLM sizing table")
    b.add_argument("--pipeline-llm", nargs="+", default=[DEFAULT_PIPELINE_LLM])
    b.add_argument("--stt", nargs="+", help="STT variants for the accuracy table")
    b.add_argument("--pipeline-stt", help="STT variant used in the full turn")
    b.add_argument("--repeats", type=int, default=3)
    b.add_argument("--tts-threads", type=int, default=8, help="Kokoro CPU threads")
    b.add_argument("--tts-int8", action="store_true", help="int8 Kokoro model")
    b.add_argument("--skip-stt", action="store_true")
    b.add_argument("--skip-llm", action="store_true")
    b.add_argument("--skip-captions", action="store_true")
    b.add_argument("--out", help="results directory")
    b.set_defaults(fn=cmd_bench)

    rep = sub.add_parser("report", help="render a results JSON as Markdown tables")
    rep.add_argument("json")
    rep.set_defaults(fn=cmd_report)

    r = sub.add_parser("run", help="one turn on a WAV file, or a live microphone loop")
    src = r.add_mutually_exclusive_group(required=True)
    src.add_argument("--wav")
    src.add_argument("--mic", action="store_true")
    r.add_argument("--lang", default="en", choices=["en", "ta"])
    r.add_argument("--llm", default=DEFAULT_PIPELINE_LLM)
    r.add_argument("--stt")
    r.add_argument("--question", default="Tell me about a project you built.")
    r.add_argument("--play", action="store_true", help="play the reply (WAV mode)")
    r.add_argument("--show-text", action="store_true", help="print transcript and reply (off by default)")
    r.set_defaults(fn=cmd_run)

    args = p.parse_args(argv)
    result: int = args.fn(args)
    return result


if __name__ == "__main__":
    sys.exit(main())
