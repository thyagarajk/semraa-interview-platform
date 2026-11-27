"""Ollama chat client (localhost only): structured JSON output, temperature 0, fixed seed, streamed."""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx

from semraa_spike.streaming import JsonStringFieldStream
from semraa_spike.timing import Clock

PROMPTS_DIR = Path(__file__).resolve().parents[2] / "prompts"
PROMPT_VERSION = "interviewer.v1"
SEED = 42
LANGUAGE_NAMES = {"en": "English", "ta": "Tamil"}


@dataclass(frozen=True)
class Prompt:
    version: str
    system: str
    schema: dict[str, Any]


def load_prompt(version: str = PROMPT_VERSION, language: str = "en") -> Prompt:
    system = (PROMPTS_DIR / f"{version}.md").read_text(encoding="utf-8")
    schema = json.loads((PROMPTS_DIR / f"{version}.schema.json").read_text(encoding="utf-8"))
    return Prompt(version, system.replace("{language}", LANGUAGE_NAMES[language]), schema)


@dataclass
class LlmResult:
    raw: str
    reply: str
    parsed: dict[str, Any] | None
    first_token_ms: float
    full_ms: float
    eval_tokens: int = 0
    eval_tokens_per_s: float = 0.0
    prompt_tokens: int = 0
    extra: dict[str, Any] = field(default_factory=dict)


class OllamaClient:
    def __init__(self, base_url: str = "http://127.0.0.1:11434", clock: Clock | None = None) -> None:
        host = urlparse(base_url).hostname
        if host not in ("127.0.0.1", "localhost", "::1"):
            raise ValueError("Ollama must be reached on localhost only")
        self._http = httpx.Client(base_url=base_url, timeout=httpx.Timeout(300.0, connect=5.0))
        self._clock = clock or Clock()

    def close(self) -> None:
        self._http.close()

    def ps(self) -> list[dict[str, Any]]:
        models: list[dict[str, Any]] = self._http.get("/api/ps").json().get("models", [])
        return models

    def show(self, model: str) -> dict[str, Any]:
        data: dict[str, Any] = self._http.post("/api/show", json={"model": model}).json()
        return data

    def unload(self, model: str) -> None:
        self._http.post("/api/generate", json={"model": model, "keep_alive": 0})

    def load(self, model: str, num_ctx: int, num_gpu: int | None = None) -> None:
        options: dict[str, Any] = {"num_ctx": num_ctx}
        if num_gpu is not None:
            options["num_gpu"] = num_gpu
        self._http.post("/api/generate", json={"model": model, "keep_alive": "30m", "options": options})

    def chat(
        self,
        model: str,
        prompt: Prompt,
        user: str,
        *,
        num_ctx: int = 4096,
        num_gpu: int | None = None,
        on_reply_delta: Callable[[str, bool], None] | None = None,
    ) -> LlmResult:
        options: dict[str, Any] = {"temperature": 0, "seed": SEED, "num_ctx": num_ctx, "num_predict": 200}
        if num_gpu is not None:
            options["num_gpu"] = num_gpu
        body = {
            "model": model,
            "messages": [{"role": "system", "content": prompt.system}, {"role": "user", "content": user}],
            "format": prompt.schema,
            "options": options,
            "stream": True,
            "think": False,
            "keep_alive": "30m",
        }
        reply = JsonStringFieldStream("reply")
        parts: list[str] = []
        first_ms: float | None = None
        reply_closed = False
        start = self._clock.now_ms()
        final: dict[str, Any] = {}
        with self._http.stream("POST", "/api/chat", json=body) as r:
            r.raise_for_status()
            for line in r.iter_lines():
                if not line:
                    continue
                msg = json.loads(line)
                if "error" in msg:
                    raise RuntimeError(f"ollama: {msg['error']}")
                piece = msg.get("message", {}).get("content", "")
                if piece:
                    if first_ms is None:
                        first_ms = self._clock.now_ms() - start
                    parts.append(piece)
                    delta = reply.feed(piece)
                    if on_reply_delta is not None and (delta or reply.done) and not reply_closed:
                        on_reply_delta(delta, reply.done)
                        reply_closed = reply.done
                if msg.get("done"):
                    final = msg
        full_ms = self._clock.now_ms() - start
        raw = "".join(parts)
        try:
            parsed: dict[str, Any] | None = json.loads(raw)
        except json.JSONDecodeError:
            parsed = None
        eval_count = int(final.get("eval_count", 0))
        eval_ns = int(final.get("eval_duration", 0))
        return LlmResult(
            raw=raw,
            reply=reply.value,
            parsed=parsed,
            first_token_ms=first_ms if first_ms is not None else full_ms,
            full_ms=full_ms,
            eval_tokens=eval_count,
            eval_tokens_per_s=eval_count / (eval_ns / 1e9) if eval_ns else 0.0,
            prompt_tokens=int(final.get("prompt_eval_count", 0)),
        )


def user_message(question: str, transcript: str) -> str:
    return f"Question: {question}\nCandidate answer (transcript): {transcript}"
