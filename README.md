# Semraa AI Voice Interview Platform

Voice interview platform by Semraa Technologies. Launch scope: College + B2C apps, Technical round,
English + Tamil, video recorded for review only.

**Where are we?** See [STATUS.md](STATUS.md). Rules: `Docs/Semraa Engineering Standards – Secure and Fast.pdf`.
Design: `Docs/Semraa AI Voice Interview Platform – Review and Target Architecture.pdf` (sections 5.15, 5.16, 8 win).

## Layout

| Path | What |
|---|---|
| `src/` | .NET 10 modular monolith. `Host/Semraa.Api`, `BuildingBlocks/Semraa.SharedKernel`, `Modules/<Module>/Semraa.<Module>[.Contracts]` |
| `tests/` | xUnit v3 tests, including architecture tests that enforce module boundaries |
| `web/` | Angular 22 workspace: apps `candidate` (B2C) and `college`; libs `@semraa/ui-kit`, `auth`, `api-client`, `interview-runtime`, `reporting` |
| `workers/` | Python 3.12+ uv workspace: `stt`, `tts`, `llm` workers sharing `common` (FastAPI, `/health`, `/ready`) |
| `deploy/dev/` | Docker Compose dev stack: PostgreSQL, PgBouncer, Keycloak, RabbitMQ, Valkey, SeaweedFS, Mailpit, Ollama |
| `.github/workflows/` | CI: build, tests, lint, dependency audit, Gitleaks, Trivy |

## Prerequisites

.NET SDK 10, Node 22 LTS + npm, Python 3.12+ with [uv](https://docs.astral.sh/uv/), Docker Desktop
(NVIDIA Container Toolkit on the GPU machine for Ollama).

## Run locally

```bash
# 1. Infrastructure
cd deploy/dev
cp .env.example .env          # then change the passwords
docker compose up -d          # add "--profile ai" on the GPU machine to start Ollama

# 2. API  (http://localhost:5100/health/live)
dotnet run --project src/Host/Semraa.Api

# 3. Web apps  (candidate on :4200, college on :4201)
cd web && npm ci
npx ng serve candidate
npx ng serve college

# 4. Workers
cd workers && uv sync --all-packages
uv run uvicorn semraa_stt.main:app --port 8101
```

Keycloak admin console: http://localhost:8080 (realm `semraa` is imported on first start).
Mailpit: http://localhost:8025. RabbitMQ: http://localhost:15672.

## Checks (same as CI)

```bash
dotnet build Semraa.slnx -c Release && dotnet test --solution Semraa.slnx -c Release
cd web && npm run lint && npm run format:check && npm run build:all && npm run test:ci
cd workers && uv run ruff check . && uv run mypy common/src stt/src tts/src llm/src && uv run pytest -q
```
