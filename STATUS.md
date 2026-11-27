# Semraa AI Voice Interview Platform – Status

> One-page "where are we" file. Update it at the end of every work session and every milestone.
> Last updated: 27 Nov 2026

## Current position

- **Phase:** M1 voice spike done **provisionally on the dev laptop** (RTX 5050, 8 GB), on branch `m1-voice-spike`
  (not merged). Must be re-run on the RTX 5070 Ti 16 GB machine before the go/no-go is final.
- **GitHub:** `github.com/thyagarajk/semraa-interview-platform`. `main` has M0 (merged, PR #1).
- **Local folder:** `Z:\Semraa\semraa-interview-platform` is a git working copy of the repo.
- **Waiting on:** Thyagu to review the M1 spike report (`Docs/spikes/M1-voice-spike.md`) and run the re-run on the GPU machine.

## Source documents (read these for detail)

| Document | Where | What to read |
|---|---|---|
| Review and Target Architecture | `Docs/Semraa AI Voice Interview Platform – Review and Target Architecture.pdf` | 5.15 (stack + hardware), 5.16 (dynamic config, pluggable providers), 8 (decisions). These win over older sections (e.g. SQL Server, hosted LLM, cloud regions). |
| Engineering Standards – Secure and Fast | `Docs/Semraa Engineering Standards – Secure and Fast.pdf` | MUST rules for C#, EF Core, PostgreSQL, Angular, real-time, Python, CI. Section 10 = PR checklist / Definition of Done. |

## Decisions in force (summary)

- Free/open source only. .NET 10 LTS, Angular 22, PostgreSQL + PgBouncer (RLS), RabbitMQ, Valkey, SeaweedFS/Garage, Keycloak, OpenTelemetry/Prometheus/Grafana/Loki.
- AI: Ollama (dev) → vLLM/llama.cpp; faster-whisper (English final), IndicConformer (Tamil), sherpa-onnx (live captions), Silero VAD; Kokoro (English TTS), Indic Parler-TTS (Tamil).
- Prices, plans, entitlements, policies, rubric weights = versioned data. Code calls `HasFeature`/`GetLimit`, never checks plan names.
- Providers pluggable per tenant via `TenantProviderSetting` + `ProviderResolver` (keyed services); one project per adapter; Azure adapters later.
- Launch: College + B2C apps, Technical round only, English + Tamil, video recorded for review (never scored).
- Rubric: Correctness 35, Depth 25, Problem-solving 20, Relevance/structure 10, Clarity 10; scale 1–5; score /100 + level.
- Consent/age/retention rules per section 8 (legal review before pilot).
- Hardware: laptop for dev; GPU machine (RTX 5070 Ti 16 GB) for voice/AI tests, 1 concurrent interview.

## Design standard (Thyagu, 27 Nov 2026)

The UI must look stunning and beautiful, not just functional. From M2 on, every screen gets a real design pass:
a shared design system in `@semraa/ui-kit` (colour tokens with light and dark themes, typography scale, spacing,
motion), polished components, considered empty/loading/error states, and responsive layouts that stay fast on a
cheap Android phone and a college lab PC (bundle budgets and accessibility still apply). Screens are reviewed with
screenshots before merge.

## Milestones

Roadmap from architecture doc section 7. Each milestone needs Thyagu's review and approval before the next starts.

| # | Milestone | Status |
|---|---|---|
| P | Planning: architecture review, decisions, engineering standards | ✅ Done (27 Nov 2026) |
| M0 | Repo foundation: git + GitHub, solution/workspace skeletons, standards tooling, docker compose dev stack, CI | ✅ Done (merged, PR #1) |
| M1 | Spike (gate): voice loop on GPU machine, English + Tamil, measure latency / STT error / caption delay, choose LLM size and Tamil models | 🟡 Provisional (laptop run done; re-run on GPU machine needed) |
| M2 | Thin vertical slice: Keycloak + OTP, College app (CSV import, one campaign type), B2C app (sign-up, practice), audio + text modes, final transcription, rubric evaluation, reports, manual invoicing. Pilot. | ⬜ Not started |
| M3 | Hardening for scale: live captions, scheduling + capacity, review queue, credit ledger + allotments, Razorpay sandbox, maker-checker payments, admission control | ⬜ Not started |
| M4 | B2B HR (Hiring app), integrity flags, fairness reporting, pricing admin console | ⬜ Not started |
| M5 | Production readiness: load/security tests, privacy review, runbooks, backup/DR drills, payment live-mode review | ⬜ Not started |

## M1 voice spike: provisional results (laptop, RTX 5050 8 GB)

Full report: `Docs/spikes/M1-voice-spike.md`. Code: `workers/spike/` (CLI `semraa-spike`). Raw numbers: `workers/spike/results/`.

- **English: GO (provisional).** End-of-turn to first AI audio p50 1.12 s, p95 1.63 s (target ≤ 1.5–2 s / ≤ 3 s) with
  Whisper large-v3-turbo int8 + qwen3:8b + Kokoro v1.0. STT WER 0 % on clean synthetic fixtures. Live captions
  (sherpa-onnx Zipformer) partial delay p95 537 ms (target ≤ 800 ms). GPU peak 7.0 GB.
- **Tamil: NO-GO on the laptop.** p50 3.55 s, p95 4.72 s. IndicConformer STT is good (WER 21.9 %, CER 4.3 %; Whisper
  57 % / 16 %). Indic Parler-TTS is the bottleneck: slower than real time on this GPU, 3/10 renders garbled, and it
  shares a full 8 GB card with the LLM. Mitigations listed in the report.
- **LLM size:** qwen3:8b (Q4_K_M, Apache-2.0) for now. qwen3:14b does not fit on 8 GB with STT + TTS (60 % on GPU,
  9 s to first audio); the 8B vs 14B decision moves to the 16 GB machine.
- Licence flag for legal: Kokoro's G2P uses espeak-ng and phonemizer (GPL-3.0); fine for a self-run server.

## Next steps

1. Thyagu follows the step-by-step guide `Docs/guides/M1-your-steps.md` (GPU re-run, real recordings, Tamil review, licence check). Also reviews `Docs/spikes/M1-voice-spike.md` and PR #2.
2. Re-run M1 on the RTX 5070 Ti machine with one command (see the report's top box): `uv sync --all-packages --extra models --extra tamil`, then `uv run semraa-spike bench --pipeline-llm qwen3:8b qwen3.5:9b qwen3:14b`.
3. Try the Tamil mitigations there (short pre-rendered openers and questions, Parler on its own GPU time, `torch.compile`), and record ~10 real English and Tamil answers (with consent) for a real WER.
4. Decide go/no-go for Tamil and the LLM size (8B vs 14B), then open the M1 PR and start M2.

### What M0 contains

- Root: `.editorconfig`, `.gitattributes`, `.gitignore`, `global.json` (.NET 10, Microsoft Testing Platform), `Directory.Build.props` (nullable, warnings as errors, latest-recommended analyzers), `Directory.Packages.props` (central versions), `Semraa.slnx`.
- `src/`: `Semraa.Api` host (deny-by-default auth, Keycloak JWT validation with 30 s skew, ProblemDetails, rate limiter, security headers, `/health/live` and `/health/ready`, `/api/v1/identity/me`); `Semraa.SharedKernel` (`Result<T>`, `DomainError`, `TenantId`/`UserId` with UUIDv7, `ITenantContext`); modules Identity and Tenancy with Contracts projects (`TenantProviderSetting` for per-tenant providers).
- `tests/`: 13 tests (shared kernel, API smoke tests for deny-by-default and security headers, architecture tests for module boundaries and sealed classes).
- `web/`: Angular 22.3 workspace, apps `candidate` (:4200) and `college` (:4201), libs `@semraa/ui-kit`, `auth` (correlation id + idempotency-key interceptor), `api-client`, `interview-runtime` (`AudioTransport` interface), `reporting` (readiness levels). Strict TS + `noUncheckedIndexedAccess`, angular-eslint (bans `any`, `innerHTML`, `bypassSecurityTrust*`), Prettier, Vitest, 300 kB initial bundle budget.
- `workers/`: uv workspace (`common`, `stt`, `tts`, `llm`), FastAPI with `/health` + `/ready`, ruff, mypy strict, pytest. Placeholder models only; real models in M1.
- `deploy/dev/`: Docker Compose with pinned versions, localhost-only ports, separate DB owner/app roles, Keycloak realm `semraa` with PKCE clients for both apps.
- `.github/`: CI workflow (build/test/lint for all three stacks, dependency audits, Gitleaks, Trivy, ShellCheck) and a PR template with the Definition of Done.

### Known follow-ups (not in M0)

- Pin Docker images by digest (tags pinned now); add Renovate.
- PostgreSQL row-level security, EF Core DbContexts and the outbox arrive with the first owned tables (M2).
- Semgrep, SonarQube, Syft SBOM and OWASP ZAP stages are added when there is deployable code to scan (M2).
- Branch protection on `main` (PR + green CI) to switch on in GitHub settings after merge.

## Open questions (from architecture doc section 8)

- Question-bank tagging (topic, expected concepts, difficulty, company type).
- Legal review of consent and retention; who signs off.
- Payment methods and whether prices are GST-inclusive.
- Final price numbers per tier and pack.
- Pilot college and B2C beta group.
- Team size and target dates.

## Change log

- 27 Nov 2026 – Status file created. Project state mapped: docs only, no code.
- 27 Nov 2026 – Git set up, first commit pushed to `main`. M0 built and opened as a PR.
- 27 Nov 2026 – Thyagu set the design standard (stunning, beautiful UI) and approved merging M0.
- 27 Nov 2026 – M1 voice spike built and run provisionally on the 8 GB laptop (branch `m1-voice-spike`): English GO, Tamil NO-GO on the laptop; re-run on the RTX 5070 Ti pending.
