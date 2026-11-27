import math

import pytest

from semraa_spike.timing import STAGES, meets_target, percentile, summarize


def test_percentile_matches_linear_interpolation() -> None:
    values = [1.0, 2.0, 3.0, 4.0]
    assert percentile(values, 0) == 1.0
    assert percentile(values, 100) == 4.0
    assert percentile(values, 50) == 2.5
    assert math.isclose(percentile(values, 95), 3.85)


def test_percentile_single_value_and_unsorted_input() -> None:
    assert percentile([7.0], 95) == 7.0
    assert percentile([3.0, 1.0, 2.0], 50) == 2.0


@pytest.mark.parametrize("q", [-1.0, 100.1])
def test_percentile_rejects_bad_q(q: float) -> None:
    with pytest.raises(ValueError):
        percentile([1.0], q)


def test_percentile_rejects_empty() -> None:
    with pytest.raises(ValueError):
        percentile([], 50)


def test_summarize_skips_missing_and_orders_stages() -> None:
    turns = [
        {"stt_final_ms": 100.0, "eot_to_first_audio_ms": 900.0, "extra_ms": 1.0},
        {"stt_final_ms": 300.0, "eot_to_first_audio_ms": None},
    ]
    s = summarize(turns)
    assert list(s) == ["stt_final_ms", "eot_to_first_audio_ms", "extra_ms"]
    assert s["stt_final_ms"].n == 2
    assert s["stt_final_ms"].p50 == 200.0
    assert s["stt_final_ms"].mean == 200.0
    assert s["stt_final_ms"].max == 300.0
    assert s["eot_to_first_audio_ms"].n == 1


def test_summarize_rejects_negative() -> None:
    with pytest.raises(ValueError):
        summarize([{"stt_final_ms": -1.0}])


def test_meets_target() -> None:
    s = summarize([{"eot_to_first_audio_ms": v} for v in (1000.0, 1200.0, 1400.0, 2900.0)])
    assert meets_target(s, "eot_to_first_audio_ms", 2000, 3000)
    assert not meets_target(s, "eot_to_first_audio_ms", 1000, 3000)
    assert not meets_target(s, "missing_ms", 2000, 3000)


def test_stage_keys_are_unique() -> None:
    assert len(set(STAGES)) == len(STAGES)
