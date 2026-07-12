# API Reference

This document is the authoritative external contract. Anything not described
here is **not part of the public API** and may change without notice.

## 1. Conventions

* Endpoints return `application/json` except `/metrics`
  (`text/plain; version=0.0.4`), SSE workflow streams
  (`text/event-stream`), and WebSocket workflow status subscriptions.
* All command endpoints accept and return UTF-8 JSON only.
* Times are RFC 3339 UTC (`2026-05-18T12:30:00Z`).
* All resource identifiers match `^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$`.
* Successful command submissions return **HTTP 202 Accepted** (work is queued,
  not finished).
* Successful status reads return **HTTP 200 OK**.
* Every response carries a `trace_id`.

## 2. Headers

| Header | Required | Notes |
|--------|----------|-------|
| `Content-Type: application/json` | yes | on every POST |
| `x-tenant-id` | yes | tenant scope; forwarded by your gateway, trusted without validation |
| `x-principal-id` | recommended | who is calling on behalf of the tenant; forwarded by your gateway, trusted without validation |
| `x-trace-id` | optional | server generates one if absent |
| `Idempotency-Key` | recommended for retried POSTs | deduplicates state-changing requests for the configured TTL |

This service performs no authentication or authorization; see
[authentication.md](authentication.md) for the trust model.

## 3. Error envelope

All error responses use this shape:

```json
{
  "success": false,
  "trace_id": "01HX2N5G6E0X4Z7V8YQK0V8RPT",
  "error": {
    "code": "validation_error",
    "message": "context_ids contains duplicates",
    "details": { "field": "context_ids" }
  }
}
```

Common `error.code` values:

| Code | HTTP | Meaning |
|------|------|---------|
| `validation_error` | 422 | Pydantic validation failed, including payload-size/depth checks. |
| `workflow_not_found` | 404 | Workflow not in tenant scope. |
| `job_not_found` | 404 | Job not in tenant scope. |
| `idempotency_key_conflict` | 409 | Duplicate key with differing payload. |
| `idempotency_key_in_progress` | 409 | Duplicate key while the first request is still running. |
| `workflow_state_conflict` | 409 | Callback does not match the workflow’s current waiting state. |
| `quota_exceeded` | 429 | Token/RPM/cost quota hit. |
| `service_unavailable` | 503 | Readiness component degraded or upstream failure. |

## 4. Limits

| Limit | Value | Source |
|-------|-------|--------|
| Max context_ids per request | 50 | `MAX_CONTEXT_IDS` |
| Max payload bytes | 256 KiB | `MAX_PAYLOAD_BYTES` |
| Max payload nesting depth | 16 | `MAX_PAYLOAD_DEPTH` |
| Identifier max length | 128 | `MAX_IDENTIFIER_LENGTH` |
| `max_input_tokens` default / cap | 100 000 / 1 000 000 | `TokenBudget` |
| `max_output_tokens` default / cap | 4 096 / 200 000 | `TokenBudget` |
| `max_total_tokens` default / cap | 120 000 / 1 200 000 | `TokenBudget` |
| `timeout_seconds` range | 1 – 604 800 | per request |
| `max_attempts` range | 1 – 10 | per request |

## 5. Capability endpoints

All six capability endpoints share the same request shape (`AICommandRequest`)
and response shape (`QueuedWorkflowResponse`). They differ only in the
`AICapability` they imply and the routing they trigger.

`AICommandRequest.workflow` accepts **any registered workflow identifier**
matching `^[a-z][a-z0-9_]*$` (3–128 chars). The set of registered workflows
is exposed dynamically via `GET /v1/workflows` (see §5.5) and is no longer
fixed by a closed enum.

### 5.1 Request body — `AICommandRequest`

```json
{
  "tenant_id": "tenant_acme",
  "workflow": "support_automation",
  "task": "generate_customer_reply",
  "payload": { "message": "..." },
  "context": {
    "brand": { "tone": "concise" },
    "case": { "order_id": "8821" }
  }
}
```

`context_ids`, `context`, `provider`, `token_budget`, `timeout_seconds`, and
`max_attempts` are optional request controls. Omit them unless the call needs
versioned stored context, inline context, provider pinning, a custom token
budget, a custom timeout, or a custom retry count.

Field rules:

