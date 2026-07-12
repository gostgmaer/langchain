# Observability — Metrics, Traces, Logs

This document is the authoritative reference for everything the platform
exports to an operator: Prometheus metric names and labels, OpenTelemetry
span surface, and structured-log fields. It is generated to match the
implementation in [`app/observability/`](../app/observability) and the
metrics middleware wired in [`app/main.py`](../app/main.py).

## 1. Metrics endpoint

| Method | Path | Notes |
|--------|------|-------|
| `GET`  | `/metrics`     | Prometheus text exposition. |
| `GET`  | `/v1/metrics`  | Versioned alias of `/metrics`. |

Both endpoints require the platform-scoped `metrics:read` permission when
RBAC is enforced. They are excluded from the OpenAPI schema.

Wire the scrape target with a label that carries `tenant_id`, `provider`,
`model`, `workflow`, `state`, and `queue_name` to enable per-dimension
slicing. Bound cardinality with relabel rules if a tenant pool grows
unbounded.

### 1.1 Shipped monitoring assets

The repository now ships a ready-to-run local monitoring bundle:

* `docker-compose.observability.yml` — Grafana + Prometheus overlay.
* `monitoring/prometheus/prometheus.yml` — scrape config for `api:8000` and
  `worker:9100`.
* `monitoring/prometheus/alerts/ai-platform-alerts.yml` — starter alert rules
  for latency, backlog, starvation, DLQ growth, and provider failures.
* `monitoring/grafana/dashboards/platform-overview.json` — workflow, queue,
  latency, retry, and DLQ dashboard.
* `monitoring/grafana/dashboards/provider-efficiency.json` — provider error,
  latency, token, cost, and cache-efficiency dashboard.

Start the bundle with:

```bash
docker compose -f docker-compose.yml -f docker-compose.observability.yml up -d
```

## 2. Metric catalog

All metrics are emitted with the prefix `ai_platform_`. Implementation:
[`app/observability/metrics.py`](../app/observability/metrics.py).

### 2.1 Request layer

| Metric | Type | Labels | Unit | Description |
|--------|------|--------|------|-------------|
| `ai_platform_request_latency_seconds` | Histogram | `method`, `path`, `status_code`, `tenant_id` | seconds | HTTP request latency. Path is the route template, not the raw path. |

### 2.2 Queues

| Metric | Type | Labels | Unit | Description |
|--------|------|--------|------|-------------|
| `ai_platform_queue_depth` | Gauge | `tenant_id`, `queue_name` | jobs | Pending jobs per queue. Sampled by the worker heartbeat loop. |
| `ai_platform_queue_lag_seconds` | Gauge | `tenant_id`, `queue_name` | seconds | Age of the oldest ready job, measured at sample time. |
| `ai_platform_active_workers` | Gauge | `tenant_id`, `queue_name` | workers | Active worker leases per queue at sample time. |

