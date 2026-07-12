# Testing

Integration teams should test against the platform at three levels.

## 1. Unit tests (your side)

Test your **request builder** and **response parser** in isolation:

* Constructs the correct headers (`x-tenant-id`, `x-principal-id`).
* Rejects standard workflow/API envelopes without the expected `trace_id` and
  `success` fields. Health endpoints use `HealthResponse` instead and are not
  wrapped in that envelope.
* Parses both success (`status: "SUCCESS"`) and error envelopes.

## 2. Contract tests

Spin up a **stub** that returns canned platform responses and verify your
code paths:

| Scenario | Stub response |
|----------|---------------|
| Submission accepted | HTTP 202 + `QueuedWorkflowResponse` |
| Validation error | HTTP 422 + `error.code = validation_error` |
| Quota exceeded | HTTP 429 + `Retry-After` |
| Workflow running | HTTP 200 + `status: RUNNING` |
| Workflow success | HTTP 200 + `status: SUCCESS`, `result: {...}` |
| Workflow failed (retriable) | HTTP 200 + `status: FAILED`, then later `RUNNING` |
| Workflow dead | HTTP 200 + `status: DEAD`, `error: {...}` |
| Waiting on tool | HTTP 200 + `status: WAITING_TOOL`, `pending_action.tool_name` |
| Waiting on approval | HTTP 200 + `status: WAITING_APPROVAL`, `pending_action.approval_type` |

## 3. Integration tests against staging

Run the eight [integration examples](integration-guide.md) end-to-end in
the staging environment:

* Email automation
* Telegram bot
* WhatsApp
* Job automation
* OCR / document intelligence
* Calendar scheduling
* CRM follow-ups
* Runtime custom workflow submission

For each, verify:

* The workflow reaches `SUCCESS` within the configured `timeout_seconds`.
* The `result` shape matches your parser’s expectations.
* Tool callbacks succeed under both happy and error paths.
* Approval callbacks succeed for both approve and reject.

For a local full-stack Docker run, use the repository E2E harness:

```powershell
docker compose -f docker-compose.yml -f docker-compose.e2e.yml down -v --remove-orphans
docker compose -f docker-compose.yml -f docker-compose.e2e.yml up -d postgres redis api worker
python scripts/docker_e2e_smoke.py
```

It runs against API, worker, Postgres, Redis, real Gemini, and real
OpenRouter fallback. By default the harness uses `E2E_SCENARIO_SET=core`,
which keeps provider-backed calls to a small smoke path. Use
`E2E_SCENARIO_SET=full` only when your selected Gemini/OpenRouter quota can
handle the larger provider-heavy matrix.

Before workflow scenarios run, the harness waits for `/health/ready` to return
`status: "ok"` and verifies
`postgresql`, `redis`, `event_store`, `workflow_queue`, `workflow_worker`,
`provider:gemini`, and `provider:openrouter`. Request and response logs are written to
`logs/docker-e2e/<timestamp>/requests.jsonl`, with a summary in
`logs/docker-e2e/<timestamp>/summary.md`.

By default the harness omits the request-level `provider` block so the API uses
its env-driven workflow defaults. Set `E2E_WORKFLOW_PROVIDER` and optionally
`E2E_WORKFLOW_MODEL` only when you need an explicit override. Legacy
`E2E_OPENROUTER_MODEL` still works and implies `provider=openrouter`.
Real upstream models can be slower or rate-limited, so the harness uses
`E2E_POLL_TIMEOUT_SECONDS=180` and `E2E_PROVIDER_COOLDOWN_SECONDS=20` by
default. Set
`E2E_WORKFLOW_TIMEOUT_SECONDS` only when a run needs custom per-workflow API
timeouts; otherwise the server default applies.
Dead-letter coverage uses a workflow timeout path so provider traffic remains
real provider traffic throughout the run.

For exhaustive real-scenario validation across all legacy and plugin workflows,
run the full smoke harness in strict mode:

```powershell
$env:E2E_SKIP_PROVIDERS  = "1"
$env:E2E_LEGACY_PROVIDER = "openai"
$env:E2E_LEGACY_MODEL    = "gemma4:31b-cloud"
$env:E2E_PLUGIN_PROVIDER = "openai"
$env:E2E_PLUGIN_MODEL    = "gemma4:31b-cloud"
$env:E2E_SCENARIO_VARIANTS = "baseline,context_rich,urgent,audit_ready"
$env:E2E_POLL_TIMEOUT_SECONDS = "1200"
$env:E2E_PLUGIN_ACCEPT_FAILED = "0"
python scripts/full_smoke_test.py
```

Use `E2E_SKIP_PROVIDERS=0` only when you explicitly want Phase 1 provider
probe coverage. On some real upstreams, provider probes can stay `RUNNING`
until timeout even when workflow phases are healthy.

