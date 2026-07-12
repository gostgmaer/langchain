# End-to-End Validation

Use this checklist to prove an integration works from submission through final
workflow state. It complements [integration-guide.md](integration-guide.md),
which contains the request examples.

## 1. Environment Readiness

Before running workflow scenarios, verify:

* API returns `200` from `/health/live`.
* API returns `200` from `/health/ready` with `status: "ok"`.
* `/health/ready` has `ok` components for `postgresql`, `redis`,
  `event_store`, `workflow_queue`, `workflow_worker`, and each configured
   provider such as `provider:gemini` and `provider:openrouter`.
* At least one worker process is running and publishing a fresh Redis heartbeat.
* Postgres migrations are at `head`.
* Redis is reachable from API and workers.
* A real Gemini credential is configured, a real OpenRouter credential is
   configured, and `AI_PLATFORM_PROVIDER_FALLBACK=openrouter` is set.
* Production-like environments use signing, RBAC, Redis idempotency, Redis rate
  limiting, and Redis provider circuit breakers.

## 2. Universal Flow

Every scenario follows the same control loop:

1. Submit `POST /v1/workflows/run` or the capability endpoint.
2. Persist `trace_id`, `workflow_id`, and `job_id` from HTTP 202.
3. Poll `GET /v1/workflows/{workflow_id}?tenant_id=...` with backoff.
4. If `status == WAITING_TOOL`, execute the named tool and post
   `/v1/workflows/{workflow_id}/tool-results`.
5. If `status == WAITING_APPROVAL`, collect a decision and post
   `/v1/workflows/{workflow_id}/approvals`.
6. Continue polling until `SUCCESS`, `FAILED`, `CANCELLED`, or `DEAD`.
7. Store the final result or error alongside your business record.

Tool and approval callbacks return `QUEUED` after a successful resume. That is
expected: the next worker lease performs the continuation step.

## 3. Scenario Matrix

| Scenario | Submit | Expected pause | Callback | Terminal expectation |
|----------|--------|----------------|----------|----------------------|
| AI communication follow-up | `ai_communication_automation` with `tool_request.crm_account_lookup` and `requires_approval=true` | `WAITING_TOOL` then `WAITING_APPROVAL` | tool result, then approval | `SUCCESS` with structured communication draft |
| Email support reply | `support_automation` with `tool_request.order_lookup` | `WAITING_TOOL` | `order_lookup` result | `SUCCESS` with `reply` |
| Telegram bot reply | `support_automation` without tool request | none | none | `SUCCESS` within short timeout |
| WhatsApp invoice | `support_automation` with `tool_request.invoice_lookup` | `WAITING_TOOL` | `invoice_lookup` result | `SUCCESS` with attachment/reference |
| Job automation | `job_automation` with `requires_approval=true` | `WAITING_APPROVAL` | approve or reject | approve -> `SUCCESS`, reject -> `FAILED` |
| Document intelligence | `document_intelligence` with `document_uri` | `WAITING_TOOL` | `document_ocr` result | `SUCCESS` with clauses/summary |
| Calendar scheduling | `calendar_automation` with `tool_request.calendar_freebusy` | `WAITING_TOOL` | `calendar_freebusy` result | `SUCCESS` with calendar request |
| CRM follow-up | `crm_workflow` with `requires_approval=true` | `WAITING_APPROVAL` | approve or reject | approve -> `SUCCESS`, reject -> `FAILED` |

## 4. Negative Scenarios

Run these before go-live:

| Scenario | Expected result |
|----------|-----------------|
| Body `tenant_id` differs from `x-tenant-id` | HTTP 403 `tenant_access_denied` |
| Missing role for submit | HTTP 403 `permission_denied` |
| Reuse `Idempotency-Key` with different body | HTTP 409 `idempotency_key_conflict` |
| Wrong `tool_name` for waiting workflow | HTTP 409 `workflow_state_conflict` |
| Wrong `approval_type` for waiting workflow | HTTP 409 `workflow_state_conflict` |
| Reject an approval | final `FAILED` with approval rejection error |
| Cancel a queued/running workflow | final `CANCELLED` |
| Provider unavailable | fallback provider or retry/dead-letter according to policy |

## 5. Evidence to Capture

For each scenario, capture:

* Request body and response envelope with secrets removed.
* Final status response.
* `trace_id`, `workflow_id`, `job_id`, tenant id, workflow name, and task.
* Any tool/approval callback payloads with PII redacted.
* Provider routing result in `result.provider` or `PROVIDER_SELECTED` events.
* Logs/traces proving the workflow crossed API and worker processes.

## 6. Load and Soak

After functional validation, run [load/k6-workflows.js](../load/k6-workflows.js)
against a staging or canary tenant. The script submits workflow-shaped payloads
for support, job, calendar, CRM, and document workloads and accepts HTTP 202 or
expected HTTP 429 throttling.

Start with the smoke profile. Increase `PEAK_VUS` only after queue depth,
worker latency, provider error rate, and dead-letter count are stable.