| Field | Type | Notes |
|-------|------|-------|
| `tenant_id` | string | must match `x-tenant-id` header |
| `workflow` | string | any registered workflow identifier matching `^[a-z][a-z0-9_]*$`; discover dynamically via `GET /v1/workflows` |
| `task` | string | free-form identifier, max 128 chars |
| `context_ids` | string[]? | up to 50, unique, identifier pattern; resolves stored tenant context |
| `context` | object? | inline per-request context, ≤ 256 KiB, depth ≤ 16 |
| `payload` | object | arbitrary JSON, ≤ 256 KiB, depth ≤ 16 |
| `provider` | object? | optional hint; router may override |
| `token_budget` | object? | enforced server-side |
| `timeout_seconds` | int? | 1..604800; default workflow-specific |
| `max_attempts` | int? | 1..10; default workflow-specific |

#### 5.1.1 `provider`

| Field | Type | Notes |
|-------|------|-------|
| `provider` | enum | `openai`, `gemini`, `anthropic`, `deepseek`, `openrouter`, `xai`, `mistral`, `groq`, `cerebras`, `nvidia`. Optional override; omit the block to use workflow defaults from env. Use `openai` with `base_url` override to target Ollama-compatible endpoints. |
| `model` | string | optional when `provider` is set. Use it only when pinning a specific model instead of the env-configured workflow default. |
| `required_capability` | enum | one of `generate`, `classify`, `extract`, `embed`, `rerank`, `summarize`, `workflow`. Must be supported by the chosen provider. |

#### 5.1.2 `token_budget`

| Field | Type | Notes |
|-------|------|-------|
| `max_input_tokens` | int | ≤ 1 000 000; default 100 000 |
| `max_output_tokens` | int | ≤ 200 000; default 4 096 |
| `max_total_tokens` | int | ≤ 1 200 000; default 120 000; must be ≥ inputs + outputs |
| `estimated_input_tokens` | int? | optional; helps the router pick long-context providers |

#### 5.1.3 Workflow payload examples

`ai_communication_automation` is intended for structured outbound and follow-up messaging.
Omit the `provider` block to use env-configured workflow defaults.

Email follow-up draft:

```json
{
  "tenant_id": "tenant_acme",
  "workflow": "ai_communication_automation",
  "task": "draft_customer_follow_up",
  "payload": {
    "channel": "email",
    "objective": "post_support_follow_up",
    "audience": "existing_customer",
    "message": "Check whether the customer still needs help after the delivery issue.",
    "tool_request": {
      "tool_name": "thread_history_lookup",
      "tool_payload": { "thread_id": "email_thread_8821" }
    }
  },
  "context": {
    "brand": { "tone": "clear and warm" },
    "customer": { "id": "customer_8821" }
  }
}
```

WhatsApp outreach draft:

```json
{
  "tenant_id": "tenant_acme",
  "workflow": "ai_communication_automation",
  "task": "draft_whatsapp_update",
  "payload": {
    "channel": "whatsapp",
    "objective": "shipping_update",
    "audience": "customer",
    "message": "Send a short WhatsApp update about the delayed shipment.",
    "tool_request": {
      "tool_name": "customer_context_lookup",
      "tool_payload": { "customer_id": "customer_8821", "order_id": "8821" }
    }
  },
  "context": {
    "brand": { "tone": "brief and reassuring" },
    "locale": "en-IN"
  }
}
```

Lead follow-up that requires approval before send:

```json
{
  "tenant_id": "tenant_acme",
  "workflow": "ai_communication_automation",
  "task": "draft_lead_follow_up",
  "payload": {
    "channel": "email",
    "objective": "lead_reengagement",
    "audience": "qualified_lead",
    "message": "Draft a follow-up for the lead who paused after the pricing discussion.",
    "requires_approval": true,
    "tool_request": {
      "tool_name": "crm_account_lookup",
      "tool_payload": { "account_id": "acct_441", "lead_id": "lead_778" }
    }
  },
  "context": {
    "brand": { "tone": "confident and consultative" },
    "campaign": { "name": "q2_reactivation" }
  }
}
```

### 5.2 Response body — `QueuedWorkflowResponse` (HTTP 202)

```json
{
  "success": true,
  "trace_id": "01HX2N5G6E0X4Z7V8YQK0V8RPT",
  "job_id": "a9f3c1f7e8c44f4ba642cfb0c2d6764e",
  "workflow_id": "d65cb4dc8e624d209344a41c1f7922dd",
  "status": "QUEUED",
  "workflow": "support_automation"
}
```

### 5.3 Endpoints

