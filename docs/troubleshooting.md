# Troubleshooting

Decision trees for the most common failure modes seen by integrators and
operators. For day-to-day operational procedures (rotations, replays,
incident response) see [runbooks.md](runbooks.md). For full error
semantics see [api.md §3](api.md#3-error-envelope).

---

## 1. Error-code quick reference

| HTTP | `error.code` | Most likely cause | First action |
|------|--------------|-------------------|--------------|
| 401 / 403 | — | Returned by your API gateway, not this service. This service performs no authentication/authorization of its own; see [authentication.md](authentication.md). | Check gateway logs/config. |
| 404 | `workflow_not_found` | Workflow ID belongs to another tenant or never existed. | Verify the workflow was created under this tenant. |
| 404 | `job_not_found` | Same as above for jobs. | Confirm `job_id` from the original 202 response. |
| 409 | `idempotency_key_conflict` | Same `Idempotency-Key` reused with a different body. | Use a new key or replay the original body verbatim. |
| 409 | `idempotency_key_in_progress` | Original request still running. | Poll workflow status; do not resubmit. |
| 409 | `workflow_state_conflict` | Tool/approval callback hit a workflow that already left the waiting state. | Read current state; abort the callback. |
| 422 | `validation_error` | Payload size, depth, identifier shape, enum, or schema. | Inspect `error.details.field`. |
| 429 | `quota_exceeded` | Per-tenant token/RPM/cost quota hit or upstream provider throttled. | Back off using `Retry-After` header. |
| 503 | `service_unavailable` | A readiness component is degraded. | Check `/health/ready`; see §4 below. |

---

## 2. Workflow stuck in a state

Use `GET /v1/workflows/{workflow_id}` to see `state` and `pending_action`.

```
state = QUEUED for > 60 s
  └── Worker not consuming.
       ├── /health/ready shows workflow_worker = N/A → worker process down.
       ├── Worker logs show "no due workflow" → tenant exceeded
       │   max_inflight_per_tenant. Increase the limit or wait.
       └── Postgres lock contention on workflow_runs → check pg_stat_activity
           for long-running queries (see §5).

state = RUNNING for > handler_timeout_seconds
  └── Handler hung. Worker will release the lease when lease_expires_at passes.
       ├── Lease will be reclaimed automatically.
       └── If it cycles forever (RUNNING → FAILED → QUEUED → RUNNING),
           the workflow is a poison pill. See §6.

state = WAITING_TOOL
  └── Platform is waiting for your tool callback.
       └── POST /v1/workflows/{id}/tool-results with the result.

state = WAITING_APPROVAL
  └── Platform is waiting for an approver.
       └── POST /v1/workflows/{id}/approvals with approve/reject.

state = FAILED with retryable=true
  └── Will retry. attempt_count increments and next_attempt_at moves forward.

state = DEAD
  └── Max attempts exhausted. See [runbooks.md §3](runbooks.md).
```

---

## 3. `/health/ready` is `degraded`

The endpoint returns the failing component name(s). Map them:

| Component | Means | Fix |
|-----------|-------|-----|
| `postgresql` | Pool exhausted, network unreachable, or readonly. | Check pool metrics, network, replica promotion state. |
| `redis` | Network or auth failure. | Check `redis-cli ping`, ACL config. |
| `event_store` | Postgres reachable but event_store table missing or unreadable. | Verify migrations ran (`alembic current`). |
| `workflow_queue` | Redis reachable but the queue keys are missing or the producer never wrote. | Restart the API; check `AI_PLATFORM_WORKFLOW_QUEUE_NAME`. |
| `workflow_worker` | No worker heartbeat in the last `worker_heartbeat_ttl_seconds`. | Start a worker, or check worker logs. |
| `provider:<name>` | Adapter health probe failing. | Bad/expired API key, base URL blocked, circuit breaker open. |

---

## 4. Provider routing failures

Symptoms: 502/503 on capability endpoints, `provider_routing_failed` in logs,
or workflows oscillating to FAILED.

Walk the routing chain (see [provider-routing.md](provider-routing.md)):

1. **Capability mismatch.** If the chosen provider does not implement the
   capability (e.g. Anthropic + `embed`), the router skips it. Verify
   `required_capability` aligns with reality.
2. **Circuit breaker open.** Each provider has its own breaker. Logs
   include `circuit_breaker_state=OPEN`. Wait for `recovery_timeout` or
   trigger a manual close.
3. **Rate-limit / 429 from upstream.** Logged as
   `provider_rate_limited`. Router retries via the fallback chain; the
   `Retry-After` header from the upstream is honoured.
4. **Quota exhausted.** Per-tenant quota in
   `TenantRoutingPolicy.daily_token_budget` was reached. Increase the
   quota or wait until the budget resets.
5. **All providers exhausted.** `ProviderRoutingError` propagates with
   `candidates_tried` for triage. Confirm at least one provider is
   healthy on `/health/ready`.

---

## 5. Database problems

### Pool exhaustion

Symptom: API requests slow, logs show `QueuePool limit of size N overflow M reached`.

```
1. Inspect pool: workers/api both export pool_in_use, pool_overflow metrics.
2. Look for long-running queries:
   SELECT pid, age(clock_timestamp(), query_start) AS duration, query
   FROM pg_stat_activity
   WHERE state = 'active' AND query NOT LIKE '%pg_stat_activity%'
   ORDER BY duration DESC LIMIT 20;
3. Kill clearly stuck queries (last resort): SELECT pg_terminate_backend(<pid>);
4. If lease acquisition is the bottleneck, see §6.
```

### Slow `acquire_due`

The lease-acquisition query is the hottest write on the workflow_runs
table. At ≥ 500 in-flight workflows it should still complete in <50 ms.
If it doesn't:

- `EXPLAIN` the query and confirm `ix_workflow_runs_tenant_state_due` is
  used.
- Run `VACUUM ANALYZE workflow_runs` if statistics are stale.
- Check for hot partitions on `event_store` (HASH 16) — uneven workflow_id
  distribution can skew load.

### Migration deadlocks

If two replicas start with no schema, both attempt `alembic upgrade head`.
The advisory lock around migrations prevents duplicate application, but
under repeated container restarts you can see lock waits. Resolve by
running migrations once out-of-band before scaling out, then start
workers.

---

## 6. Poison-pill loops

A poison pill is a workflow that fails repeatedly because of a bug in
the request, not a transient issue. Symptoms:

- Same `workflow_id` appearing many times in retry logs.
- `attempt_count` climbing to `max_attempts` then transitioning to `DEAD`.
- Provider cost rising disproportionate to job volume.

Steps:

1. Inspect the workflow's events via `GET /v1/workflows/{id}` and the
   event store.
2. Decide: is the input malformed, or is the prompt/router wrong?
3. If input is malformed, mark the workflow DEAD by letting it exhaust;
   ask the producer to fix the payload schema.
4. If platform-side, fix the prompt/router, then replay using
   `workflows replay --tag <reason>` (see [runbooks.md §4](runbooks.md#4-bulk-replay-by-error-class)).

Prevention: enable per-handler timeout (`spec.timeout_seconds`); enforce
a per-workflow `max_attempts` so producers can choose less-aggressive
retry budgets for expensive workflows.

---

## 7. Idempotency edge cases

| Scenario | Behaviour | Recommendation |
|----------|-----------|----------------|
| Same key, same body, within TTL | Returns the cached response (HTTP 200, original `trace_id`). | Safe. |
| Same key, different body, within TTL | `idempotency_key_conflict` (409). | Generate a new key. |
| Same key, first request still running | `idempotency_key_in_progress` (409). | Poll workflow status; do not retry. |
| Same key after TTL | Treated as a new request. | Use longer-lived keys for long-running flows. |
| Same key across tenants | Today the cache scope includes tenant, path, and key before hashing for Redis. Cross-tenant collisions cannot replay another tenant's response. | — |

---

## 8. Webhook deliveries failing

(Webhook delivery is rolling out behind a feature flag; see
[webhooks.md](webhooks.md).)

| Symptom | Cause | Fix |
|---------|-------|-----|
| 401 from your endpoint | Receiver signature verification mismatch. | Verify `x-signature-*` headers with the documented payload format. |
| Duplicate deliveries | Built-in at-least-once. | Dedupe by `x-webhook-id` or `event_id`. |
| Delivery never arrives | Subscription disabled, or filtered out by `workflows`/`events`. | Inspect subscription state via admin tools. |
| Receiver returning 5xx → DLQ | Receiver outage. | Fix receiver; admin can re-enqueue from DLQ. |

---

## 9. Performance smoke

Quick sanity numbers for a healthy single-node dev environment with
Postgres + Redis on the same host:

| Operation | Expected p50 | Red flag at |
|-----------|--------------|-------------|
| `POST /v1/workflows/run` (queueing) | < 80 ms | > 250 ms |
| `acquire_due` lease query | < 20 ms | > 100 ms |
| Provider call (Gemini Flash, 200-token reply) | 700–1500 ms | > 5 s |
| Event append (single event) | < 25 ms | > 80 ms |

If queueing latency exceeds the red flag, profile the API DB pool,
`enforce_payload_limits`, and middleware order.

---

## 10. Escalation

If a problem persists after walking the relevant section above:

1. Capture `trace_id` and the failing `workflow_id`/`job_id`.
2. Pull the structured logs filtered by `trace_id` (every layer
   propagates it).
3. Attach `/health/ready` and the relevant Prometheus snapshot.
4. File against the platform team's on-call queue.
