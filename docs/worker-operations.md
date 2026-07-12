# Worker Operations

The API process only validates requests, persists workflow state, and returns
`QUEUED`. A separate worker process must run for workflows to leave the queue.

## Start a Worker

Local development:

```bash
python -m app.workers.main
```

Docker Compose:

```bash
docker compose up api worker postgres redis
```

The worker uses the same `AI_PLATFORM_*` configuration as the API. It creates
its own database and Redis clients, builds the provider router from configured
provider keys, loads the prompt registry, and registers all supported workflow
handlers.

## What the Worker Does

1. Acquires one due `QUEUED` workflow using a database lease.
2. Resolves the handler for the workflow name.
3. Records `WORKER_STARTED` and executes exactly one workflow step.
4. Transitions to `SUCCESS`, `WAITING_TOOL`, `WAITING_APPROVAL`, `FAILED`, or
   `DEAD` through the workflow engine.
5. Releases the lease in all outcomes.
6. Runs a periodic timeout scanner via `WorkflowEngine.handle_timeouts()`.

## Worker Heartbeat and Health

Each worker started through `python -m app.workers.main` publishes a Redis
heartbeat under `worker_metrics:workflow-worker-<uuid>`. The heartbeat stores
`last_seen_at`, the current or last job id, counters for claimed/completed/
failed/retried/dead-lettered jobs, and expires automatically when the worker is
gone.

`GET /health/ready` and `GET /health` expose this as the `workflow_worker`
component. The component is `ok` when at least one heartbeat is fresher than the
stale threshold and `degraded` with `no active workflow worker heartbeat` when
no worker has reported recently. The stale threshold is derived from the worker
poll interval and never drops below 30 seconds.

Docker and Kubernetes workers do not need an HTTP health endpoint. Use the API
readiness result, queue depth, and worker metrics instead of probing the worker
container directly.

## Required Configuration

| Variable | Purpose |
|----------|---------|
| `AI_PLATFORM_WORKFLOW_WORKER_LEASE_SECONDS` | Lease duration for one claimed workflow. |
| `AI_PLATFORM_WORKFLOW_WORKER_POLL_INTERVAL_SECONDS` | Idle wait between lease attempts. |
| `AI_PLATFORM_WORKFLOW_WORKER_TIMEOUT_SCAN_INTERVAL_SECONDS` | Interval for timeout scans. |
| `AI_PLATFORM_WORKFLOW_WORKER_TIMEOUT_BATCH_SIZE` | Maximum timed-out workflows handled per scan. |
| `AI_PLATFORM_WORKFLOW_WORKER_MAX_INFLIGHT_PER_TENANT` | Per-tenant active lease cap to prevent one tenant occupying all workers. |
| `AI_PLATFORM_WORKFLOW_SNAPSHOT_INTERVAL` | Event snapshot cadence for long workflow streams. |
| `AI_PLATFORM_PROVIDER_API_KEYS__<provider>` | Provider credentials used by handlers. |
| `AI_PLATFORM_PROVIDER_CIRCUIT_BREAKER_BACKEND` | Use `redis` in production so provider failures are shared across replicas. |
| `AI_PLATFORM_PROVIDER_QUOTA_BACKEND` | Use `redis` outside local/test so token quota reservations are shared across replicas. |
| `AI_PLATFORM_PROVIDER_DAILY_TOKEN_QUOTAS__<provider>` | Default per-tenant daily token cap for each configured provider. |

Production workers should run as independently scalable replicas. Scale them on
queue depth, `workflow_runs` pending count, provider latency, and DLQ growth.

## Shutdown

The worker handles `SIGINT` and `SIGTERM` by stopping new lease acquisition,
finishing the active step, cancelling the timeout scanner, and closing clients.
Use a termination grace period longer than `WORKFLOW_WORKER_LEASE_SECONDS`.

## Dead-Letter Operations

Dead-lettered workflows remain in `workflow_runs` with state `DEAD` and are
also pushed to the Redis dead-letter queue for operations visibility.

List unresolved dead letters:

```bash
curl -H "x-tenant-id: tenant_123" \
   "https://api.example.com/v1/workflows/dead-letter?tenant_id=tenant_123"
```

Replay after the incident is fixed:

```bash
curl -X POST \
   -H "content-type: application/json" \
   -H "x-tenant-id: tenant_123" \
   -H "x-principal-id: ops-1" \
   -d '{"tenant_id":"tenant_123","reason":"provider recovered","reset_attempts":true}' \
   "https://api.example.com/v1/workflows/<workflow_id>/dead-letter/replay"
```

Alert when `workflow_dead_letter_total` increases for the same tenant/workflow
for more than one evaluation window, or when the Redis dead-letter queue depth
is non-zero for longer than the workflow SLO.