| Method | Path | Capability |
|--------|------|------------|
| POST | `/v1/generate` | generate |
| POST | `/v1/classify` | classify |
| POST | `/v1/extract` | extract |
| POST | `/v1/embed` | embed |
| POST | `/v1/rerank` | rerank |
| POST | `/v1/summarize` | summarize |
| POST | `/v1/workflows/run` | workflow (full pipeline) |

Notes:

* `/v1/workflows/run` accepts `WorkflowRunRequest` which extends
  `AICommandRequest` and additionally requires that `payload`, `context`, **or**
  `context_ids` is non-empty.
* The hidden alias `POST /v1/workflows` is accepted by some deployments but
  not part of the contract — always use `/v1/workflows/run`.
* `/v1/...` endpoints are the public contract. Any unversioned compatibility
  aliases are hidden from OpenAPI and should not be used by integrations.

### 5.4 Capability/provider compatibility matrix

The platform supports these provider names: `openai`, `gemini`, `anthropic`,
`deepseek`, `openrouter`, `xai`, `mistral`, `groq`, `cerebras`, `nvidia`.
Ollama-compatible runtimes are used through the `openai` provider with a base
URL override.

Representative capability support:

| Capability | OpenAI | Anthropic | Gemini | DeepSeek | OpenRouter | xAI | Mistral | Groq | Cerebras | NVIDIA |
|------------|--------|-----------|--------|----------|------------|-----|---------|------|----------|--------|
| generate | yes | yes | yes | yes | yes | yes | yes | yes | yes | yes |
| classify | yes | yes | yes | yes | yes | yes | yes | yes | yes | yes |
| extract | yes | yes | yes | yes | yes | yes | yes | yes | yes | yes |
| summarize | yes | yes | yes | yes | yes | yes | yes | yes | yes | yes |
| rerank | yes | yes | yes | yes | yes | yes | yes | yes | yes | yes |
| embed | yes | no | yes | no | yes | no | yes | no | no | no |

If a request pins a provider that does not support the requested capability,
the API returns HTTP 422 `validation_error`.

### 5.5 Workflow discovery

```text
GET /v1/workflows
GET /v1/workflows?category=<category>
GET /v1/workflows?enabled_only=true
```

Returns every workflow registered with the plugin registry
([app/workflows/plugin_registry.py](../app/workflows/plugin_registry.py)).
Clients should treat this endpoint as the authoritative list of valid
`workflow` values for capability and workflow-run POSTs.

**Query parameters**

| Name | Type | Default | Notes |
|------|------|---------|-------|
| `category` | string | – | One of `core_ai`, `tooling`, `documents`, `communication`, `calendar`, `recruitment`, `crm`, `commerce`, `analytics`, `future`, `custom`, `legacy`. Unknown categories return an empty list (HTTP 200). |
| `enabled_only` | bool | `false` | When `true`, only workflows currently enabled for dispatch are returned. |

**Response**

```json
{
  "workflows": [
    {
      "workflow_name": "support_automation",
      "category": "legacy",
      "prompt_id": "support.customer_response",
      "version": "1.0.0",
      "description": "E-commerce support reply generation.",
      "model": null,
      "routing_hint": "bulk_processing",
      "default_provider": null,
      "requires_json": true,
      "ocr_tool_name": null,
      "approval_type": null,
      "tool_names": [],
      "tags": ["support", "legacy"],
      "metadata": {},
      "retry_policy": {
        "max_attempts": 3,
        "initial_backoff_seconds": 1.0,
        "max_backoff_seconds": 60.0,
        "jitter_ratio": 0.1
      },
      "registered_at": "2026-05-18T12:00:00+00:00",
      "deprecated": false,
      "composable": false,
      "composed_of": [],
      "enabled": true
    }
  ],
  "summary": {
    "total": 52,
    "enabled": 52,
    "disabled": 0,
    "disabled_names": [],
    "by_category": {
      "legacy": 8,
      "core_ai": 7,
      "communication": 8,
      "...": 0
    }
  }
}
```

**Notes**

* Workflow names must match `^[a-z][a-z0-9_]*$` (3–128 chars). Names that
  fail the pattern return `validation_error` at request time; names that
  pass the pattern but are not in the registry return `workflow_not_found`
  at dispatch.
* Categories are stable; new categories require a platform release.
* See [workflows.md](workflows.md) for the full registry contract.

## 6. Status endpoints

### 6.1 `GET /v1/jobs/{job_id}` and `GET /v1/workflows/{workflow_id}`

Query parameters:

