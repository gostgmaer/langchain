# Scaling

The platform is designed to run **millions of workflows per day** across
many tenants. This document is the integration-facing scaling reference:
what the platform handles for you, what you must plan for, and what the
operating envelope looks like.

## 1. What the platform handles

* Async-by-default API. Heavy work never blocks a connection.
* Multi-tenant fair-share queueing with per-tenant in-flight caps.
* Priority lanes per queue (`p0` interactive, `p5` bulk).
* Provider-aware routing with circuit breakers and EWMA-weighted failover.
* Adaptive routing that can prefer lower-latency/lower-cost healthy providers
  when no workflow policy pins a provider.
* Worker autoscaling on queue depth, latency, and provider 429 rate.
* Per-process worker concurrency via `AI_PLATFORM_WORKFLOW_WORKER_CONCURRENCY`.
* Per-tenant quotas and cost ceilings.
* Semantic response caching, embedding caching, RAG reranking, and context
  compression to reduce tokens and provider pressure.
* Partitioned data tables for write throughput and retention.

## 2. What you must plan for

* **Backpressure on your side.** When a tenant is throttled (HTTP 429),
  pause your producers; do not loop submit.
* **Status updates.** Prefer SSE or WebSocket status streams for active user
  views. If polling, use exponential backoff. A constant 100 ms poll for 1M
  workflows is your own self-DoS.
* **Idempotency keys.** Required for any submission path with retries on
  your side (e.g. email automation re-deliveries).
* **Context cache hits.** Frequent contexts should be small (≤ 64 KiB)
  and stable. Cache-miss-heavy traffic increases tail latency.
* **Tool callbacks.** Your tool service must scale alongside platform
  throughput; otherwise workflows pile up in `WAITING_TOOL`.

## 3. Throughput envelope

The exact numbers depend on the deployment. Default sizing targets:

| Dimension | Target |
|-----------|--------|
| Sustained command RPS per tenant | configurable (5k+ realistic) |
| Burst command RPS per tenant | 2× sustained for 60 s |
| Concurrent workflows per tenant | configurable (10k+ realistic) |
| Concurrent active jobs per standard deployment | 500-1000 with API/worker HPA and Redis-backed coordination |
| Provider concurrency | governed by tenant quotas + provider limits |
| Workflow timeout | up to 7 days |
| Tool callback timeout | per-tool, ≤ workflow `timeout_seconds` |

## 4. Cost scaling

* Every attempt records tokens and provider cost in `ai_generations`.
* Rolled up per (tenant, day, provider, model) in `usage_metrics`.
* The router can be configured to **fail over to cheaper providers** when
  per-tenant daily ceilings approach.
* Use `BULK_PROCESSING` workflows for non-interactive volume to keep cost
  near DeepSeek pricing. See [provider-routing.md](provider-routing.md).

## 5. Hot paths and limits

| Path | Hot? | Notes |
|------|:----:|-------|
| `POST /v1/generate` (and siblings) | ✓ | Stateless; horizontally scaled. |
| `GET /v1/jobs/{id}` | ✓ | Read from projection; backed by index. |
| `GET /v1/workflows/{id}` | ✓ | Same. |
| `GET /v1/realtime/workflows/{id}/events` | ✓ | SSE status stream, bounded by max stream seconds. |
| `WS /v1/realtime/workflows/{id}/ws` | ✓ | WebSocket status snapshots for active clients. |
| `POST /v1/agents/orchestrations` | ✓ | Queues child workflows and returns immediately. |
| `GET /metrics` | — | Use Prometheus scrape, not application traffic. |
| Tool callback POSTs | ✓ | Correlated by `workflow_id` + `pending_action.tool_name`. |
| Approval callbacks | – | Low volume, role-gated. |

## 6. Worker autoscaling signals

Workers scale on the following signals:

* Queue pending count per stream (per priority).
* Average worker latency (EWMA).
* Provider 429 rate (negative signal — do not scale up).
* CPU + memory (last-resort signal for embedding/OCR workers).

The worker lease query enforces `AI_PLATFORM_WORKFLOW_WORKER_MAX_INFLIGHT_PER_TENANT`
so one tenant cannot consume every active lease while other tenants have due
work queued.

