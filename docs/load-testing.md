# Load Testing

The repository now ships two complementary load-testing lanes:

- [scripts/platform_validation.py](../scripts/platform_validation.py): Python operational harness for smoke, concurrency, high-input, memory/RAG, resilience, and report generation.
- [load/k6-workflows.js](../load/k6-workflows.js): k6 submission-pressure lane for sustained traffic, exact 500/1000 concurrent submissions, webhook bursts, and replay bursts.

## Python Harness

Use the Python harness when you need the platform to validate more than raw
HTTP throughput. It performs:

- API startup, health, metrics, PostgreSQL, Redis, migrations, prompt registry, pgvector, and WebSocket smoke checks.
- Sequential smoke runs across email, Telegram, WhatsApp, CRM, job automation, OCR, calendar, document intelligence, and multi-agent workflows.
- 500-concurrency, 1000-concurrency, workflow burst, webhook burst, and dead-letter replay profiles.
- High-input validation for OCR-scale documents, long email threads, large resumes, large CRM histories, and huge context windows.
- Memory and RAG checks for vector search, metadata filtering, hybrid retrieval, reranking, semantic cache hits, and embedding cache hits.
- Resilience drills for Redis outage, worker crash, PostgreSQL pause, and optional externally injected provider/queue faults.

Run smoke only:

```powershell
python scripts/platform_validation.py --mode smoke --output-dir logs/platform-validation/smoke
```

Run the full suite:

```powershell
python scripts/platform_validation.py --mode full --output-dir logs/platform-validation/full
```

Optional fault-injection hooks are exposed through environment variables so the
same harness can be used with Docker, `kubectl`, or external chaos tooling:

- `PLATFORM_FAULT_PROVIDER_TIMEOUT_INJECT`
- `PLATFORM_FAULT_PROVIDER_TIMEOUT_RESTORE`
- `PLATFORM_FAULT_MALFORMED_PROVIDER_INJECT`
- `PLATFORM_FAULT_MALFORMED_PROVIDER_RESTORE`
- `PLATFORM_FAULT_QUEUE_INJECT`
- `PLATFORM_FAULT_QUEUE_RESTORE`

Each run writes:

- `summary.json`
- `smoke-test-report.md`
- `stress-test-report.md`
- `concurrency-report.md`
- `bottleneck-analysis.md`
- `failure-analysis.md`
- `scaling-recommendations.md`

## k6 Profiles

Use k6 when you need long-running submission pressure or when the platform is
already running in a staging or canary environment.

Default smoke and peak:

```bash
k6 run -e BASE_URL=https://staging-api.example.com \
  -e TENANT_ID=tenant_load_test \
  -e ENABLE_STATUS_POLLING=true \
  load/k6-workflows.js
```

Enable exact 500 and 1000 concurrent submissions:

```bash
k6 run -e BASE_URL=https://staging-api.example.com \
  -e TENANT_ID=tenant_load_test \
  -e ENABLE_CONCURRENCY_500=true \
  -e ENABLE_CONCURRENCY_1000=true \
  -e ENABLE_STATUS_POLLING=true \
  -e CONCURRENCY_500_SAMPLE_RATE=0.2 \
  -e CONCURRENCY_1000_SAMPLE_RATE=0.1 \
  load/k6-workflows.js
```

Enable workflow and webhook bursts:

```bash
k6 run -e BASE_URL=https://staging-api.example.com \
  -e TENANT_ID=tenant_load_test \
  -e ENABLE_WORKFLOW_BURST=true \
  -e ENABLE_WEBHOOK_BURST=true \
  -e ENABLE_STATUS_POLLING=true \
  load/k6-workflows.js
```

Replay burst requires a role with dead-letter replay permission and an
environment that already has dead-lettered workflows to replay:

```bash
k6 run -e BASE_URL=https://staging-api.example.com \
  -e TENANT_ID=tenant_load_test \
  -e PRINCIPAL_ROLES=admin \
  -e ENABLE_REPLAY_BURST=true \
  -e ENABLE_STATUS_POLLING=true \
  load/k6-workflows.js
```

## Execution Notes

- The Python harness falls back to `docker exec` for direct PostgreSQL and Redis probes when the host cannot reach those services directly.
- k6 validates queue exit and completion with sampled polling to keep the submission profile realistic at high concurrency.
- Dead-letter replay intentionally degrades to a documented skip when the target environment has nothing to replay.
- Use a dedicated tenant for load tests so the generated metrics and dead-letter analysis stay isolated.