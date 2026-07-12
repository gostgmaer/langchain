# Architecture

This document describes the architecture implemented in this repository. It is
the high-level map for maintainers; external integrators should start with
[getting-started.md](getting-started.md), [api.md](api.md), and
[integration-guide.md](integration-guide.md).

## 1. System Shape

```text
Client
  |
  v
FastAPI API Gateway
  - request context and trace id
  - tenant header binding
  - request signing
  - rate limiting
  - idempotency
  - Pydantic validation
  |
  v
Workflow Engine
  - append immutable event
  - rebuild/project workflow snapshot
  - persist workflow projection
  - enqueue due work
  |
  v
Worker Process
  - acquire database lease
  - execute registered workflow handler
  - call provider router
  - pause for tools/approvals or complete
  |
  v
Provider Router
  - route by capability and routing hint
  - enforce tenant policy/quota store
  - retry/fail over with circuit breakers
  |
  v
Provider Adapters
  OpenAI | Anthropic | Gemini | DeepSeek | OpenRouter | xAI
```

The API process does not perform heavy provider work. It validates, resolves
context metadata, creates a durable workflow, enqueues it, and returns HTTP
202. Workers are separate processes and can scale independently.

## 2. Modules

| Module | Responsibility |
|--------|----------------|
| [app/api](../app/api) | FastAPI routes, request/response schemas, API errors. |
| [app/middleware](../app/middleware) | body limit, rate limit, trace context, tenant isolation, idempotency, signing. |
| [app/core](../app/core) | settings, logging, tracing, container wiring, health checks. |
| [app/context](../app/context) and [app/services/context_service.py](../app/services/context_service.py) | tenant-scoped context resolution from Redis/Postgres. |
| [app/prompts](../app/prompts) and [app/services/prompt_registry.py](../app/services/prompt_registry.py) | versioned prompt files and hot reload/cache support. |
| [app/events](../app/events) | event envelope, append-only event store, event snapshots. |
| [app/workflows](../app/workflows) | workflow engine, state machine, projection repository, dispatcher, worker coordinator, **plugin registry**. |
| [app/workflows/plugins](../app/workflows/plugins) | category-scoped plugin modules that register `WorkflowPluginSpec` records at startup. |
| [app/queues](../app/queues) | Redis-backed queue primitives using hashes and sorted sets. |
| [app/providers](../app/providers) | provider adapters, router, parsing, resilience, circuit breakers. |
| [app/security](../app/security) | RBAC, tenant checks, signing, encryption, payload codec. |
| [app/observability](../app/observability) | OpenTelemetry and Prometheus metric recording. |
| [migrations](../migrations) | Alembic schema migrations and seed data. |

## 3. Request Lifecycle

1. Middleware enforces request size, rate limits, trace context, tenant
   identity, idempotency, and signing in that order.
2. The route validates the command schema and checks RBAC.
3. The context resolver resolves `context_ids` and records the versioned
   context metadata in the workflow payload.
4. The workflow engine appends `WORKFLOW_CREATED` to `event_store`, projects a
   `workflow_runs` row, saves a snapshot when due, and enqueues the projection.
5. The route returns `QueuedWorkflowResponse` with `job_id`, `workflow_id`,
   `trace_id`, and `status: QUEUED`.
6. A worker leases the due workflow from `workflow_runs`, emits
   `WORKER_STARTED`, and dispatches to the registered handler.
7. The handler either returns a JSON result, a `ToolRequest`, an
   `ApprovalRequest`, or raises a retryable/non-retryable error.
8. The engine records the next event and projection state:
   `SUCCESS`, `WAITING_TOOL`, `WAITING_APPROVAL`, `FAILED`, `QUEUED`, `DEAD`,
   or `CANCELLED`.

## 4. Event Sourcing

Workflow state is derived from immutable events. `workflow_runs` is the
operational projection used for status reads, leasing, and indexes; it is not
the source of truth. The event store supports optimistic concurrency via
`expected_version`.

Long streams are checkpointed in `event_snapshots` according to
`AI_PLATFORM_WORKFLOW_SNAPSHOT_INTERVAL`. Loading a workflow reads the latest
snapshot plus the event tail, then applies the state machine.