Inside each worker pod, `AI_PLATFORM_WORKFLOW_WORKER_CONCURRENCY` controls how
many independent worker loops claim leases concurrently. Increase it only when
provider quotas, database pool size, and Redis capacity are sized accordingly.
For burst traffic, scale replicas first and then raise per-pod concurrency.

Scale-down respects in-flight leases: workers stop claiming on SIGTERM,
finish work, then exit. This is invisible to integrators.

## 7. Database scaling

* `event_store` is hash-partitioned by stream for write throughput.
* `ai_generations`, `usage_metrics`, `audit_logs` are range-partitioned by
  time; old partitions are archived.
* Reads from operational tables use covering indexes per common access
  path (by `tenant_id + state + created_at`, by `trace_id`, …).

## 8. Redis scaling

* Production should use separate Redis instances: cache/rate/idempotency
  (LRU) and queue (no-eviction, AOF). Local compose may run a single Redis.
* `AI_PLATFORM_RATE_LIMIT_BACKEND=redis` and
  `AI_PLATFORM_IDEMPOTENCY_BACKEND=redis` are required in production so API
  replicas share quota and replay state.
* `AI_PLATFORM_PROVIDER_CIRCUIT_BREAKER_BACKEND=redis` is required in
  production so provider outages trip globally instead of per process.
* `AI_PLATFORM_PROVIDER_QUOTA_BACKEND=redis` and
  `AI_PLATFORM_PROVIDER_DAILY_TOKEN_QUOTAS__<provider>` are required outside
  local/test so token-budget reservations are shared across replicas and one
  tenant cannot consume the platform-wide provider budget.
* Queue keys use Redis hashes and sorted sets for job payloads, schedules,
  and leases. Shard by queue name when a single queue key becomes hot.
* The queue Redis must not share memory pressure with the cache; mixing
  them risks silent message loss.

## 9. Kubernetes baseline

Reference manifests live in [`k8s/`](../k8s). They deploy separate API and
worker Deployments, HPA policies, a ClusterIP Service, and default-deny
NetworkPolicy scaffolding. Replace `secret.example.yaml` with your secret
manager or ExternalSecret integration before applying in production.

Baseline for the 100-500 user / 30k monthly workflow target:

* API: 2 replicas, HPA to 6.
* Worker: 2 replicas, HPA to 10.
* Redis/Postgres: managed services with backups and metrics, not in-cluster
  single pods.
* Termination grace: longer than the workflow lease duration.

## 10. Multi-region considerations

* Workflows are tenant-pinned to a region by policy and by data residency.
* Cross-region context replication is your responsibility (publish the
  same `context_id` to each region’s context store before activating
  workflows there).
* Trace ids are globally unique. Logs and metrics from all regions can be
  correlated by `trace_id`.

## 11. Patterns at scale

| Pattern | When |
|---------|------|
| Fan-in batching | Many small classifications → one platform call per batch where possible. |
| Pre-warming contexts | Frequently used contexts pushed into cache during off-peak. |
| Pre-computing embeddings | Use `embed` workflows nightly; cache vectors in your store. |
| Splitting heavy contexts | Resume → `:summary` + `:full`; prompts pick the right one. |
| Sequencing approvals | Batch low-risk approvals; auto-approve under a configured policy. |

## 12. Anti-patterns at scale

* Constant fast polling of `GET /v1/jobs/{id}` (use exponential backoff).
* Submitting the same workflow many times without `Idempotency-Key`.
* Inlining large documents in `payload` instead of using contexts.
* Re-submitting on `FAILED` (the engine retries automatically).
* Holding a request open with `?wait=true` for long workflows.

## 13. Capacity planning checklist

* [ ] Tenant quotas approved (RPS, daily token budget, daily cost ceiling).
* [ ] Workflows benchmarked end-to-end at expected RPS.
* [ ] Tool services load-tested at 2× expected throughput.
* [ ] Polling clients verified with exponential backoff.
* [ ] Backpressure plan documented for HTTP 429 / 503.
* [ ] Observability dashboards include `tenant_id` and `workflow`.
