from semraa_spike.stt_indic import ctc_greedy

VOCAB = ["<unk>", "▁வ", "ண", "க்கம்", "▁நன்றி"]
BLANK = 5


def test_collapses_repeats_and_drops_blanks() -> None:
    path = [BLANK, 1, 1, 2, BLANK, 3, 3, BLANK, 4, 4, BLANK]
    assert ctc_greedy(path, VOCAB, blank=BLANK) == "வணக்கம் நன்றி"


def test_blank_separates_repeated_token() -> None:
    assert ctc_greedy([2, BLANK, 2], VOCAB, blank=BLANK) == "ணண"


def test_empty_path() -> None:
    assert ctc_greedy([BLANK, BLANK], VOCAB, blank=BLANK) == ""
