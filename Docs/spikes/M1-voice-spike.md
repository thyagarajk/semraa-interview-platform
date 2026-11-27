# M1 voice spike: results (provisional)

> **Provisional.** Every number below comes from the **dev laptop: NVIDIA GeForce RTX 5050 Laptop GPU, 8 GB VRAM**
> (AMD Ryzen 7 260, 23 GB RAM, Windows 11, driver 610.91). It is not the target GPU machine (RTX 5070 Ti,
> 16 GB). The go/no-go below is provisional and **must be re-run on the RTX 5070 Ti machine** with:
>
> ```powershell
> cd workers
> uv sync --all-packages --extra models --extra tamil
> uv run semraa-spike bench --pipeline-llm qwen3:8b qwen3.5:9b qwen3:14b
> ```
>
> That one command downloads the pinned models (set `HF_TOKEN` for the two gated AI4Bharat models), renders the
> fixtures, runs every benchmark and writes `workers/spike/results/latest.{json,md}`.

Date: 27 Nov 2026. Branch `m1-voice-spike`. Raw results: `workers/spike/results/20261127-170047.json` (final run)
and `20261127-161410.json` (first run, has the qwen3:14b full-turn numbers).

## Summary

| | English | Tamil |
|---|---|---|
| End-of-turn to first AI audio, p50 / p95 (target ≤ 1.5–2 s / ≤ 3 s) | **1.12 s / 1.63 s** ✅ (qwen3:8b) | **3.55 s / 4.72 s** ❌ (qwen3:8b) |
| Final STT error on fixtures | WER 0.0 % (Whisper large-v3-turbo) | WER 21.9 %, CER 4.3 % (IndicConformer) |
| Live captions partial delay p95 (target ≤ 800 ms) | **537 ms** ✅ | no streaming Tamil model available |
| GPU memory peak (8 GB card) | 7.0 GB | 8.1 GB (at the limit) |
| Provisional verdict | **GO** | **NO-GO on this laptop**; decide on the 5070 Ti after the mitigations below |

**Recommendation (provisional):** LLM **qwen3:8b** (Q4_K_M) as the default; 14B does not fit on 8 GB next to STT +
TTS (only 60 % of its layers fit on the GPU, about 6 tokens/s, 9 s to first audio), so the 8B vs 14B decision
moves to the 16 GB machine. Tamil STT: **IndicConformer 600M** (clearly better than Whisper on Tamil). Tamil TTS:
**Indic Parler-TTS** is the only permissively licensed option found, but it is the bottleneck: slower than real time
on this GPU and unreliable on 3 of 10 renders. It needs the mitigations in "Risks" and a re-run on the 5070 Ti.

## How a turn is measured

Cascaded loop, one candidate answer per turn (CLI `semraa-spike`, code in `workers/spike/`):

1. **Silero VAD v6.2.3** on 32 ms frames. End of answer = 1,800 ms of silence (configurable `--silence-ms`, range
   1,500–2,500), with hysteresis (speech ≥ 0.5, silence < 0.35) and a 250 ms minimum speech burst.
2. **STT** on the segmented answer (English: faster-whisper large-v3-turbo on CUDA; Tamil: IndicConformer).
3. **LLM** through Ollama on 127.0.0.1: JSON schema output (`reply`, `intent`, `answer_quality`), temperature 0,
   seed 42, `num_ctx` 4096, thinking off. Prompt: `workers/spike/prompts/interviewer.v1.md`. The `reply` field is
   decoded while it streams.
4. **TTS** sentence by sentence: the first sentence goes to TTS as soon as it is complete (a short opener is released
   at once), later sentences are synthesised while the first one plays. Indic Parler-TTS streams 0.5 s chunks.

