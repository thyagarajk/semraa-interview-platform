# Semraa AI Voice Interview Platform – Status

> One-page "where are we" file. Update it at the end of every work session and every milestone.
> Last updated: 27 Nov 2026

## Current position

- **Phase:** Planning complete. No code written yet.
- **Local folder:** `Z:\Semraa\semraa-interview-platform` holds only `Docs/` (2 PDFs). It is not yet a git repository.
- **GitHub:** `github.com/thyagarajk/semraa-interview-platform` exists, is public and has no commits.
- **Waiting on:** Thyagu to approve the next milestone (see "Next steps").

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

## Milestones

Roadmap from architecture doc section 7. Each milestone needs Thyagu's review and approval before the next starts.

| # | Milestone | Status |
|---|---|---|
| P | Planning: architecture review, decisions, engineering standards | ✅ Done (27 Nov 2026) |
| M0 | Repo foundation: git + GitHub, solution/workspace skeletons, standards tooling, docker compose dev stack, CI | ⏳ Proposed next |
| M1 | Spike (gate): voice loop on GPU machine, English + Tamil, measure latency / STT error / caption delay, choose LLM size and Tamil models | ⬜ Not started |
| M2 | Thin vertical slice: Keycloak + OTP, College app (CSV import, one campaign type), B2C app (sign-up, practice), audio + text modes, final transcription, rubric evaluation, reports, manual invoicing. Pilot. | ⬜ Not started |
| M3 | Hardening for scale: live captions, scheduling + capacity, review queue, credit ledger + allotments, Razorpay sandbox, maker-checker payments, admission control | ⬜ Not started |
| M4 | B2B HR (Hiring app), integrity flags, fairness reporting, pricing admin console | ⬜ Not started |
| M5 | Production readiness: load/security tests, privacy review, runbooks, backup/DR drills, payment live-mode review | ⬜ Not started |

## Next steps

1. Thyagu approves M0 scope (or chooses to start with the M1 spike).
2. `git init` the local folder, connect to the GitHub repo, first commit (Docs + this file).
3. Build M0 (see proposal below), open a PR for review.

### M0 proposal (for approval)

- `.gitignore`, `.editorconfig`, `Directory.Build.props` (nullable, warnings as errors, analyzers), `Directory.Packages.props`.
- `src/` .NET 10 solution: API host + first platform module skeletons (Identity & Access, Tenant) with Contracts projects and architecture tests.
- `web/` Angular 22 workspace: `candidate` and `college` apps, libs `ui-kit`, `auth`, `api-client`, `interview-runtime` (empty shells, strict TS, ESLint, bundle budgets).
- `workers/` Python 3.12 + uv: `stt`, `tts`, `llm` service shells with `/health` and `/ready`.
- `deploy/docker-compose.dev.yml`: PostgreSQL, PgBouncer, Keycloak, RabbitMQ, Valkey, SeaweedFS, Mailpit, Ollama; non-root, pinned images.
- CI (GitHub Actions free tier): build + test, Gitleaks, dependency audit, Trivy.

## Open questions (from architecture doc section 8)

- Question-bank tagging (topic, expected concepts, difficulty, company type).
- Legal review of consent and retention; who signs off.
- Payment methods and whether prices are GST-inclusive.
- Final price numbers per tier and pack.
- Pilot college and B2C beta group.
- Team size and target dates.

## Change log

- 27 Nov 2026 – Status file created. Project state mapped: docs only, no code.
