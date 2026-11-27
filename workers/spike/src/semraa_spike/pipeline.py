"""One cascaded interview turn: VAD end-of-turn -> STT -> LLM (streamed JSON) -> TTS sentence by sentence."""

from __future__ import annotations

import queue
import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from semraa_spike.audio import Audio, frames
from semraa_spike.llm import OllamaClient, Prompt, user_message
from semraa_spike.streaming import SentenceChunker
from semraa_spike.stt import Stt
from semraa_spike.timing import Clock
from semraa_spike.tts import Tts
from semraa_spike.vad import SAMPLE_RATE, EndOfTurnConfig, EndOfTurnDetector, SileroVad, TurnEventKind

SEGMENT_PAD_BEFORE_S = 0.2
SEGMENT_PAD_AFTER_S = 0.3


@dataclass
class Components:
    vad: SileroVad
    eot: EndOfTurnConfig
    stt: Stt
    llm: OllamaClient
    llm_model: str
    prompt: Prompt
    tts: Tts
    num_ctx: int = 4096
    num_gpu: int | None = None


@dataclass
class TurnResult:
    timings: dict[str, float | None]
    transcript: str
    reply: str
    llm_json_valid: bool
    llm_tokens_per_s: float
    reply_audio: list[tuple[Audio, int]] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class DetectedTurn:
    speech_start_ms: float
    last_speech_end_ms: float
    eot_at_ms: float
    vad_compute_ms_per_frame: float
    closed_by_silence: bool


def detect_turn(vad: SileroVad, cfg: EndOfTurnConfig, audio: Audio, clock: Clock) -> DetectedTurn:
    vad.reset()
    det = EndOfTurnDetector(cfg)
    start = None
    t0 = clock.now_ms()
    n = 0
    for frame in frames(audio):
        n += 1
        event = det.update(vad(frame))
        if event is None:
            continue
        if event.kind is TurnEventKind.SPEECH_START:
            start = event
        else:
            per_frame = (clock.now_ms() - t0) / n
            return DetectedTurn(event.speech_start_ms, event.last_speech_end_ms, event.at_ms, per_frame, True)
    per_frame = (clock.now_ms() - t0) / max(n, 1)
    if start is None:
        raise ValueError("no speech detected")
    end = len(audio) * 1000 / SAMPLE_RATE
    return DetectedTurn(start.speech_start_ms, end, end, per_frame, False)


def run_turn(
    c: Components,
    audio: Audio,
    question: str,
    clock: Clock | None = None,
    on_audio: Callable[[Audio, int], None] | None = None,
    detected: DetectedTurn | None = None,
) -> TurnResult:
    """Run one turn on a recorded answer. Timing starts at the VAD end-of-turn decision.

    Pass `detected` when the turn was already segmented live (microphone mode).
    """
    clock = clock or Clock()
    turn = detected or detect_turn(c.vad, c.eot, audio, clock)
    a = max(0, int((turn.speech_start_ms / 1000 - SEGMENT_PAD_BEFORE_S) * SAMPLE_RATE))
    b = min(len(audio), int((turn.last_speech_end_ms / 1000 + SEGMENT_PAD_AFTER_S) * SAMPLE_RATE))
    segment = np.ascontiguousarray(audio[a:b])

    t_eot = clock.now_ms()
    transcript = c.stt.transcribe(segment)
    t_stt = clock.now_ms()

    sentences: queue.Queue[str | None] = queue.Queue()
    first_audio_at: list[float] = []
    first_synth_ms: list[float] = []
    reply_audio: list[tuple[Audio, int]] = []
    errors: list[BaseException] = []

    def tts_worker() -> None:
        try:
            while (sentence := sentences.get()) is not None:
                s0 = clock.now_ms()
                samples, rate = c.tts.synth(sentence)
                done = clock.now_ms()
                if not first_audio_at:
                    first_audio_at.append(done)
                    first_synth_ms.append(done - s0)
                reply_audio.append((samples, rate))
                if on_audio is not None:
                    on_audio(samples, rate)
        except BaseException as exc:  # surfaced after join
            errors.append(exc)

    worker = threading.Thread(target=tts_worker, daemon=True)
    worker.start()
    chunker = SentenceChunker()

    def on_delta(delta: str, reply_done: bool) -> None:
        for s in chunker.feed(delta):
            sentences.put(s)
        if reply_done:
            for s in chunker.flush():
                sentences.put(s)

    try:
        result = c.llm.chat(
            c.llm_model, c.prompt, user_message(question, transcript),
            num_ctx=c.num_ctx, num_gpu=c.num_gpu, on_reply_delta=on_delta,
        )  # fmt: skip
        for s in chunker.flush():
            sentences.put(s)
    finally:
        sentences.put(None)
        worker.join()
    if errors:
        raise errors[0]

    vad_detect = turn.eot_at_ms - turn.last_speech_end_ms + turn.vad_compute_ms_per_frame
    eot_to_audio = (first_audio_at[0] - t_eot) if first_audio_at else None
    timings: dict[str, float | None] = {
        "vad_detect_ms": vad_detect,
        "stt_final_ms": t_stt - t_eot,
        "llm_first_token_ms": result.first_token_ms,
        "llm_full_ms": result.full_ms,
        "tts_first_audio_ms": first_synth_ms[0] if first_synth_ms else None,
        "eot_to_first_audio_ms": eot_to_audio,
        "speech_end_to_first_audio_ms": (vad_detect + eot_to_audio) if eot_to_audio is not None else None,
    }
    return TurnResult(
        timings=timings,
        transcript=transcript,
        reply=result.reply,
        llm_json_valid=result.parsed is not None and set(result.parsed) >= {"reply", "intent"},
        llm_tokens_per_s=result.eval_tokens_per_s,
        reply_audio=reply_audio,
        extra={"closed_by_silence": turn.closed_by_silence, "parsed": result.parsed},
    )
