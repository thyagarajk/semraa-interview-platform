"""Per-turn stage timings and their p50/p95 aggregation (pure logic, no model imports)."""

from __future__ import annotations

import math
import time
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass

# Stage keys, in pipeline order. All values are milliseconds.
STAGES: tuple[str, ...] = (
    "vad_detect_ms",  # last voiced frame -> end-of-turn decision (includes the configured silence wait)
    "stt_final_ms",  # end-of-turn -> final transcript
    "llm_first_token_ms",  # transcript ready -> first LLM token
    "llm_full_ms",  # transcript ready -> last LLM token
    "tts_first_audio_ms",  # first sentence handed to TTS -> its audio ready
    "eot_to_first_audio_ms",  # end-of-turn decision -> first AI audio ready (the latency target)
    "speech_end_to_first_audio_ms",  # last voiced frame -> first AI audio ready (what the candidate feels)
)


def percentile(values: Sequence[float], q: float) -> float:
    """Linear-interpolated percentile (same as numpy's default 'linear' method). q in [0, 100]."""
    if not values:
        raise ValueError("percentile of empty sequence")
    if not 0.0 <= q <= 100.0:
        raise ValueError(f"q must be in [0, 100], got {q}")
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    rank = (len(ordered) - 1) * q / 100.0
    low = math.floor(rank)
    high = math.ceil(rank)
    if low == high:
        return ordered[low]
    return ordered[low] + (ordered[high] - ordered[low]) * (rank - low)


@dataclass(frozen=True)
class StageSummary:
    n: int
    p50: float
    p95: float
    mean: float
    max: float


def summarize(turns: Iterable[Mapping[str, float | None]]) -> dict[str, StageSummary]:
    """Aggregate per-turn timings into per-stage summaries. Missing (None) values are skipped."""
    buckets: dict[str, list[float]] = {}
    for turn in turns:
        for stage, value in turn.items():
            if value is None:
                continue
            if value < 0 or math.isnan(value):
                raise ValueError(f"invalid timing for {stage}: {value}")
            buckets.setdefault(stage, []).append(float(value))
    ordered_keys = [s for s in STAGES if s in buckets] + sorted(k for k in buckets if k not in STAGES)
    return {
        stage: StageSummary(
            n=len(buckets[stage]),
            p50=percentile(buckets[stage], 50),
            p95=percentile(buckets[stage], 95),
            mean=sum(buckets[stage]) / len(buckets[stage]),
            max=max(buckets[stage]),
        )
        for stage in ordered_keys
    }


def meets_target(summary: Mapping[str, StageSummary], stage: str, p50_ms: float, p95_ms: float) -> bool:
    s = summary.get(stage)
    return s is not None and s.p50 <= p50_ms and s.p95 <= p95_ms


class Clock:
    """Monotonic millisecond clock; injectable so tests can drive time."""

    def now_ms(self) -> float:
        return time.perf_counter_ns() / 1_000_000
