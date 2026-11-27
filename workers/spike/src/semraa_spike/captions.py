"""Live captions with a sherpa-onnx streaming transducer, and the caption partial-delay measurement.

Partial delay for a token = (stream time at which the chunk containing it arrived + compute time to emit it)
minus the token's own timestamp in the audio. It includes chunk buffering, model look-ahead and compute,
i.e. what a candidate would see on screen.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from semraa_spike.audio import Audio
from semraa_spike.timing import Clock
from semraa_spike.vad import SAMPLE_RATE


@dataclass
class CaptionRun:
    text: str
    token_delays_ms: list[float] = field(default_factory=list)
    chunk_compute_ms: list[float] = field(default_factory=list)
    chunk_ms: float = 0.0


class StreamingCaptioner:
    def __init__(self, model_dir: Path, threads: int = 2, provider: str = "cpu") -> None:
        import sherpa_onnx

        def pick(prefix: str) -> str:
            int8 = sorted(model_dir.glob(f"{prefix}*.int8.onnx"))
            fp32 = sorted(p for p in model_dir.glob(f"{prefix}*.onnx") if ".int8." not in p.name)
            chosen = (int8 or fp32)[0]
            return str(chosen)

        self._rec = sherpa_onnx.OnlineRecognizer.from_transducer(
            tokens=str(model_dir / "tokens.txt"),
            encoder=pick("encoder"),
            decoder=str(sorted(p for p in model_dir.glob("decoder*.onnx") if ".int8." not in p.name)[0]),
            joiner=pick("joiner"),
            num_threads=threads,
            sample_rate=SAMPLE_RATE,
            decoding_method="greedy_search",
            provider=provider,
        )
        self.name = f"sherpa-onnx/{model_dir.name} ({provider} x{threads})"

    def run(self, audio: Audio, chunk_ms: float = 100.0, clock: Clock | None = None) -> CaptionRun:
        clock = clock or Clock()
        stream = self._rec.create_stream()
        chunk = int(SAMPLE_RATE * chunk_ms / 1000)
        out = CaptionRun(text="", chunk_ms=chunk_ms)
        seen = 0
        for i in range(0, len(audio), chunk):
            arrival_ms = (i + min(chunk, len(audio) - i)) * 1000 / SAMPLE_RATE
            t0 = clock.now_ms()
            stream.accept_waveform(SAMPLE_RATE, audio[i : i + chunk])
            while self._rec.is_ready(stream):
                self._rec.decode_stream(stream)
            result = self._rec.get_result_all(stream)
            compute = clock.now_ms() - t0
            out.chunk_compute_ms.append(compute)
            stamps = list(result.timestamps)
            for ts in stamps[seen:]:
                out.token_delays_ms.append(arrival_ms + compute - ts * 1000)
            seen = len(stamps)
        stream.input_finished()
        while self._rec.is_ready(stream):
            self._rec.decode_stream(stream)
        out.text = self._rec.get_result_all(stream).text.strip()
        return out
