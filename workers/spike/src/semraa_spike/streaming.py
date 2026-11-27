"""Streaming helpers: pull the spoken "reply" field out of partial JSON, and cut it into sentences for TTS."""

from __future__ import annotations

import re
from typing import ClassVar


class JsonStringFieldStream:
    """Incrementally decode one top-level string field (e.g. "reply") from a JSON object streamed in chunks.

    The LLM is constrained to a JSON schema whose first property is the spoken reply, so we can start TTS on
    the first sentence before the object is complete.
    """

    _ESCAPES: ClassVar[dict[str, str]] = {
        '"': '"',
        "\\": "\\",
        "/": "/",
        "b": "\b",
        "f": "\f",
        "n": "\n",
        "r": "\r",
        "t": "\t",
    }

    def __init__(self, field: str) -> None:
        self._key = re.compile(r'"' + re.escape(field) + r'"\s*:\s*"')
        self._buf = ""
        self._pos = 0  # index into _buf of the next undecoded char inside the value
        self._state = "seek"  # seek -> value -> done
        self.value = ""

    @property
    def done(self) -> bool:
        return self._state == "done"

    def feed(self, chunk: str) -> str:
        """Add raw JSON text; return the newly decoded part of the field value."""
        self._buf += chunk
        if self._state == "seek":
            m = self._key.search(self._buf)
            if m is None:
                return ""
            self._state = "value"
            self._pos = m.end()
        if self._state != "value":
            return ""
        out: list[str] = []
        buf = self._buf
        i = self._pos
        while i < len(buf):
            ch = buf[i]
            if ch == '"':
                self._state = "done"
                i += 1
                break
            if ch == "\\":
                if i + 1 >= len(buf):
                    break  # escape split across chunks; wait for more
                esc = buf[i + 1]
                if esc == "u":
                    if i + 6 > len(buf):
                        break
                    code = int(buf[i + 2 : i + 6], 16)
                    if 0xD800 <= code < 0xDC00:  # high surrogate: need the low half too
                        if i + 12 > len(buf):
                            break
                        low = int(buf[i + 8 : i + 12], 16)
                        out.append(chr(0x10000 + ((code - 0xD800) << 10) + (low - 0xDC00)))
                        i += 12
                    else:
                        out.append(chr(code))
                        i += 6
                    continue
                out.append(self._ESCAPES.get(esc, esc))
                i += 2
                continue
            out.append(ch)
            i += 1
        self._pos = i
        text = "".join(out)
        self.value += text
        return text


# Sentence end: . ! ? (and the Devanagari danda, harmless for Tamil) followed by whitespace.
_SENTENCE_END = re.compile(r"(?<=[.!?।])\s+")
# Common abbreviations that end in a dot but do not end a sentence.
_ABBREV = re.compile(r"(?:\b(?:e\.g|i\.e|etc|vs|Dr|Mr|Ms|Mrs|approx)\.|\b[A-Z]\.)$")


class SentenceChunker:
    """Accumulate streamed text and release whole sentences, merging very short ones (TTS sounds better)."""

    def __init__(self, min_chars: int = 24, first_min_chars: int = 8) -> None:
        """`first_min_chars` is lower so a short opener ("Good answer.") reaches TTS at once: that sentence
        decides the time to first AI audio. Later sentences are synthesised while the first one plays."""
        self.min_chars = min_chars
        self.first_min_chars = first_min_chars
        self._released = 0
        self._pending = ""

    def feed(self, text: str) -> list[str]:
        self._pending += text
        out: list[str] = []
        start = 0
        for m in _SENTENCE_END.finditer(self._pending):
            candidate = self._pending[start : m.start()].strip()
            limit = self.first_min_chars if self._released == 0 else self.min_chars
            if _ABBREV.search(candidate) or len(candidate) < limit:
                continue
            out.append(candidate)
            self._released += 1
            start = m.end()
        self._pending = self._pending[start:]
        return out

    def flush(self) -> list[str]:
        rest = self._pending.strip()
        self._pending = ""
        return [rest] if rest else []
