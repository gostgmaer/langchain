# Getting Started

This guide takes an external integrator from "no access" to "first successful
workflow" in a single sitting. Read this before [api.md](api.md).

## 1. What this platform is

The Multi-Tenant AI Operating Platform is an HTTP service. You send commands
(generate, classify, extract, embed, rerank, summarize, run workflow), the
platform queues them, executes them asynchronously, and exposes their state
through polling endpoints. It owns prompts, providers, retries, and workflow
state. It never owns your business data.

* You **do not** call OpenAI/Anthropic/Gemini directly.
* You **do not** manage retries or backoff.
* You **do not** persist prompts.
* You **do** identify the tenant on every call.
* You **do** poll for status (or accept callbacks once webhooks are enabled —
  see [webhooks.md](webhooks.md)).

## 2. Prerequisites

Before you integrate, your team needs:

| Item | Provided by | Notes |
|------|-------------|-------|
| `tenant_id` | Platform admin | Unique stable id. Pattern `^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$`. |
| API base URL | Platform admin | e.g. `https://ai.example.com` |
| Principal id | Caller-defined | Stable identifier for the human or service calling on behalf of the tenant. |
| Workflow names you may run | Platform admin | Identifiers matching `^[a-z][a-z0-9_]*$`; discover at runtime via `GET /v1/workflows`. See [workflows.md](workflows.md). |

This service performs no authentication or authorization itself; it trusts
the `x-tenant-id`/`x-principal-id` headers forwarded by your API gateway.
See [authentication.md](authentication.md).

## 3. Environments

The platform exposes the same contract in every environment. The only
differences are URL and quotas.

| Environment | Purpose | Stability |
|-------------|---------|-----------|
| `local` | Developer machines | unstable |
| `dev` | Pre-merge integration | unstable |
| `staging` | Pre-prod, prod-equivalent | high |
| `production` | Live traffic | high |

Configure your client with the environment’s base URL — never embed
provider-specific URLs (OpenAI etc.) directly in your code.

## 4. Required HTTP headers

Every API call must include:

| Header | Required | Example | Source of truth |
|--------|----------|---------|-----------------|
| `Content-Type` | yes | `application/json` | always |
| `x-tenant-id` | yes | `tenant_acme` | matches body `tenant_id` |
| `x-principal-id` | recommended | `user_42` or `svc_email_bot` | the caller |
| `x-trace-id` | optional | `01HX…` ULID/UUID | generated server-side if absent |

These identity headers are forwarded by your API gateway; this service trusts
them without validation. See [authentication.md](authentication.md).

## 5. Your first call (end-to-end)

This example sends a single generation command and polls for its result.

### 5.1 Submit the workflow

```http
POST /v1/generate HTTP/1.1
Host: ai.example.com
Content-Type: application/json
x-tenant-id: tenant_acme
x-principal-id: user_42

{
  "tenant_id": "tenant_acme",
  "workflow": "support_automation",
  "task": "generate_customer_reply",
  "payload": {
    "message": "Where is my order?",
    "channel": "email"
  },
  "context": {
    "brand": { "tone": "concise" },
    "case": { "order_id": "8821" }
  }
}
```

### 5.2 Response (HTTP 202)

```json
{
  "success": true,
  "job_id": "a9f3c1f7e8c44f4ba642cfb0c2d6764e",
  "workflow_id": "d65cb4dc8e624d209344a41c1f7922dd",
  "trace_id": "01HX2N5G6E0X4Z7V8YQK0V8RPT",
  "status": "QUEUED",
  "workflow": "support_automation"
}
```

**Persist `job_id`, `workflow_id`, and `trace_id` immediately.** They are
your only handles to the workflow.

### 5.3 Poll for status

```http
GET /v1/jobs/a9f3c1f7e8c44f4ba642cfb0c2d6764e?tenant_id=tenant_acme HTTP/1.1
Host: ai.example.com
x-tenant-id: tenant_acme
x-principal-id: user_42
```

Possible responses (HTTP 200):

```json
{ "success": true, "workflow_id": "...", "job_id": "...", "trace_id": "...",
  "status": "RUNNING", "workflow": "support_automation",
  "attempt_count": 1, "max_attempts": 3,
  "next_attempt_at": null, "timeout_at": "2026-05-18T12:30:00Z",
  "result": null, "error": null }
```

```json
{ "success": true, "workflow_id": "...", "job_id": "...", "trace_id": "...",
  "status": "SUCCESS", "workflow": "support_automation",
  "attempt_count": 1, "max_attempts": 3,
  "next_attempt_at": null, "timeout_at": "2026-05-18T12:30:00Z",
  "result": { "reply": "Your order #8821 shipped on 2026-05-17…",
              "tone": "supportive", "next_action": "await_customer" },
  "error": null }
```

Workflow states: `QUEUED → RUNNING → (WAITING_TOOL | WAITING_APPROVAL)* → SUCCESS | FAILED | DEAD`.

### 5.4 Recommended polling cadence

| Workflow type | Initial delay | Cadence | Max wait |
|---------------|---------------|---------|----------|
| Interactive (single generation) | 200 ms | 250 ms exponential to 2 s | 30 s |
| Heavy (job automation, OCR) | 1 s | 2 s exponential to 15 s | timeout + 30 s |
| Approval-bound | 5 s | 30 s | configured `timeout_seconds` |

Stop polling on any terminal status: `SUCCESS`, `FAILED`, `CANCELLED`, `DEAD`.

## 6. Error handling primer

* **HTTP 422** – payload rejected by Pydantic or payload-limit validation. Fix the request; do not retry.
* **HTTP 401 / 403** – returned by your API gateway, not this service (this
  service performs no authentication/authorization of its own).
* **HTTP 409** – idempotency conflict. Use a different idempotency key.
* **HTTP 422** – workflow-specific business validator rejected payload. Do not retry.
* **HTTP 429** – tenant quota exceeded. Honor `Retry-After`.
* **HTTP 503** – platform is unhealthy. Retry with exponential backoff.

See [api.md](api.md) for the full error envelope.

## 7. Reference vocabulary

| Term | Meaning |
|------|---------|
| Workflow | A named, multi-step procedure (`job_automation`, `support_automation`, …). |
| Task | A free-form identifier you choose to label *this* invocation. Used for routing prompts and metrics. |
| Context | A versioned named object (brand voice, candidate profile, contract clause) resolved via `context_ids`. |
| Provider | Underlying LLM vendor (OpenAI, Anthropic, …). Selected by the router. |
| Capability | One of `generate`, `classify`, `extract`, `embed`, `rerank`, `summarize`, `workflow`. |
| `trace_id` | End-to-end correlation id. |
| `job_id` | A single attempt of a workflow. |
| `workflow_id` | The overall workflow instance (may span multiple `job_id`s through retries). |

## 8. Next steps

1. Read [api.md](api.md) for the complete contract.
2. Read [authentication.md](authentication.md) before going beyond local dev.
3. Read [workflows.md](workflows.md) for state-machine semantics.
4. Pick the example closest to your use case in
   [integration-guide.md](integration-guide.md).
5. If you need tenant-specific behavior without deployment, use
  [custom-workflow-cookbook.md](custom-workflow-cookbook.md).
6. Use the reference clients in [sdk-examples.md](sdk-examples.md) if you need
  a submit/poll implementation quickly.
7. Before shipping, read [production-checklist.md](production-checklist.md).
