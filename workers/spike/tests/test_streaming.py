import json

from semraa_spike.streaming import JsonStringFieldStream, SentenceChunker


def stream(text: str, size: int) -> tuple[str, JsonStringFieldStream]:
    s = JsonStringFieldStream("reply")
    got = "".join(s.feed(text[i : i + size]) for i in range(0, len(text), size))
    return got, s


def test_extracts_field_across_any_chunking() -> None:
    reply = 'Good. Now, what is "Big-O" of a hash lookup?\nAnd \\ unicode: é தமிழ் 😀'
    doc = json.dumps({"reply": reply, "intent": "follow_up"})
    for size in range(1, 12):
        got, s = stream(doc, size)
        assert got == reply, size
        assert s.done


def test_field_not_first_and_ascii_escaped_json() -> None:
    doc = json.dumps({"intent": "clarify", "reply": "சரி. 😀"}, ensure_ascii=True)
    got, s = stream(doc, 3)
    assert got == "சரி. 😀"
    assert s.value == got


def test_missing_field_yields_nothing() -> None:
    got, s = stream('{"intent": "x"}', 4)
    assert got == ""
    assert not s.done


def test_sentence_chunker_releases_complete_sentences() -> None:
    c = SentenceChunker(min_chars=10)
    out: list[str] = []
    for piece in ["That is a good answer. ", "Can you expl", "ain the trade-off? Thanks"]:
        out += c.feed(piece)
    assert out == ["That is a good answer.", "Can you explain the trade-off?"]
    assert c.flush() == ["Thanks"]
    assert c.flush() == []


def test_sentence_chunker_merges_short_and_skips_abbreviations() -> None:
    c = SentenceChunker(min_chars=20, first_min_chars=20)
    out = c.feed("Okay. Use a cache, e.g. Redis or Valkey. Next one. ")
    assert out == ["Okay. Use a cache, e.g. Redis or Valkey."]
    assert c.flush() == ["Next one."]


def test_sentence_chunker_releases_short_opener_first() -> None:
    c = SentenceChunker(min_chars=24, first_min_chars=8)
    out = c.feed("Good start. Yes. Now explain chaining in detail. ")
    assert out == ["Good start.", "Yes. Now explain chaining in detail."]
    assert SentenceChunker(first_min_chars=8).feed("Ok. Fine. ") == ["Ok. Fine."]