| Name | Required | Notes |
|------|----------|-------|
| `tenant_id` | yes | must equal `x-tenant-id` |

Response body — `JobStatusResponse` (`WorkflowStatusResponse` for the other endpoint):

```json
{
  "success": true,
  "trace_id": "01HX…",
  "workflow_id": "...",
  "job_id": "...",
  "status": "RUNNING",
  "workflow": "support_automation",
  "attempt_count": 1,
  "max_attempts": 3,
  "next_attempt_at": null,
  "timeout_at": "2026-05-18T12:30:00Z",
  "pending_action": null,
  "result": null,
  "error": null
}
```

If the workflow is paused, `pending_action` is populated instead of `result`:

```json
{
  "status": "WAITING_TOOL",
  "pending_action": {
    "kind": "tool",
    "tool_name": "order_lookup",
    "tool_payload": { "order_id": "8821" }
  },
  "result": null,
  "error": null
}
```

Terminal states:

* `SUCCESS` – `result` contains workflow output, `error` is null.
* `FAILED` – `error` contains `{code, message, details}`; if retries remain
  (set by the engine, distinct from the request `max_attempts`) the engine may
  transition back to `QUEUED` automatically.
* `CANCELLED` – caller cancelled the workflow before terminal completion.
* `DEAD` – all retries exhausted; manual replay required.

### 6.2 Real-time workflow updates

Use Server-Sent Events for browser-friendly polling without opening a custom
socket protocol:

```http
GET /v1/realtime/workflows/{workflow_id}/events?tenant_id=tenant_acme
Accept: text/event-stream
```

Each event is named `workflow.status` and carries the same status fields as
`GET /v1/workflows/{workflow_id}`. The stream closes after a terminal state or
`AI_PLATFORM_REALTIME_MAX_STREAM_SECONDS`.

WebSocket clients can subscribe at:

```text
/v1/realtime/workflows/{workflow_id}/ws?tenant_id=tenant_acme
```

The WebSocket sends JSON status snapshots and then closes after terminal state
or timeout. WebSocket clients must provide the tenant id in query params and,
for non-browser clients, should also send the configured tenant header.

### 6.3 Multi-agent orchestration

`POST /v1/agents/orchestrations` queues several specialist workflow agents as
one persisted orchestration. The API returns immediately with child workflow
ids; workers execute each child through the normal workflow engine.

```json
{
  "tenant_id": "tenant_acme",
  "objective": "triage and draft a support response",
  "strategy": "parallel",
  "tasks": [
    {
      "agent_name": "classifier",
      "role": "classification",
      "workflow": "support_automation",
      "task": "classify_intent",
      "payload": {"message": "Refund my order"}
    },
    {
      "agent_name": "reply_writer",
      "role": "response_generation",
      "workflow": "support_automation",
      "task": "draft_reply",
      "payload": {"message": "Refund my order"}
    }
  ]
}
```

Status is available at:

```http
GET /v1/agents/orchestrations/{orchestration_id}?tenant_id=tenant_acme
```

Both endpoints are tenant-scoped via `x-tenant-id`.

### 6.4 Callback endpoints

When `status` is `WAITING_TOOL` or `WAITING_APPROVAL`, the client reads
`pending_action` and resumes the workflow by posting to one of these endpoints.

#### `POST /v1/workflows/{workflow_id}/tool-results`

Request body:

```json
{
  "tenant_id": "tenant_acme",
  "tool_name": "order_lookup",
  "result": {
    "order_id": "8821",
    "status": "shipped",
    "tracking_url": "https://example.com/track/8821"
  }
}
```

Rules:

* The workflow must currently be `WAITING_TOOL`.
* `tool_name` must match `pending_action.tool_name` exactly.
* Success returns `WorkflowStatusResponse`, usually with `status: QUEUED` and
  `pending_action: null`; a worker then leases the workflow and continues.
* A state mismatch returns HTTP 409 `workflow_state_conflict`.

#### `POST /v1/workflows/{workflow_id}/approvals`

Approve:

```json
{
  "tenant_id": "tenant_acme",
  "approval_type": "manager_sign_off",
  "decision": "approve",
  "approval_payload": { "comment": "Approved for send" }
}
```

Reject:

```json
{
  "tenant_id": "tenant_acme",
  "approval_type": "manager_sign_off",
  "decision": "reject",
  "reason": "Tone is too informal"
}
```

Rules:

