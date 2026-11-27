import pytest

from semraa_spike.vad import EndOfTurnConfig, EndOfTurnDetector, TurnEvent, TurnEventKind

CFG = EndOfTurnConfig(frame_ms=10, min_speech_ms=50, end_silence_ms=100)


def run(probs: list[float], cfg: EndOfTurnConfig = CFG) -> list[TurnEvent]:
    det = EndOfTurnDetector(cfg)
    events = [det.update(p) for p in probs]
    return [e for e in events if e is not None]


def test_end_of_turn_after_configured_silence() -> None:
    probs = [0.0] * 5 + [0.9] * 20 + [0.0] * 10
    events = run(probs)
    assert [e.kind for e in events] == [TurnEventKind.SPEECH_START, TurnEventKind.END_OF_TURN]
    eot = events[1]
    assert eot.speech_start_ms == 50
    assert eot.last_speech_end_ms == 250
    assert eot.at_ms == 350  # exactly end_silence_ms after the last voiced frame


def test_pause_shorter_than_threshold_does_not_end_turn() -> None:
    probs = [0.9] * 10 + [0.0] * 9 + [0.9] * 10 + [0.0] * 10
    events = run(probs)
    eots = [e for e in events if e.kind is TurnEventKind.END_OF_TURN]
    assert len(eots) == 1
    assert eots[0].last_speech_end_ms == 290


def test_short_burst_never_opens_a_turn() -> None:
    probs = [0.9] * 3 + [0.0] * 30  # 30 ms < min_speech_ms
    assert run(probs) == []


def test_hysteresis_keeps_speech_between_thresholds() -> None:
    # 0.4 is below speech_threshold (0.5) but above silence_threshold (0.35): continues an open stretch
    probs = [0.9] * 10 + [0.4] * 20 + [0.0] * 10
    events = run(probs)
    assert events[-1].kind is TurnEventKind.END_OF_TURN
    assert events[-1].last_speech_end_ms == 300


def test_mid_probability_alone_does_not_start_speech() -> None:
    assert run([0.4] * 50) == []


def test_detector_resets_for_next_turn() -> None:
    one_turn = [0.9] * 10 + [0.0] * 10
    events = run(one_turn + one_turn)
    assert [e.kind for e in events].count(TurnEventKind.END_OF_TURN) == 2
    assert events[-1].speech_start_ms == 200


@pytest.mark.parametrize(
    "kwargs",
    [
        {"speech_threshold": 0.3, "silence_threshold": 0.5},
        {"end_silence_ms": 0},
        {"frame_ms": 0},
    ],
)
def test_config_validation(kwargs: dict[str, float]) -> None:
    with pytest.raises(ValueError):
        EndOfTurnConfig(**kwargs)  # type: ignore[arg-type]