For production-readiness validation inside this repository, run the unified
operational harness after the stack is healthy:

```powershell
python scripts/platform_validation.py --mode smoke --output-dir logs/platform-validation/smoke
python scripts/platform_validation.py --mode full --output-dir logs/platform-validation/full
```

The harness validates:

* API startup and `/health`.
* `/metrics`, PostgreSQL, Redis, migrations, prompt loading, pgvector, and WebSocket startup.
* Workflow execution across email, Telegram, WhatsApp, CRM, job automation, OCR, calendar, document intelligence, and multi-agent flows.
* 500-concurrency, 1000-concurrency, workflow burst, webhook burst, and dead-letter replay load profiles.
* High-input compression and chunking for OCR documents, long email threads, resumes, CRM histories, and huge context windows.
* Memory and RAG behaviors including vector search, metadata filtering, hybrid retrieval, reranking, semantic cache hits, and embedding cache hits.
* Redis outage, worker crash, PostgreSQL pause, and optional command-driven provider or queue fault injection.

Reports are written to the selected output directory as `summary.json`,
`smoke-test-report.md`, `stress-test-report.md`, `concurrency-report.md`,
`bottleneck-analysis.md`, `failure-analysis.md`, and
`scaling-recommendations.md`. See [load-testing.md](load-testing.md) and
[performance.md](performance.md) for the full operator workflow.

## 4. Negative tests

| Test | Expected |
|------|----------|
| Submit with payload > 256 KiB | 422 `validation_error` |
| Submit with 51 `context_ids` | 422 |
| Submit with unknown `workflow` | 422 |
| Submit with `provider=anthropic` and `required_capability=embed` | 422 |
| Poll for a workflow in another tenant | 404 |
| Deliver tool/approval callback after the workflow left the waiting state | 409 `workflow_state_conflict` |

## 5. Load tests

Generate load that mirrors your production mix. Start with:

* 100 RPS sustained for 10 minutes.
* 2× burst for 60 seconds.
* 1% error injection (refusal, retriable failure).
* Mixed workflows weighted by your actual product traffic.

Verify:

* `success` rate ≥ 99% (excluding intentional failures).
* p95 time-to-`SUCCESS` within your SLO.
* No tenant-side queue growth (your producers stay up).
* HTTP 429 honors `Retry-After` (you back off correctly).

The repository includes a k6 smoke/soak script at
[`load/k6-workflows.js`](../load/k6-workflows.js). See
[`load/README.md`](../load/README.md) for command examples.

The k6 script now exposes explicit `concurrency_500`, `concurrency_1000`,
`workflow_burst`, `webhook_burst`, and `dead_letter_replay_burst` profiles.
Enable sampled completion polling with `ENABLE_STATUS_POLLING=true` and tune the
per-profile sample rates with `CONCURRENCY_500_SAMPLE_RATE` and
`CONCURRENCY_1000_SAMPLE_RATE`.

## 6. Chaos and failure injection

Simulate (on your side):

* Tool service down → workflows time out and retry; your fallback logic
  fires after `DEAD`.
* Approval service slow → workflows hit `WORKFLOW_TIMEOUT`; you escalate.
* Polling watcher restart → no duplicates because of idempotent watchers.

Coordinate with the platform team to simulate (on platform side):

* Provider outage (Anthropic down).
* Redis queue blip.
* Postgres failover.

The repository harness accepts optional command hooks for platform-side chaos so
the same test plan can be used with Docker, `kubectl`, or external fault
injection tools:

* `PLATFORM_FAULT_PROVIDER_TIMEOUT_INJECT` / `PLATFORM_FAULT_PROVIDER_TIMEOUT_RESTORE`
* `PLATFORM_FAULT_MALFORMED_PROVIDER_INJECT` / `PLATFORM_FAULT_MALFORMED_PROVIDER_RESTORE`
* `PLATFORM_FAULT_QUEUE_INJECT` / `PLATFORM_FAULT_QUEUE_RESTORE`

Set `RUN_TESTCONTAINERS=1` to enable the optional Docker-backed Redis/Postgres
smoke test in `tests/integration/test_testcontainers_smoke.py`.

## 7. Observability validation

For a sample workflow:

* You can find every log line by `trace_id` in your sink.
* OpenTelemetry trace spans for your request appear linked to the
  platform’s.
* Prometheus `request_total{workflow="…"}` increments on submission.
* The corresponding `ai_generations` and `audit_logs` rows exist (audit
  query via the admin console).

## 8. Test data hygiene

* Never use real customer PII in non-prod environments.
* Use deterministic seeds for fixture generation.
* Reset tenant state via the admin runbook between test runs.

## 9. CI gates

Recommended gates for your integration repo:

* All contract tests pass.
* Integration suite (against staging) green on PR.
* Load test smoke run nightly.
* `production-checklist.md` lint passes before tagging a release.