* The workflow must currently be `WAITING_APPROVAL`.
* `approval_type` must match `pending_action.approval_type` exactly.
* Approve usually returns `status: QUEUED`; a worker then leases the workflow
  and continues. Reject returns `status: FAILED`.
* A state mismatch returns HTTP 409 `workflow_state_conflict`.

#### `DELETE /v1/workflows/{workflow_id}`

Cancels a non-terminal workflow. Query parameters:

| Name | Required | Notes |
|------|----------|-------|
| `tenant_id` | yes | must equal `x-tenant-id` |
| `reason` | no | defaults to `cancelled_by_caller` |

Success returns `WorkflowStatusResponse` with `status: CANCELLED`. Cancelling
an already terminal workflow returns HTTP 409 `workflow_state_conflict`.

## 7. Operational endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health` | aggregate health, returns 503 when any component is degraded |
| GET | `/health/live` | process liveness, always 200 when the API process can respond |
| GET | `/health/ready` | full-stack readiness, returns 503 when any component is degraded |
| GET | `/metrics` | Prometheus text exposition |
| GET | `/v1/metrics` | same as `/metrics` (versioned alias) |
| POST | `/v1/agents/orchestrations` | queue a persisted multi-agent orchestration |
| GET | `/v1/agents/orchestrations/{orchestration_id}` | read orchestration and child workflow status |
| GET | `/v1/realtime/workflows/{workflow_id}/events` | SSE workflow status stream |
| WS | `/v1/realtime/workflows/{workflow_id}/ws` | WebSocket workflow status snapshots |
| GET | `/v1/workflows/dead-letter` | list tenant dead-lettered workflows |
| POST | `/v1/workflows/{workflow_id}/dead-letter/replay` | requeue a dead-lettered workflow |
| DELETE | `/v1/workflows/{workflow_id}` | cancel a non-terminal workflow |

Health responses are not wrapped in the standard `success` envelope. The only
top-level statuses are `ok` and `degraded`. Readiness currently checks:

* `postgresql` - executes a database round trip.
* `redis` - sends a Redis `PING`.
* `event_store` - verifies `event_store`, `event_snapshots`, and
  `workflow_runs` tables are present.
* `workflow_queue` - reports ready, delayed, leased, and total job counts for
  the base queue, retry queue, and dead-letter queue.
* `workflow_worker` - requires at least one fresh Redis heartbeat from a
  worker process.
* `provider:<name>` - one component per configured provider adapter, for
  example `provider:openrouter`.

Health response example:

```json
{
  "trace_id": "01HX…",
  "status": "ok",
  "service": "Multi-Tenant AI Platform",
  "environment": "production",
  "version": "1.0.0",
  "checked_at": "2026-05-18T10:40:32.000000Z",
  "components": [
    {"name": "postgresql", "status": "ok", "latency_ms": 4.0, "error": null, "details": {"driver": "asyncpg"}},
    {"name": "redis", "status": "ok", "latency_ms": 1.2, "error": null, "details": {"backend": "redis"}},
    {"name": "event_store", "status": "ok", "latency_ms": 2.1, "error": null, "details": {"tables": "event_store,event_snapshots,workflow_runs"}},
    {"name": "workflow_queue", "status": "ok", "latency_ms": 3.3, "error": null, "details": {"workflow_queue.ready_jobs": "0", "workflow_queue.total_jobs": "0"}},
    {"name": "workflow_worker", "status": "ok", "latency_ms": 2.0, "error": null, "details": {"active_workers": "1", "observed_workers": "1"}},
    {"name": "provider:openrouter", "status": "ok", "latency_ms": 8.7, "error": null, "details": {"provider": "openrouter", "provider_status": "ok"}}
  ]
}
```

## 8. Idempotency

Pass `Idempotency-Key` (recommended ≤ 128 chars, identifier pattern) to make
command submission idempotent for a 24h window:

* Same key + same payload → same `job_id`, HTTP 202.
* Same key + different payload → HTTP 409 `idempotency_key_conflict`.
* Same key while the first request is still running → HTTP 409
  `idempotency_key_in_progress`.
* No key → every submission creates a new workflow.

## 9. Versioning

* The path prefix `/v1/` is part of the contract; breaking changes will be
  delivered under `/v2/`.
* Response payloads are forward-compatible: clients **must** ignore unknown
  fields.
* Enum extensions (new `workflow`, new `status`, new error codes) are
  treated as additive and shipped without a version bump.

## 10. Out of contract

Endpoints under `/internal/`, admin routes, and anything not listed here are
not part of the integration contract. Do not depend on them.
