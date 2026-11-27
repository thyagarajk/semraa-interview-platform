import math

import pytest

from semraa_spike.wer import error_rates, normalize


def test_normalize_english() -> None:
    assert normalize("It's a Real-Time, O(n) cache!") == "its a real time o n cache"


def test_normalize_keeps_tamil_vowel_signs() -> None:
    text = "தரவுத்தளம், ஒரு அட்டவணை."
    assert normalize(text) == "தரவுத்தளம் ஒரு அட்டவணை"


def test_perfect_match() -> None:
    r = error_rates(["Hello world."], ["hello, world"])
    assert r.wer == 0.0
    assert r.cer == 0.0
    assert r.ref_words == 2


def test_corpus_level_wer() -> None:
    # 1 substitution in 4 words + 1 deletion in 2 words = 2 errors / 6 words
    r = error_rates(["a b c d", "e f"], ["a x c d", "e"])
    assert math.isclose(r.wer, 2 / 6)
    assert r.n_utterances == 2


def test_rejects_mismatched_lengths_and_empty() -> None:
    with pytest.raises(ValueError):
        error_rates(["a"], [])
    with pytest.raises(ValueError):
        error_rates([], [])
    with pytest.raises(ValueError):
        error_rates(["..."], ["a"])
