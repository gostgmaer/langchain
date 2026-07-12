# Event Model

Every meaningful transition in the platform is an immutable event. Workflow
state, audit trails, metrics, and (future) webhooks all derive from the
event log.

## 1. Event envelope

All events share this envelope shape:

```json
{
  "event_id": "01HX2N5G6E0X4Z7V8YQK0V8RPT",
  "event_name": "PROVIDER_SELECTED",
  "tenant_id": "tenant_acme",
  "workflow_id": "d65cb4dc...",
  "trace_id": "01HX2...",
  "job_id": "a9f3c1...",
  "correlation_id": "order_8821",
  "causation_id": "01HX2N5G6E0X4Z7V8YQK0V8RPS",
  "idempotency_key": "sha256:...",
  "occurred_at": "2026-05-18T12:00:01.234Z",
  "producer": "ai-worker-generation",
  "schema_version": 1,
  "payload": { "...": "..." }
}
```

| Field | Meaning |
|-------|---------|
| `event_id` | Globally unique, time-ordered (ULID-like). |
| `event_name` | One of the enum below. |
| `tenant_id` | Mandatory; events are never tenant-unscoped. |
| `workflow_id` | The workflow instance. |
| `trace_id` | End-to-end correlation id. |
| `job_id` | The specific attempt; absent before a worker leases. |
| `correlation_id` | Business id you supplied (e.g. order id). |
| `causation_id` | `event_id` that caused this event (chain). |
| `idempotency_key` | Deduplication for upstream sources (webhooks, tools). |
| `occurred_at` | RFC 3339 UTC. |
| `producer` | Service that wrote the event. |
| `schema_version` | Version for `payload`. Additive changes only. |
| `payload` | Event-specific JSON. |

## 2. Event names

| Event | Payload highlights |
|-------|---------------------|
| `REQUEST_RECEIVED` | http_method, http_path, content_length |
| `REQUEST_VALIDATED` | workflow, task, capability |
| `CONTEXT_RESOLVED` | context_ids, versions, version_hash |
| `JOB_QUEUED` | queue_name, priority, deadline_at |
| `WORKFLOW_CREATED` | workflow, task, max_attempts, timeout_at |
| `WORKER_STARTED` | worker_id, attempt |
| `PROVIDER_SELECTED` | provider, model, routing_hint, reason |
| `TOOL_REQUESTED` | tool_name, tool_payload |
| `WAITING_APPROVAL` | approval_type, approval_payload |
| `WORKFLOW_RESUMED` | source (`tool` \| `approval`), reference id |
| `COMPLETED` | result_keys, tokens, provider, model, latency_ms |
| `FAILED` | error_class, error_code, message, retriable |
| `RETRY_SCHEDULED` | attempt, not_before |
| `WORKFLOW_TIMEOUT` | deadline_at, elapsed_ms |
| `WORKFLOW_CANCELLED` | cancelled_by, reason |
| `DEAD_LETTER` | error_class, attempts_used |
| `DEAD_LETTER_REPLAYED` | replayed_by, reason, reset_attempts, next_attempt_at |

## 3. Ordering & consistency

* Events are appended to the workflow’s stream with optimistic concurrency:
  the writer supplies `expected_version`; the engine retries on conflict.
* Events are written to PostgreSQL **in the same transaction** as the
  projection update (transactional outbox), guaranteeing no phantom or lost
  events.
* Within a workflow, events are strictly ordered by `occurred_at` and a
  monotonically increasing stream version. Across workflows there is no
  ordering guarantee.

## 4. Reading events

Today, the public surface for events is the workflow status endpoint
(`GET /v1/workflows/{workflow_id}`), which projects events into a snapshot.
Long workflow streams are periodically checkpointed in `event_snapshots` so
rehydration reads the latest snapshot plus the event tail instead of replaying
the entire stream every time.

Direct event tailing is **not part of the public contract**. A future
webhook channel will fan out specific events to integrators (see
[webhooks.md](webhooks.md)).

## 5. Event-driven integration patterns

Even without webhooks today, you can build event-driven integrations using
the same conceptual model:

1. Submit a workflow → receive `workflow_id`.
2. Poll status until terminal.
3. On `WAITING_TOOL` / `WAITING_APPROVAL`, fulfil the request via the
   appropriate callback endpoint (see [tool-calls.md](tool-calls.md)).
4. On `SUCCESS` / `DEAD`, take action; persist `trace_id` for audit.

When webhooks are enabled, you will receive a signed POST with the same
envelope for the events your subscription elects. The polling fallback
should always remain implemented so that webhook outages do not stall your
pipeline.

## 6. Event replay

* The engine can rebuild any workflow snapshot from its events at any time.
* Operators can replay `DEAD` workflows after fixing the root cause.
* Event payloads are versioned; downstream consumers should ignore unknown
  fields.

## 7. Retention

* `event_store` is hash-partitioned by stream for write throughput; old
  partitions are archived (not purged) according to the deployment’s
  retention policy (typically 365 days online, 7 years cold).
* `audit_logs` and `usage_metrics` are range-partitioned by time and can
  be detached for cold storage.

## 8. Schema evolution rules

* Add fields. Never remove or rename within a `schema_version`.
* Bump `schema_version` when a removal or semantic change is unavoidable.
* Consumers MUST ignore unknown fields.