Queue names emitted: `workflow_queue`, `workflow_queue:retry`,
`workflow_queue:dead_letter` (the platform default). See
[`architecture.md` §5](architecture.md#5-queue-and-leases).

### 2.3 Provider calls

| Metric | Type | Labels | Unit | Description |
|--------|------|--------|------|-------------|
| `ai_platform_provider_calls_total` | Counter | `tenant_id`, `provider`, `model`, `capability`, `status` | calls | Outbound provider attempts. `status` ∈ `success`, `failure`. |
| `ai_platform_provider_latency_seconds` | Histogram | `tenant_id`, `provider`, `model`, `capability` | seconds | Per-call provider latency. |
| `ai_platform_provider_cost_usd_total` | Counter | `tenant_id`, `provider`, `model`, `capability` | USD | Cumulative provider spend; clamped at 0 when upstream reports no cost. |
| `ai_platform_token_usage_total` | Counter | `tenant_id`, `provider`, `model`, `capability`, `direction` | tokens | `direction` ∈ `input`, `output`. |

`capability` is one of `generate`, `embed`, `classify`, `summarize`,
`rerank`, `extract`, `ocr`, matching the platform capability matrix in
[`provider-routing.md`](provider-routing.md).

### 2.4 Workflow engine

| Metric | Type | Labels | Unit | Description |
|--------|------|--------|------|-------------|
| `ai_platform_workflow_retries_total` | Counter | `tenant_id`, `workflow` | retries | Retry attempts scheduled by the engine. Incremented at retry-scheduling time, not on retry success. |
| `ai_platform_dead_letter_jobs_total` | Counter | `tenant_id`, `queue_name`, `reason` | jobs | Jobs moved to the dead-letter queue. `reason` is the engine's failure category (`workflow_timeout`, `retries_exhausted`, `non_retryable`, …). |
| `ai_platform_workflow_transitions_total` | Counter | `tenant_id`, `workflow`, `state` | transitions | Every state entered by a workflow, including resumes. Sum over `state` is **not** the submission count; use `workflow_transitions_total{state="QUEUED"}` minus resume contributions for that. |

### 2.5 Semantic cache

| Metric | Type | Labels | Unit | Description |
|--------|------|--------|------|-------------|
| `ai_platform_semantic_cache_total` | Counter | `tenant_id`, `workflow`, `result` | lookups | Cache lookup outcomes. `result` ∈ `hit`, `miss`. |

### 2.6 Embeddings

| Metric | Type | Labels | Unit | Description |
|--------|------|--------|------|-------------|
| `ai_platform_embedding_operations_total` | Counter | `tenant_id` | operations | Total embedding operations (batches). |
| `ai_platform_embedding_cache_hits_total` | Counter | `tenant_id` | operations | Embedding operations fully served from Redis cache. |

### 2.7 Memory service

| Metric | Type | Labels | Unit | Description |
|--------|------|--------|------|-------------|
| `ai_platform_memory_operations_total` | Counter | `tenant_id`, `operation`, `memory_type` | operations | Memory store/recall operations. `operation` ∈ `store`, `recall`. `memory_type` ∈ `conversation`, `episodic`, `semantic`. |

### 2.8 Context compression

| Metric | Type | Labels | Unit | Description |
|--------|------|--------|------|-------------|
| `ai_platform_context_compression_total` | Counter | `tenant_id` | operations | Context assembly operations where budget was under-utilised (compression active). |
| `ai_platform_context_compression_tokens_saved_total` | Counter | `tenant_id` | tokens | Cumulative tokens saved by context compression. |

### 2.9 Reranking

| Metric | Type | Labels | Unit | Description |
|--------|------|--------|------|-------------|
| `ai_platform_reranking_operations_total` | Counter | `tenant_id` | operations | Reranking passes executed. |

### 2.10 Multi-agent orchestration

| Metric | Type | Labels | Unit | Description |
|--------|------|--------|------|-------------|
| `ai_platform_orchestration_total` | Counter | `tenant_id`, `strategy` | orchestrations | Agent orchestration runs dispatched. |

## 3. Recommended alerts and SLOs

Treat the numbers below as starting points; tune per tenant.

The default Prometheus rules in
`monitoring/prometheus/alerts/ai-platform-alerts.yml` codify the first five
signals below.

| Symptom | Expression | Threshold |
|---------|------------|-----------|
| API tail latency regression | `histogram_quantile(0.95, sum(rate(ai_platform_request_latency_seconds_bucket[5m])) by (le, path))` | > 1.5 s for 10 m on hot paths. |
| Queue starvation | `min_over_time(ai_platform_active_workers[5m]) == 0` while `ai_platform_queue_depth > 0` | any tenant for 2 m. |
| Queue backlog | `ai_platform_queue_depth` | > 1000 sustained 10 m. |
| Queue staleness | `ai_platform_queue_lag_seconds` | > workflow timeout p50. |
| Provider error rate | `sum(rate(ai_platform_provider_calls_total{status="failure"}[5m])) by (provider) / sum(rate(ai_platform_provider_calls_total[5m])) by (provider)` | > 0.05 for 10 m. |
| Dead-letter growth | `increase(ai_platform_dead_letter_jobs_total[15m])` | any non-zero increase is page-worthy unless replay is in flight. |
| Tenant cost burn | `increase(ai_platform_provider_cost_usd_total[1d])` | > daily ceiling. |

SLO suggestions for a typical 500–1000 concurrent-workflow deployment:

* API availability: 99.9 % (5xx-only) on `/v1/*` excluding `/metrics`.
* Workflow success rate (excluding tenant-input failures): 99 % over 30 d.
* `WAITING_TOOL` dwell time p95: < tenant's tool SLA + 5 s.

## 4. OpenTelemetry

Tracing is enabled when `AI_PLATFORM_OTEL_ENABLED=true`. The collector
endpoint comes from `AI_PLATFORM_OTEL_EXPORTER_OTLP_ENDPOINT` (required in
production). Service identity comes from `AI_PLATFORM_OTEL_SERVICE_NAME`,
`_NAMESPACE`, and `_INSTANCE_ID`.

### 4.1 Instrumented components

* FastAPI (via OpenTelemetry's ASGI middleware) — every HTTP request.
* SQLAlchemy — every database statement.
* `redis.asyncio` — every Redis command.
* `structlog` — log records carry the current trace/span ids.
* Worker loop and workflow engine — manual spans wrap workflow execution,
  provider calls, and queue operations.

### 4.2 Standard span attributes

All platform spans carry:

| Attribute | Source | Notes |
|-----------|--------|-------|
| `tenant_id` | `x-tenant-id` header / workflow row | always set on tenant-scoped spans. |
| `trace_id`  | request middleware | same value surfaced in responses. |
| `workflow`  | workflow plugin name | absent on non-workflow spans. |
| `workflow_id` | engine | set once a workflow row exists. |
| `job_id` | engine | set once a queue job exists. |
| `capability` | provider router | `generate`, `embed`, … |
| `provider` | provider adapter | resolved provider id. |
| `model` | provider adapter | resolved model id. |
| `state` | engine | terminal state on transition spans. |
| `attempt_count` | engine | retry attempt index. |

`trace_id` is globally unique; cross-region log correlation should pivot on
it.

### 4.3 Sampling

`AI_PLATFORM_OTEL_TRACE_SAMPLE_RATIO` controls head sampling (1.0 = trace
every request). For high-volume production, sample at 0.1–0.2 and force-
sample on errors via OTEL's parent-based ratio sampler (configured at the
collector).

## 5. Structured logs

All logs come from `structlog`. Format defaults to JSON. Every record
carries:

| Field | Type | Notes |
|-------|------|-------|
| `event` | string | Log message / event id (e.g. `workflow.transition`). |
| `level` | string | `INFO`, `WARNING`, `ERROR`, etc. |
| `timestamp` | RFC3339 string | UTC. |
| `service` | string | `AI_PLATFORM_OTEL_SERVICE_NAME`. |
| `environment` | string | `local` / `staging` / `production`. |
| `trace_id` | string | when available. |
| `span_id` | string | when available. |
| `tenant_id` | string | when available. |
| `workflow` | string | workflow name when applicable. |
| `workflow_id` | string | when applicable. |
| `job_id` | string | when applicable. |
| `attempt_count` | int | retry-loop logs. |
| `provider` / `model` / `capability` | string | provider router logs. |
| `duration_ms` | float | latency-bearing logs. |
| `error.type` / `error.message` / `error.stack` | string | on failures. |

Sensitive fields are redacted:

* Anything declared as `SecretStr` in `Settings` → `***`.
* Request bodies of `POST /v1/*` capability endpoints are NOT logged.
* Provider keys never appear in logs.

## 6. Health components and degraded triggers

`/health/ready` reports each component independently. The aggregate
returns 503 if any required component is `degraded`.

| Component | Required | Trigger for `degraded` |
|-----------|:--------:|------------------------|
| `postgresql` | ✓ | DB roundtrip fails within `AI_PLATFORM_HEALTH_CHECK_TIMEOUT_SECONDS`. |
| `redis` | ✓ | Redis `PING` fails or times out. |
| `event_store` | ✓ | `event_store`, `event_snapshots`, or `workflow_runs` table missing. |
| `workflow_queue` | ✓ | Cannot read queue metrics from Redis. |
| `workflow_worker` | ✓ | No fresh `worker_metrics:workflow-worker-*` heartbeat within `max(30, AI_PLATFORM_WORKFLOW_WORKER_POLL_INTERVAL_SECONDS * 10)` seconds. |
| `provider:<name>` | ✓ | Adapter health check fails. One component per configured provider key. |

`/health/live` only verifies the API process can answer; it does not check
dependencies.
