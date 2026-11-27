## What and why

## How it was tested

## Definition of Done (Engineering Standards, section 10)

### Security
- [ ] Endpoint or hub has an explicit authorization policy and a tenant or owner check
- [ ] Inputs validated; outputs encoded; no raw SQL concatenation; no innerHTML with user or AI text
- [ ] No secrets, personal data, tokens or transcripts in code or logs
- [ ] Credit, payment and state-changing calls are idempotent and audited
- [ ] New dependency justified, licence checked (free/open source, no non-commercial terms), no known CVEs

### Performance
- [ ] No N+1 queries; lists are paged; new queries on large tables have an index and a checked plan
- [ ] Async end to end with cancellation; heavy work moved to a queue
- [ ] Angular bundle budget still green; heavy UI deferred
- [ ] Voice-path change measured against the latency budget

### Quality
- [ ] Unit tests for the logic; integration test for the endpoint; tenant-isolation test for any new owned table
- [ ] Migration is backward compatible and has a rollback plan
- [ ] Metrics, traces and structured logs added for the new path
- [ ] API contract (OpenAPI) and docs updated
- [ ] STATUS.md updated