Key events are documented in [event-model.md](event-model.md).

## 5. Queue and Leases

The implemented queue backend stores job payloads in Redis hashes and schedules
ready/delayed work in Redis sorted sets. The durable source remains Postgres:
workers claim due `workflow_runs` rows with database leases before executing a
workflow step.

### 5.1 Queue naming

Queue names are derived from a base stream name (configured via
`AI_PLATFORM_WORKFLOW_QUEUE_NAME`, default `workflow_queue`):

| Logical queue | Redis key suffix | Default name |
|---------------|------------------|--------------|
| Ready jobs | *(none)* | `workflow_queue` |
| Delayed retries | `:retry` | `workflow_queue:retry` |
| Dead letters | `:dead_letter` | `workflow_queue:dead_letter` |

The metrics exporter labels each queue with these exact names
(see [`observability-metrics.md` §2.2](observability-metrics.md#22-queues)).
The dead-letter queue is consumed only by operators via
`GET /v1/workflows/dead-letter` and
`POST /v1/workflows/{workflow_id}/dead-letter/replay`.

This split gives operators two views:

* Postgres projection: authoritative workflow state, leases, deadlines, dead
  letters.
* Redis queue keys: operational visibility into queued, retry, and dead-letter
  jobs.

Workers enforce `AI_PLATFORM_WORKFLOW_WORKER_MAX_INFLIGHT_PER_TENANT` at lease
time so one tenant cannot occupy every active worker lease.

Workers also publish Redis heartbeats under `worker_metrics:workflow-worker-*`.
The API health service uses those heartbeats for the `workflow_worker`
readiness component, so readiness proves that API and worker processes share
the same Redis backend.

## 6. Tool and Approval Resumes

When a workflow enters `WAITING_TOOL` or `WAITING_APPROVAL`, the status
endpoint exposes `pending_action`. The callback endpoints append
`WORKFLOW_RESUMED` and move the workflow back to `QUEUED`. The next worker
lease preserves the callback payload in `resume_payload`, allowing the handler
to continue with the tool result or approval decision.

Rejected approvals append a non-retryable `FAILED` event. Cancelled workflows
append `WORKFLOW_CANCELLED` and move to `CANCELLED`.

## 6a. Workflow Plugin Registry

Workflow definitions live in a plugin registry, not in API code. At startup
[app/core/container.py](../app/core/container.py) calls
`build_workflow_plugin_registry()` from
[app/workflows/plugin_registry.py](../app/workflows/plugin_registry.py), which
loads every module under [app/workflows/plugins/](../app/workflows/plugins)
and invokes its `register_plugins(registry)` hook.

```text
container.startup
  -> build_workflow_plugin_registry()
       -> load_all_plugins(registry)
            -> legacy.register_plugins        (8 workflows)
            -> core_ai.register_plugins       (7)
            -> tooling.register_plugins       (4)
            -> documents.register_plugins     (5)
            -> communication.register_plugins (8)
            -> calendar.register_plugins      (3)
            -> recruitment.register_plugins   (4)
            -> crm.register_plugins           (4)
            -> commerce.register_plugins      (3)
            -> analytics.register_plugins     (3)
            -> future.register_plugins        (3)
  -> build_workflow_handler_registry(plugin_registry=...)
       -> for each enabled plugin spec:
            resolve model:    request > env > plugin spec
            resolve routing:  request > env > plugin spec
            resolve provider: request > workflow env >
                              prompt env > prompt YAML metadata >
                              plugin spec > AI_PLATFORM_DEFAULT_PROVIDER
            instantiate PromptBackedWorkflowHandler
```

Each `WorkflowPluginSpec` is an immutable frozen dataclass carrying
`workflow_name`, `category`, `prompt_id`, `version`, `description`, `model`,
`routing_hint`, `default_provider`, `requires_json`, `ocr_tool_name`,
`approval_type`, `tool_names`, `tags`, `metadata`, `retry_policy`,
`deprecated`, `composable`, and `composed_of`.

Registry capabilities:

* `register / unregister / enable / disable / require / get`
* `list_all / list_enabled / list_by_category / registered_names / enabled_names`
* `summary()` returns totals and per-category counts for metrics
* `add_listener / remove_listener` for `REGISTERED`, `UNREGISTERED`,
  `ENABLED`, `DISABLED` events. Listener exceptions are swallowed by the
  registry and logged; they never break a write.
* Thread-safe via `RLock`.

The registry is exposed through:

* `ContainerProtocol.workflow_plugin_registry`
* FastAPI dependency `get_workflow_plugin_registry`
* Public HTTP API `GET /v1/workflows` (see [api.md §5.5](api.md#55-workflow-discovery))

`AICommandRequest.workflow` validates only the identifier pattern
(`^[a-z][a-z0-9_]*$`). Dispatch against an unregistered or disabled name
fails fast with `workflow_not_found`.

For the full workflow catalog and the procedure to add a new workflow see
[workflows.md](workflows.md).

## 7. Provider Routing

The provider router maps routing hints to ordered provider chains:

| Hint | Chain |
|------|-------|
| `premium_communication` | Anthropic -> OpenRouter |
| `structured_json` | OpenAI -> OpenRouter |
| `long_context` | Gemini -> OpenAI -> OpenRouter |
| `bulk_processing` | DeepSeek -> OpenRouter |
| `fallback` | OpenRouter |
| `auto` | OpenAI -> OpenRouter |

Embedding overrides the hint and routes through OpenAI -> Gemini. A tenant
policy store can restrict or override provider choices. The standalone build
ships in-memory policy/quota stores; production should replace them with a
durable store.

Provider calls use retry/failover handling and circuit breakers from
[app/providers/resilience.py](../app/providers/resilience.py). Production
should use Redis-backed breaker state so all replicas share provider health.
Configured provider adapters also appear in aggregate health as
`provider:<name>` components. Local, staging, and Docker E2E validation use
the real OpenRouter adapter as `provider:openrouter`.

## 8. Deployment Topology

The production baseline is:

* API Deployment: FastAPI, HTTP 8000, readiness/liveness probes.
* Worker Deployment: `python -m app.workers.main`, independently scaled.
* PostgreSQL: managed service with backups and PITR.
* Redis: managed service for queue, rate limit, idempotency, and breaker state
  in small deployments; larger deployments should split queue from cache.
* OpenTelemetry collector and Prometheus scrape target.

Reference manifests live in [k8s](../k8s). Docker Compose is available for
local/staging smoke runs. See [deployment.md](deployment.md) and
[worker-operations.md](worker-operations.md).

## 9. Security Boundaries

Every state-changing request is tenant-bound and role-checked. Production
startup requires request signing, RBAC, Redis-backed shared state, encryption
keys, provider credentials, and OTLP configuration. See [security.md](security.md),
[authentication.md](authentication.md), and [configuration.md](configuration.md).

## 10. Observability

Every request/workflow carries `trace_id`, `tenant_id`, and `workflow_id`.
Logs use structlog, traces use OpenTelemetry, and metrics use Prometheus. The
operator flow for an incident is: find `trace_id`, inspect workflow status,
read event/audit rows, then inspect provider/router metrics.

## 11. Tenant Entitlement & Access Control

The platform includes a decoupled access control system to manage tenant permissions and billing status:

*   **TenantAccessRecord:** A high-performance local cache stored in the AI service database. It stores the `status` (active/suspended/expired) and `plan_tier` (free/pro/enterprise).
*   **Decoupled Sync:** The AI service listens to generic Redis events (e.g., `events.billing.subscription_status_updated`) broadcast by an external Payment service. It updates its local permit cache as events arrive.
*   **Enforcement Guard:** The `ensure_tenant_access` middleware optionally blocks workflows for tenants without a valid permit.
*   **Data Purity:** The AI service stores zero financial or payment provider data (no Stripe IDs, no credit card info). It only tracks the "Yes/No" permission to execute.

To enable strict payment-based blocking in production, set `AI_PLATFORM_BILLING_ENFORCED="true"`.