import numpy as np

from semraa_spike.pipeline import LiveSegmenter, LiveTurn
from semraa_spike.vad import FRAME_SAMPLES, SAMPLE_RATE, EndOfTurnConfig, TurnEventKind

CFG = EndOfTurnConfig(end_silence_ms=1000.0, min_speech_ms=250.0)


def frame(value: float) -> np.ndarray:
    return np.full(FRAME_SAMPLES, value, dtype=np.float32)


def test_idle_microphone_keeps_only_a_bounded_preroll() -> None:
    seg = LiveSegmenter(CFG)
    for _ in range(5000):  # ~160 s of silence
        assert seg.push(frame(0.0), 0.0) is None
    assert seg.buffered_frames * CFG.frame_ms < CFG.end_silence_ms + CFG.min_speech_ms + 500


def test_turn_audio_and_times_line_up_with_the_speech() -> None:
    seg = LiveSegmenter(CFG)
    for _ in range(2000):
        seg.push(frame(0.0), 0.0)
    events = []
    for _ in range(30):  # ~960 ms of speech, samples marked 1.0
        events.append(seg.push(frame(1.0), 0.9))
    for _ in range(100):
        ev = seg.push(frame(0.0), 0.0)
        if ev is not None:
            events.append(ev)
            break
    assert TurnEventKind.SPEECH_START in events
    turn = events[-1]
    assert isinstance(turn, LiveTurn)
    d = turn.detected
    start = round(d.speech_start_ms * SAMPLE_RATE / 1000)
    end = round(d.last_speech_end_ms * SAMPLE_RATE / 1000)
    assert np.all(turn.audio[start:end] == 1.0)
    assert turn.audio[start - 1] == 0.0 and turn.audio[end] == 0.0
    assert d.eot_at_ms - d.last_speech_end_ms >= CFG.end_silence_ms
    assert seg.buffered_frames == 0  # cleared for the next answer


def test_long_answer_is_not_trimmed_once_speech_started() -> None:
    seg = LiveSegmenter(CFG)
    turn = None
    for i in range(400):  # ~13 s answer with short pauses
        turn = seg.push(frame(1.0), 0.9 if i % 20 else 0.0) or turn
    for _ in range(100):
        ev = seg.push(frame(0.0), 0.0)
        if isinstance(ev, LiveTurn):
            turn = ev
            break
    assert isinstance(turn, LiveTurn)
    assert turn.detected.last_speech_end_ms - turn.detected.speech_start_ms > 12_000