Timing starts at the VAD end-of-turn decision. "Last word → first AI audio" adds the 1.8 s silence wait, which is
what the candidate feels. Each pipeline row is 10 fixtures × 3 repeats = 30 turns after one warm-up turn.
GPU memory is the whole device (it includes Ollama's own process), sampled every 50 ms.

## Results: full turn

### English: STT Whisper turbo int8_float16 (CUDA), TTS Kokoro v1.0 fp32 (CPU, 8 threads)

| Stage | qwen3:8b p50 | qwen3:8b p95 | qwen3.5:9b p50 | qwen3.5:9b p95 |
|---|---:|---:|---:|---:|
| VAD end-of-turn (incl. 1.8 s silence wait) | 1,824 | 1,824 | 1,824 | 1,824 |
| STT final | 349 | 358 | 345 | 362 |
| LLM first token | 62 | 67 | 252 | 260 |
| LLM full reply | 1,133 | 1,247 | 1,578 | 1,881 |
| TTS first sentence | 454 | 832 | 654 | 1,246 |
| **End-of-turn → first AI audio** | **1,124** | **1,630** | **1,681** | **2,474** |
| Last word → first AI audio | 2,948 | 3,454 | 3,505 | 4,298 |
| GPU peak (of 8,151 MB) | 7,039 MB | | 7,911 MB | |

All values in ms. JSON valid 30/30 for both. LLM fully on GPU for both.

qwen3:14b (first run, Whisper float16): end-of-turn → first audio p50 **8,954 ms**, p95 10,176 ms; LLM full reply
p50 9,364 ms; only 60 % of the model on the GPU. Not viable on 8 GB.

First run, before tuning (Whisper float16, Kokoro 4 threads): qwen3:8b p50 1,634 / p95 2,596 ms, GPU peak
8,063 MB. Switching Whisper to int8_float16 (same WER, −1.1 GB) and giving Kokoro 8 threads cut p50 by 0.5 s.

### Tamil: STT IndicConformer (CPU, CTC), TTS Indic Parler-TTS fp16 (CUDA, streamed)

| Stage | qwen3:8b p50 | qwen3:8b p95 | qwen3.5:9b p50 | qwen3.5:9b p95 |
|---|---:|---:|---:|---:|
| VAD end-of-turn (incl. 1.8 s silence wait) | 1,824 | 1,824 | 1,824 | 1,824 |
| STT final | 359 | 466 | 364 | 480 |
| LLM first token | 418 | 591 | 1,232 | 1,559 |
| LLM full reply | 5,040 | 8,835 | 6,947 | 9,451 |
| TTS first chunk | 1,096 | 1,376 | 1,203 | 1,402 |
| **End-of-turn → first AI audio** | **3,547** | **4,715** | **3,776** | **4,985** |
| Last word → first AI audio | 5,371 | 6,539 | 5,600 | 6,809 |
| GPU peak (of 8,151 MB) | 8,140 MB | | 7,993 MB | |

Why Tamil is slow here: Tamil text costs several times more tokens per word, so the first sentence takes about
1.5–2 s to generate; Parler-TTS and the LLM share the GPU at the same time (the LLM's full reply takes 5.0 s in the
pipeline against 2.3 s alone); Parler's first chunk takes about 1.1 s; and the card is full (8.14 of 8.15 GB).

## Results: STT accuracy

Corpus WER/CER over 10 fixtures per language (text normalised: case, punctuation; Tamil vowel signs kept).

| Lang | Model | WER | CER | p50 ms | p95 ms | VRAM MB |
|---|---|---:|---:|---:|---:|---:|
| en | faster-whisper large-v3-turbo, CUDA float16 | 0.0 % | 0.0 % | 367 | 410 | 2,327 |
| en | faster-whisper large-v3-turbo, CUDA int8_float16 | 0.0 % | 0.0 % | 319 | 347 | 1,224 |
| en | faster-whisper medium, CUDA int8_float16 | 0.7 % | 0.1 % | 519 | 569 | 1,160 |
| en | faster-whisper small, CUDA int8_float16 | 1.4 % | 0.2 % | 254 | 290 | 424 |
| ta | IndicConformer 600M multilingual, CTC, CPU | **21.9 %** | **4.3 %** | 463 | 576 | 0 |
| ta | faster-whisper large-v3-turbo, CUDA float16 (baseline) | 57.1 % | 15.6 % | 473 | 565 | 1,440 |

Caveats: fixtures are synthetic. English uses Windows OneCore voices (Indian English Ravi and Heera, US Zira, Mark,
David): clean studio-like speech, so 0 % WER is optimistic. Tamil audio comes from Indic Parler-TTS, so some Tamil
errors are TTS artefacts, not STT errors (for example "ஸ்டாக்" came out unclear in ta02). Tamil is agglutinative,
so CER is the fairer measure; most WER errors are one-letter differences or split compounds. Real self-recorded
answers (with Indian accents, noise and code-mixing) are needed before any accuracy decision is final.

## Results: LLM sizing (alone, without STT/TTS loaded)

Ollama 0.40.16, all Q4_K_M, all Apache-2.0 (licence checked with `ollama show --license`). 10 fixture answers each.

| Lang | Model (Ollama id) | On GPU | First token p50 / p95 ms | Full reply p50 / p95 ms | tok/s | JSON valid | VRAM MB |
|---|---|---:|---:|---:|---:|---:|---:|
| en | qwen3:8b (500a1f067a9f) | 100 % | 75 / 82 | 961 / 1,048 | 47.9 | 10/10 | 5,463 |
| en | qwen3.5:9b (56671c2ab938) | 100 % | 241 / 246 | 1,360 / 1,598 | 44.1 | 10/10 | 6,327 |
| en | qwen2.5:7b (845dbda0ea48) | 100 % | 58 / 65 | 840 / 1,048 | 51.0 | 10/10 | 4,633 |
| en | qwen3:14b (bdbd181c33f2) | 60 % | 365 / 391 | 6,621 / 8,141 | 6.1 | 10/10 | 6,007 |
| ta | qwen3:8b | 100 % | 110 / 147 | 2,328 / 3,001 | 47.4 | 10/10 | 5,465 |
| ta | qwen3.5:9b | 100 % | 248 / 255 | 1,701 / 2,006 | 43.9 | 10/10 | 6,327 |
| ta | qwen2.5:7b | 100 % | 87 / 97 | 2,499 / 3,736 | 50.2 | 10/10 | 4,635 |
| ta | qwen3:14b | 60 % | 455 / 513 | 16,915 / 24,031 | 5.8 | 10/10 | 5,989 |

All replies were valid JSON (schema-constrained decoding). English replies are on topic and polite. Tamil replies
from qwen3.5:9b read more natural and shorter than qwen3:8b's (it uses fewer tokens for the same answer), but a
native Tamil speaker must review them; this spike only checks that they are Tamil, on topic and valid JSON.

## Results: live captions (English)

sherpa-onnx streaming Zipformer (`sherpa-onnx-streaming-zipformer-en-2023-06-26`, int8, CPU, 2 threads), 100 ms
chunks, delay measured per emitted token (chunk arrival + compute − token timestamp):

- Partial delay **p50 416 ms, p95 537 ms** (602 tokens) ✅ target p95 ≤ 800 ms. Chunk compute p95 17 ms (real-time
  factor about 0.17).
- WER 18.7 % (no punctuation or casing; tech words such as "chaining" are missed). Fine for captions, which are not
  scored; the final transcript comes from Whisper.
- No streaming Tamil model exists in sherpa-onnx; Tamil captions need another approach (for example chunked
  IndicConformer CTC every 0.5–1 s). Not measured.

## Models, versions and licences

| Use | Model | Pinned version | Format | Licence |
|---|---|---|---|---|
| VAD | Silero VAD v6.2.3 | sha256 `1a153a22…88e3` | ONNX | MIT |
| STT en | faster-whisper large-v3-turbo (mobiuslabsgmbh) | HF `0a363e91` | CTranslate2 | MIT |
| STT en (compared) | faster-whisper medium / small (Systran) | HF `08e178d4` / `536b0662` | CTranslate2 | MIT |
| STT ta | AI4Bharat IndicConformer 600M multilingual | HF `2a77d305` (gated) | ONNX | MIT |
| Captions en | sherpa-onnx streaming Zipformer en 2023-06-26 | sha256 `639e25b5…1282` | ONNX | Apache-2.0 |
| TTS en | Kokoro-82M v1.0 (kokoro-onnx export), voice af_heart | sha256 `7d5df8ec…a6c5` | ONNX | Apache-2.0 |
| TTS ta | AI4Bharat Indic Parler-TTS, speakers Jaya / Kavitha | HF `660bc53c` (gated) | safetensors | Apache-2.0 |
| TTS ta (description tokenizer) | google/flan-t5-large tokenizer | HF `0613663d` | JSON/SentencePiece | Apache-2.0 |
| LLM | qwen3:8b, qwen3.5:9b, qwen2.5:7b, qwen3:14b | Ollama ids above | GGUF Q4_K_M | Apache-2.0 |

Runtimes: faster-whisper 1.2.1, CTranslate2 4.9.1, onnxruntime 1.32.0, sherpa-onnx 2.0.3, kokoro-onnx 0.6.1,
PyTorch 2.11.0+cu128, parler-tts 0.2.3, transformers 4.46.1, jiwer 4.0.0, Ollama 0.40.16.

No pickle checkpoints are loaded. IndicConformer's upstream wrapper needs `trust_remote_code` and a TorchScript
preprocessor (pickle-based); instead the spike re-implements the log-mel front end in NumPy from the TorchScript
source (read as text) and reads its window and filterbank as raw float32 bytes, then runs the ONNX encoder and CTC
head directly. Kokoro's `voices-v1.0.bin` is a NumPy `.npz` loaded with `allow_pickle=False`.

## Risks and follow-ups

1. **Tamil latency (blocker for Tamil).** Mitigations to try on the 5070 Ti, in order:
   (a) prompt the LLM to open with a very short acknowledgement and pre-render a small set of fixed Tamil openers
   ("சரி.", "நல்லது.") so audio starts at once while the rest generates; questions are known in advance and can be
   pre-rendered too; (b) give Parler its own CUDA stream / run it on its own GPU time slice, or try `torch.compile`
   and SDPA attention; (c) on 16 GB the card is no longer full, which alone should remove the contention seen here.
2. **Indic Parler-TTS is slower than real time here** (real-time factor about 1.4: 3.45 s of audio took about 4.9 s),
   so streamed playback would stutter. The 5070 Ti should be about 2–3× faster; re-measure.
3. **Indic Parler-TTS reliability.** 3 of the first 10 Tamil renders were truncated or garbled (both STT models
   agreed on the nonsense); swapping speaker fixed them. Production needs a guard, for example an IndicConformer
   round-trip check on each synthesised sentence with a retry, and a native-speaker listening test.
4. **8 GB is at the limit.** Tamil turns peaked at 8.14 of 8.15 GB. Any extra load on the laptop spills into
   shared memory and latency jumps (seen with qwen3.5:9b in the first run). Use the laptop for development only.
5. **Licences to review:** Kokoro's G2P uses espeak-ng (via espeakng-loader) and phonemizer, both **GPL-3.0**. Fine
   for a server we run ourselves (no distribution), but legal should confirm. sherpa-onnx 2.x has an Apache-only
   Kokoro path but it is lexicon-only and silently drops unknown words ("Kubernetes"), so it was rejected.
6. The flan-t5-large tokenizer that Parler-TTS fetches at load is now pinned to revision `0613663d`; the numbers
   above were measured just before the pin, with the latest revision at that time.
7. **Accuracy needs real speech.** Record about 10 English and 10 Tamil answers from team members (with consent,
   kept out of git or stored as approved test data) and re-run WER; add noise and code-mixed answers.
8. **IndicConformer successor.** Its model card now recommends bodhan-ai "Indic-Transcribe" (25 languages); check
   its licence and compare on the GPU machine.
9. **Tamil live captions** are not covered (no streaming Tamil model); prototype chunked CTC in M3.
10. **VAD silence wait** (1.8 s) is the largest part of what the candidate feels. Tune 1.5–2.5 s with real users;
    a smarter end-of-turn signal (for example the LLM judging if the answer is complete) could cut it.
11. **Microphone mode** (`semraa-spike run --mic`) is built but was not tested here (no one at the laptop).

## Go / no-go (provisional)

- **English: GO.** Every target is met with margin on an 8 GB laptop GPU: end-of-turn → first audio p50 1.1 s,
  p95 1.6 s; captions p95 0.54 s; STT accurate on clean speech.
- **Tamil: NO-GO on the 8 GB laptop** (p50 3.5 s, p95 4.7 s against ≤ 2 s / ≤ 3 s). STT is good (IndicConformer);
  TTS speed and the shared GPU are the problem. Decide on the RTX 5070 Ti after mitigations 1(a)–(c); if Tamil still
  misses p95 ≤ 3 s there, launch Tamil with pre-rendered questions and openers, and revisit the TTS model.
- **LLM size:** qwen3:8b now. Compare with qwen3:14b and qwen3.5:9b on the 16 GB machine for both latency and
  interview quality (a rubric-scored comparison belongs in M2).

## Reproduce

```powershell
cd workers
uv sync --all-packages --extra models --extra tamil   # model runtimes; CI installs only the light core
$env:HF_TOKEN = [Environment]::GetEnvironmentVariable('HF_TOKEN','User')  # gated AI4Bharat models
uv run semraa-spike bench                              # everything; writes spike/results/latest.{json,md}
uv run semraa-spike run --wav spike/fixtures/audio/en02.wav --question "How does a hash map work?" --play
uv run semraa-spike run --mic --lang en               # live loop; Ctrl+C to stop
```

Ollama must listen on 127.0.0.1 only. The spike logs no transcripts or audio; `run --show-text` prints them to the
console on request.
