Machine: NVIDIA GeForce RTX 5050 Laptop GPU (8151 MB), Windows-11-10.0.26200-SP0

### Turn latency - en - LLM qwen3:8b - STT turbo-int8 (30 turns, silence 1800 ms)

STT: faster-whisper/faster-whisper-large-v3-turbo (cuda, int8_float16); TTS: kokoro-v1.0/kokoro-v1.0.onnx (af_heart, cpu x8)

| Stage | p50 ms | p95 ms | max ms |
|---|---:|---:|---:|
| VAD end-of-turn (incl. silence wait) | 1,824 | 1,824 | 1,824 |
| STT final | 349 | 358 | 363 |
| LLM first token | 62 | 67 | 76 |
| LLM full reply | 1,133 | 1,247 | 1,277 |
| TTS first sentence | 454 | 832 | 852 |
| **End-of-turn -> first AI audio** | 1,124 | 1,630 | 1,659 |
| Last word -> first AI audio | 2,948 | 3,454 | 3,483 |

WER 0.0%, CER 0.0%; JSON valid 30/30; LLM on GPU 1.0; GPU peak 7,039 / 8,151 MB

### Turn latency - en - LLM qwen3.5:9b - STT turbo-int8 (30 turns, silence 1800 ms)

STT: faster-whisper/faster-whisper-large-v3-turbo (cuda, int8_float16); TTS: kokoro-v1.0/kokoro-v1.0.onnx (af_heart, cpu x8)

| Stage | p50 ms | p95 ms | max ms |
|---|---:|---:|---:|
| VAD end-of-turn (incl. silence wait) | 1,824 | 1,824 | 1,824 |
| STT final | 345 | 362 | 363 |
| LLM first token | 252 | 260 | 264 |
| LLM full reply | 1,578 | 1,881 | 1,885 |
| TTS first sentence | 654 | 1,246 | 1,293 |
| **End-of-turn -> first AI audio** | 1,681 | 2,474 | 2,514 |
| Last word -> first AI audio | 3,505 | 4,298 | 4,338 |

WER 0.0%, CER 0.0%; JSON valid 30/30; LLM on GPU 1.0; GPU peak 7,911 / 8,151 MB

### Turn latency - ta - LLM qwen3:8b - STT indic-conformer (30 turns, silence 1800 ms)

STT: indic-conformer-600m (ta, ctc, CPU); TTS: indic-parler-tts (cuda, torch.float16), streamed 0.5 s chunks

| Stage | p50 ms | p95 ms | max ms |
|---|---:|---:|---:|
| VAD end-of-turn (incl. silence wait) | 1,824 | 1,824 | 1,824 |
| STT final | 359 | 466 | 503 |
| LLM first token | 418 | 591 | 664 |
| LLM full reply | 5,040 | 8,835 | 9,581 |
| TTS first sentence | 1,096 | 1,376 | 1,506 |
| **End-of-turn -> first AI audio** | 3,547 | 4,715 | 4,830 |
| Last word -> first AI audio | 5,371 | 6,539 | 6,654 |

WER 21.0%, CER 4.4%; JSON valid 30/30; LLM on GPU 1.0; GPU peak 8,140 / 8,151 MB

### Turn latency - ta - LLM qwen3.5:9b - STT indic-conformer (30 turns, silence 1800 ms)

STT: indic-conformer-600m (ta, ctc, CPU); TTS: indic-parler-tts (cuda, torch.float16), streamed 0.5 s chunks

| Stage | p50 ms | p95 ms | max ms |
|---|---:|---:|---:|
| VAD end-of-turn (incl. silence wait) | 1,824 | 1,824 | 1,824 |
| STT final | 364 | 480 | 539 |
| LLM first token | 1,232 | 1,559 | 1,723 |
| LLM full reply | 6,947 | 9,451 | 9,608 |
| TTS first sentence | 1,203 | 1,402 | 1,532 |
| **End-of-turn -> first AI audio** | 3,776 | 4,985 | 5,312 |
| Last word -> first AI audio | 5,600 | 6,809 | 7,136 |

WER 21.0%, CER 4.4%; JSON valid 30/30; LLM on GPU 1.0; GPU peak 7,993 / 8,151 MB

### STT accuracy and latency

| Lang | Model | WER | CER | p50 ms | p95 ms | VRAM MB |
|---|---|---:|---:|---:|---:|---:|
| en | faster-whisper/faster-whisper-large-v3-turbo (cuda, float16) | 0.0% | 0.0% | 367 | 410 | 2,327 |
| en | faster-whisper/faster-whisper-large-v3-turbo (cuda, int8_float16) | 0.0% | 0.0% | 319 | 347 | 1,224 |
| en | faster-whisper/faster-whisper-medium (cuda, int8_float16) | 0.7% | 0.1% | 519 | 569 | 1,160 |
| en | faster-whisper/faster-whisper-small (cuda, int8_float16) | 1.4% | 0.2% | 254 | 290 | 424 |
| ta | indic-conformer-600m (ta, ctc, CPU) | 21.9% | 4.3% | 463 | 576 | 0 |
| ta | faster-whisper/faster-whisper-large-v3-turbo (cuda, float16) | 57.1% | 15.6% | 473 | 565 | 1,440 |

### LLM sizing (Ollama, num_ctx 4096, temperature 0, seed 42)

| Lang | Model | Quant | On GPU | First token p50/p95 ms | Full p50/p95 ms | tok/s | JSON | VRAM MB |
|---|---|---|---:|---:|---:|---:|---:|---:|
| en | qwen3:8b | Q4_K_M | 1.0 | 75 / 82 | 961 / 1,048 | 47.9 | 10/10 | 5,463 |
| en | qwen3.5:9b | Q4_K_M | 1.0 | 241 / 246 | 1,360 / 1,598 | 44.1 | 10/10 | 6,327 |
| en | qwen2.5:7b | Q4_K_M | 1.0 | 58 / 65 | 840 / 1,048 | 51.0 | 10/10 | 4,633 |
| en | qwen3:14b | Q4_K_M | 0.604 | 365 / 391 | 6,621 / 8,141 | 6.1 | 10/10 | 6,007 |
| ta | qwen3:8b | Q4_K_M | 1.0 | 110 / 147 | 2,328 / 3,001 | 47.4 | 10/10 | 5,465 |
| ta | qwen3.5:9b | Q4_K_M | 1.0 | 248 / 255 | 1,701 / 2,006 | 43.9 | 10/10 | 6,327 |
| ta | qwen2.5:7b | Q4_K_M | 1.0 | 87 / 97 | 2,499 / 3,736 | 50.2 | 10/10 | 4,635 |
| ta | qwen3:14b | Q4_K_M | 0.604 | 455 / 513 | 16,915 / 24,031 | 5.8 | 10/10 | 5,989 |

### Live captions (English)

sherpa-onnx/sherpa-onnx-streaming-zipformer-en-2023-06-26 (cpu x2), 100 ms chunks: partial delay p50 416 ms, p95 537 ms (n=602 tokens); chunk compute p95 17.4 ms; WER 18.7%


