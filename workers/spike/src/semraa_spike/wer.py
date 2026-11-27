"""Word / character error rate with a language-aware normaliser (pure logic around jiwer)."""

from __future__ import annotations

import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass

import jiwer


def normalize(text: str) -> str:
    """Casefold, drop punctuation and symbols, keep letters, combining marks (Tamil vowel signs) and digits.

    Hyphens and apostrophes become spaces / vanish so "real-time" == "real time" and "it's" == "its".
    """
    text = unicodedata.normalize("NFC", text).casefold()
    out: list[str] = []
    for ch in text:
        if ch in ("'", "\u2019"):
            continue
        cat = unicodedata.category(ch)
        if cat[0] in ("L", "M", "N"):
            out.append(ch)
        elif ch in ("‌", "‍"):  # zero-width (non-)joiners carry no meaning for scoring
            continue
        else:
            out.append(" ")
    return " ".join("".join(out).split())


@dataclass(frozen=True)
class ErrorRates:
    wer: float
    cer: float
    n_utterances: int
    ref_words: int


def error_rates(references: Sequence[str], hypotheses: Sequence[str]) -> ErrorRates:
    """Corpus-level WER and CER (errors summed over all utterances / total reference length)."""
    if len(references) != len(hypotheses):
        raise ValueError("references and hypotheses differ in length")
    if not references:
        raise ValueError("need at least one utterance")
    refs = [normalize(r) for r in references]
    hyps = [normalize(h) for h in hypotheses]
    if any(not r for r in refs):
        raise ValueError("empty reference after normalisation")
    return ErrorRates(
        wer=float(jiwer.wer(refs, hyps)),
        cer=float(jiwer.cer(refs, hyps)),
        n_utterances=len(refs),
        ref_words=sum(len(r.split()) for r in refs),
    )
