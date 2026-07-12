# Workflows

A **workflow** is a named, multi-step procedure with an explicit lifecycle,
durable state, an event log, retry policy, and a deadline. This document
defines the lifecycle and how integrators interact with it.

## 1. Workflow plugin registry

Workflows are no longer hardcoded into the API. At startup the container
builds a plugin-based registry ([app/workflows/plugin_registry.py](../app/workflows/plugin_registry.py))
populated by [app/workflows/plugins/](../app/workflows/plugins). Each plugin
contributes one or more `WorkflowPluginSpec` records that declare:

* `workflow_name` (lower_snake_case identifier; any `^[a-z][a-z0-9_]*$`)
* `category` (one of the values in §1.2)
* `prompt_id`, `version`, `description`
* `model`, `routing_hint`, `default_provider`, `requires_json`
* `approval_type` (optional human-in-the-loop gate)
* `ocr_tool_name` (optional OCR pre-step)
* `retry_policy`, `tags`, `metadata`, `deprecated`, `composable`, `composed_of`

The registry is thread-safe, supports `register/unregister/enable/disable`,
emits structured events to listeners, and exposes a discovery API. New
workflows are added by dropping a `WorkflowPluginSpec` into one of the
plugin modules — **no schema, no enum, no API change is required**.

`AICommandRequest.workflow` accepts any identifier matching
`^[a-z][a-z0-9_]*$` (min 3, max 128 chars). Dispatch fails with
`workflow_not_found` if the name is not registered or is disabled.

### 1.1 Registered workflows (52)

The platform ships 52 built-in workflows across 11 categories. The
authoritative list is always `GET /v1/workflows` (see §1.3). Highlights:

| Category | Workflows |
|----------|-----------|
| `legacy` (8) | `ai_communication_automation`, `support_automation`, `job_automation`, `recruiter_automation`, `calendar_automation`, `crm_workflow`, `crm_workflows` *(deprecated alias of `crm_workflow`)*, `document_intelligence` |
| `core_ai` (7) | `classification_workflow`, `extraction_workflow`, `retrieval_workflow`, `generation_workflow`, `summarization_workflow`, `embedding_workflow`, `reranking_workflow` |
| `tooling` (4) | `tool_orchestration_workflow`, `approval_workflow`, `callback_workflow`, `notification_workflow` |
| `documents` (5) | `document_workflow`, `ocr_workflow`, `invoice_processing_workflow`, `contract_review_workflow`, `resume_parsing_workflow` |
| `communication` (8) | `email_workflow`, `email_reply_workflow`, `telegram_workflow`, `whatsapp_workflow`, `slack_workflow`, `discord_workflow`, `sms_workflow`, `auto_followup_workflow` |
| `calendar` (3) | `calendar_workflow`, `meeting_scheduling_workflow`, `reminder_workflow` |
| `recruitment` (4) | `job_matching_workflow`, `resume_selection_workflow`, `recruiter_reply_workflow`, `interview_followup_workflow` |
| `crm` (4) | `lead_qualification_workflow`, `lead_scoring_workflow`, `crm_followup_workflow`, `customer_support_workflow` |
| `commerce` (3) | `order_status_workflow`, `refund_workflow`, `complaint_resolution_workflow` |
| `analytics` (3) | `sentiment_analysis_workflow`, `anomaly_detection_workflow`, `reporting_workflow` |
| `future` (3) | `composite_workflow`, `agent_workflow`, `custom_workflow` |

Legacy pipelines (pre-plugin):

| Name | Pipeline | Typical use |
|------|----------|-------------|
| `ai_communication_automation` | tool_request? → approval? → generate | cross-channel customer, sales, and renewal communication drafting |
| `job_automation` | extract → embed → rerank → generate | match candidate ⇄ JD, draft outreach |
| `recruiter_automation` | extract → generate | premium recruiter replies, negotiations |
| `support_automation` | classify → extract → tool_request → generate | e-commerce email/chat support |
| `calendar_automation` | extract → validate → tool_request → generate | meeting extraction & scheduling |
| `crm_workflow` (alias `crm_workflows`) | classify → extract → generate | CRM follow-ups, segmented outreach |
| `document_intelligence` | ocr → extract → summarize | contracts, statements, invoices |

### 1.2 Categories

`WorkflowCategory` is a closed enum exposed in the registry and discovery
API:

`core_ai`, `tooling`, `documents`, `communication`, `calendar`,
`recruitment`, `crm`, `commerce`, `analytics`, `future`, `custom`, `legacy`.

### 1.3 Discovery endpoint

```text
GET /v1/workflows
GET /v1/workflows?category=communication
GET /v1/workflows?enabled_only=true
```

Returns every registered workflow with full spec metadata so clients can
build dynamic UIs and validate workflow names client-side. See
[api.md §5.5](api.md#55-workflow-discovery).

### 1.4 Operational behaviour

* **Enable/disable** — operators can disable a workflow at runtime
  (`registry.disable(name)`). Disabled workflows remain visible in
  `GET /v1/workflows` but are excluded from dispatch and from
  `enabled_only=true`.
* **Deprecation** — `crm_workflows` is registered with `deprecated=true`
  and a `deprecation_message`. Integrators should migrate to `crm_workflow`.
* **Versioning** — every spec carries a SemVer `version`. Bumping the
  version after a behaviour change lets callers pin on a known shape.
* **Defaults override precedence** — the runtime values are resolved per
  workflow at handler-build time:
  * **Model:** request `provider.model` →
    `AI_PLATFORM_WORKFLOW_DEFAULT_MODELS__<workflow>` →
    plugin spec `model` →
    `AI_PLATFORM_DEFAULT_MODEL` →
    fail-fast (no router default).
  * **Routing hint:** request → `AI_PLATFORM_WORKFLOW_DEFAULT_ROUTING_HINTS__<workflow>` →
    plugin spec `routing_hint`.
  * **Provider** (six-step chain):
    1. request `provider.provider`
    2. `AI_PLATFORM_WORKFLOW_DEFAULT_PROVIDERS__<workflow>`
    3. `AI_PLATFORM_PROMPT_DEFAULT_PROVIDERS__<PROMPT_ID>`
       (use underscores in place of dots — e.g.
       `AI_PLATFORM_PROMPT_DEFAULT_PROVIDERS__ANALYTICS_ANOMALY_DETECTION`)
    4. `metadata.default_provider` declared in the prompt YAML
    5. plugin spec `default_provider`
    6. `AI_PLATFORM_DEFAULT_PROVIDER` (platform-wide fallback)

  Every prompt YAML can declare its natural home in
  `metadata.default_provider`; operators override per environment with
  the env keys above without touching code or YAML.

The `task` field labels *this* invocation (`generate_customer_reply`,
`extract_meeting_details`, …). Tasks are used by the prompt registry and
metrics; they do not change the workflow’s lifecycle.

### 1.5 Custom workflow options

There are two supported ways to customize workflow behavior.

#### Option A - runtime `custom_workflow` (no deployment)

Use `workflow="custom_workflow"` when a tenant needs custom logic but you do
not want to ship code yet. The platform passes your payload into the
`future.custom` prompt, which expects tenant-supplied instructions, rules,
tools, and output schema.

Recommended request shape:

```json
{
  "tenant_id": "tenant_acme",
  "workflow": "custom_workflow",
  "task": "partner_contract_summary",
  "payload": {
    "workflow_definition": {
      "name": "partner_contract_summary",
      "version": "2026-05-23",
      "system_prompt": "You are a contract analyst.",
      "rules": [
        "Use only the supplied input.",
        "Return strict JSON only."
      ],
      "output_schema": {
        "type": "object",
        "required": ["summary"],
        "properties": {
          "summary": {"type": "string"}
        }
      }
    },
    "input": {
      "document_text": "..."
    },
    "available_tools": []
  }
}
```

Operational notes:

* The outer request is validated by the public API contract; the inner
  `workflow_definition` object is **your** payload contract today.
* Keep a `version` inside the custom definition and validate it client-side.
* Persist the definition in your own system or pass it through `context_ids`
  if you need reuse. There is no public HTTP CRUD API for custom workflow
  definitions today.

#### Option B - first-class plugin workflow (deployment required)

Use a first-class plugin when the workflow should be reusable, discoverable via
`GET /v1/workflows`, versioned with the platform, covered by tests, and shared
across tenants or teams. This is the path documented in §9.

Rule of thumb:

* Choose `custom_workflow` for fast tenant-specific experimentation.
* Choose a plugin workflow for durable productized automation.

## 2. State machine

```text
QUEUED ─► RUNNING ─┬─► WAITING_TOOL ───────┐
                   ├─► WAITING_APPROVAL ───┤
                   │                       │
                   ▼                       ▼
                SUCCESS              QUEUED (resumed)
                                           │
                   ▲                       ▼
                   └────────────────── RUNNING

QUEUED ─► RUNNING ─► FAILED ─► QUEUED  (retry)
                              ─► DEAD    (retries exhausted)

any non-terminal state ─► CANCELLED
any active state ─► WORKFLOW_TIMEOUT ─► FAILED|DEAD
```

Terminal states: **`SUCCESS`**, **`CANCELLED`**, and **`DEAD`**. All others
may transition.

| State | Meaning | Client action |
|-------|---------|---------------|
| `QUEUED` | Accepted, waiting for a worker. | Poll. |
| `RUNNING` | Worker is processing. | Poll. |
| `WAITING_TOOL` | Workflow paused for an external tool result. | Resolve tool, deliver result. |
| `WAITING_APPROVAL` | Workflow paused for a human approver. | Approve/reject via approval endpoint. |
| `SUCCESS` | Finished; `result` populated. | Consume `result`. |
| `FAILED` | Last attempt failed; may auto-retry. | Wait — engine decides. |
| `CANCELLED` | Caller cancelled before terminal completion. | Stop polling; apply local cancellation policy. |
| `DEAD` | All retries exhausted. | Manual replay or DLQ inspection. |

## 3. Event log

Every transition appends an event to the event store. See
[event-model.md](event-model.md) for the full envelope. Key event names:

`WORKFLOW_CREATED`, `WORKER_STARTED`, `PROVIDER_SELECTED`, `TOOL_REQUESTED`,
`WAITING_APPROVAL`, `WORKFLOW_RESUMED`, `COMPLETED`, `FAILED`,
`RETRY_SCHEDULED`, `WORKFLOW_TIMEOUT`, `WORKFLOW_CANCELLED`, `DEAD_LETTER`.

Replaying these events reconstructs the workflow snapshot — the engine never
trusts a denormalized state column as the source of truth.

## 4. Lifecycle in detail

### 4.1 Submission

`POST /v1/workflows/run` (or any capability endpoint) returns:

```json
{ "job_id": "...", "workflow_id": "...", "status": "QUEUED", "workflow": "..." }
```

The workflow is durable from this instant. The platform owns its progress.

### 4.2 Execution

A worker leases the job, executes the primitive(s), updates state, and emits
events. If the workflow needs an external tool (e.g. inventory lookup), it
emits `TOOL_REQUESTED` and transitions to `WAITING_TOOL`. The callback emits
`WORKFLOW_RESUMED`, moves the workflow back to `QUEUED`, and a worker leases
the next step. See [tool-calls.md](tool-calls.md).

Workers are not embedded in the API process. Run them separately with
`python -m app.workers.main` or the `worker` service in `docker-compose.yml`.
See [worker-operations.md](worker-operations.md).

### 4.3 Approval

For workflows configured with human review (recruiter outreach, high-value
support replies, calendar bookings), the worker emits `WAITING_APPROVAL`. An
approver with the `approver` role must call the approval endpoint (see
[tool-calls.md](tool-calls.md)).

### 4.4 Retry

Transient failures (provider timeout, network blip, JSON parse miss) schedule
a retry: `FAILED → RETRY_SCHEDULED → QUEUED`. Retry policy follows
exponential backoff with jitter; the `attempt_count` in the status response
shows the current attempt.

The implementation lives in
[`app/workflows/retry.py`](../app/workflows/retry.py). Given the policy
`(initial_backoff_seconds B, max_backoff_seconds M, jitter_ratio J)` and
the current `attempt_count = n`, the next attempt is scheduled at:

```text
base_delay = min(B * 2^(n - 1), M)
delay     = max(0, base_delay + U(-J * base_delay, +J * base_delay))
next_at   = now + delay
```

Defaults (overridable per-workflow via `WorkflowPluginSpec.retry_policy`
or globally via env):

| Symbol | Env variable | Default |
|--------|--------------|---------|
| `max_attempts` | `AI_PLATFORM_WORKFLOW_MAX_ATTEMPTS` | `3` |
| `B` | `AI_PLATFORM_WORKFLOW_RETRY_INITIAL_BACKOFF_SECONDS` | `5.0` |
| `M` | `AI_PLATFORM_WORKFLOW_RETRY_MAX_BACKOFF_SECONDS` | `300.0` |
| `J` | per-plugin `retry_policy.jitter_ratio` | `0.1` |

When `attempt_count` reaches `max_attempts`, the workflow transitions to
`DEAD` instead of `QUEUED`. Provider-level retries (network/HTTP 429) are
independent and handled inside the provider adapter; see
[`provider-routing.md`](provider-routing.md).

### 4.5 Timeout

If `now >= timeout_at`, the engine emits `WORKFLOW_TIMEOUT` and either retries
(if attempts remain) or moves to `DEAD`. The default deadline is workflow-
specific; override via the request `timeout_seconds`.

### 4.6 Dead-letter

`DEAD` workflows are inspected by operators. They are not auto-replayed.
See [runbooks.md](runbooks.md) for the replay procedure.

## 5. Result shape

`result` is workflow-specific JSON. The platform always returns a typed
object; the keys are stable per workflow + task.

Example for `support_automation` / `generate_customer_reply`:

```json
{
  "reply": "Your order #8821 shipped on 2026-05-17…",
  "tone": "supportive",
  "next_action": "await_customer",
  "tools_used": ["order_lookup"],
  "provider": "openai",
  "model": "gpt-4o-mini",
  "tokens": { "prompt": 1183, "completion": 220, "total": 1403 }
}
```

Example for `job_automation` / `extract_embed_rerank_generate`:

```json
{
  "match_score": 0.81,
  "highlights": ["7y Python", "FastAPI", "AWS"],
  "draft_email": "Hi Priya, …",
  "provider": "anthropic",
  "model": "claude-sonnet-4-5"
}
```

## 6. Concurrency & idempotency

* The engine uses optimistic concurrency on the event stream. Two parallel
  appends with the same `expected_version` cause one to retry.
* Submission idempotency is opt-in via `Idempotency-Key`; production uses
  the Redis backend so replay state is shared across API replicas (see
  [api.md](api.md#8-idempotency)).
* Tool/approval callbacks are correlated by `workflow_id` plus the
  `pending_action.tool_name` or `pending_action.approval_type` reported by the
  status endpoint.

## 7. Observability

Each workflow’s history can be reconstructed end-to-end from:

* `GET /v1/workflows/{workflow_id}` — current state.
* OpenTelemetry trace keyed by `trace_id`.
* Structured logs filtered by `trace_id` or `workflow_id`.
* Prometheus metrics labeled with `workflow` and `state`.

## 8. Best practices

* Always log `trace_id`, `workflow_id`, `job_id` alongside your business id.
* Treat `result` as immutable. If you need a revised output, submit a new
  workflow.
* Discover allowed workflows via `GET /v1/workflows` rather than hardcoding
  a list on the client; new workflows ship without breaking changes.
* Set realistic `timeout_seconds` — too short causes retries and cost.

## 9. Adding a new first-class workflow (maintainer reference)

A new workflow should ship with prompt, registry entry, tests, and docs; no
schema/API changes are required.

1. **Prompt** — add `app/prompts/<category>/<name>.yaml` with sections
   `system`, `domain`, `rules`, `tools`, `context`, `task`, `output_schema`
   and a unique `prompt_id`.
2. **Plugin spec** — add a `WorkflowPluginSpec` to the matching module under
   [app/workflows/plugins/](../app/workflows/plugins). Example:

   ```python
   WorkflowPluginSpec(
       workflow_name="payment_followup_workflow",
       category=WorkflowCategory.CRM,
       prompt_id="crm.payment_followup",
       version="1.0.0",
       description="Dunning / payment chase communication.",
       routing_hint=RoutingHint.PREMIUM_COMMUNICATION,
       approval_type="finance_send_approval",
       tags=("finance", "dunning"),
   )
   ```

3. **Tests** — add coverage in `tests/unit/workflows/` and (optionally) a
   route-level scenario in `tests/integration/`.

4. **Docs** — update [docs/workflows.md](workflows.md),
  [docs/integration-guide.md](integration-guide.md), and
  [README.md](../README.md) if the workflow is externally available.

The container picks the spec up at next startup; `GET /v1/workflows`
immediately lists the new workflow.
