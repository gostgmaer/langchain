# Tool Calls and Human Approval

Many workflows cannot finish on language alone. Support replies need order
lookups; calendar replies need free/busy queries; recruiter replies often
need an approver to sign off. The platform represents both with the same
pattern: the workflow pauses in a waiting state, exposes the pending action
through the status endpoint, and resumes when you call back.

## 1. Lifecycle overview

```text
RUNNING ─► WAITING_TOOL ─► (caller delivers tool result) ─► QUEUED ─► RUNNING ─► SUCCESS
RUNNING ─► WAITING_APPROVAL ─► (approver decides) ─► QUEUED ─► RUNNING ─► SUCCESS
                                                  └─► FAILED  (rejected)
```

Poll `GET /v1/workflows/{workflow_id}`. When the workflow is paused, the
response contains `pending_action`.

Tool example:

```json
{
  "status": "WAITING_TOOL",
  "pending_action": {
    "kind": "tool",
    "tool_name": "order_lookup",
    "tool_payload": { "order_id": "8821" }
  }
}
```

Approval example:

```json
{
  "status": "WAITING_APPROVAL",
  "pending_action": {
    "kind": "approval",
    "approval_type": "manager_sign_off",
    "approval_payload": {
      "preview": { "subject": "Senior Platform Engineer at Acme" }
    }
  }
}
```

## 2. Tool requests (`WAITING_TOOL`)

When `pending_action.kind = "tool"`, you must:

1. Execute the tool using your own data sources.
2. POST the result back to the workflow.
3. Correlate the callback by `workflow_id` plus `pending_action.tool_name`.

### 2.1 Delivering a tool result

```http
POST /v1/workflows/{workflow_id}/tool-results HTTP/1.1
Content-Type: application/json
x-tenant-id: tenant_acme
x-principal-id: svc_order_service

{
  "tenant_id": "tenant_acme",
  "tool_name": "order_lookup",
  "result": {
    "order_id": "8821",
    "shipped_at": "2026-05-17T09:00:00Z",
    "carrier": "BlueDart",
    "tracking_url": "https://example.com/track/8821"
  }
}
```

Rules:

* The workflow must currently be `WAITING_TOOL`.
* `tool_name` must match `pending_action.tool_name` exactly.
* Success returns `WorkflowStatusResponse`, usually with `status: QUEUED`.
  The worker leases the workflow again and continues with the tool result in
  its resume payload.
* A mismatch returns HTTP 409 `workflow_state_conflict`.

## 3. Approvals (`WAITING_APPROVAL`)

When `pending_action.kind = "approval"`, the approver decides the workflow.

### 3.1 Approving or rejecting

```http
POST /v1/workflows/{workflow_id}/approvals HTTP/1.1
x-tenant-id: tenant_acme
x-principal-id: user_42

{
  "tenant_id": "tenant_acme",
  "approval_type": "manager_sign_off",
  "decision": "approve",
  "approval_payload": { "comment": "Looks good. Ship it." }
}
```

```json
{
  "tenant_id": "tenant_acme",
  "approval_type": "manager_sign_off",
  "decision": "reject",
  "reason": "Rewrite — too informal."
}
```

Rules:

* The workflow must currently be `WAITING_APPROVAL`.
* `approval_type` must match `pending_action.approval_type` exactly.
* Approve usually returns `status: QUEUED`; reject returns `status: FAILED`.
* A mismatch returns HTTP 409 `workflow_state_conflict`.

## 4. Failure semantics

| Caller does | Engine reaction |
|-------------|-----------------|
| Never delivers a tool result | `WORKFLOW_TIMEOUT` at `timeout_at`; retry or dead-letter. |
| Delivers garbage JSON | HTTP 422; workflow stays in `WAITING_TOOL`. |
| Delivers the wrong `tool_name` | HTTP 409 `workflow_state_conflict`; no state change. |
| Delivers the wrong `approval_type` | HTTP 409 `workflow_state_conflict`; no state change. |
| Rejects an approval | Workflow transitions to `FAILED`. |

## 5. Pattern: building a tool integration

1. Poll workflow status or consume your own watcher’s events.
2. On `WAITING_TOOL`, read `pending_action.tool_name` and
   `pending_action.tool_payload`.
3. Map `tool_name` to your handler (`order_lookup`, `calendar_freebusy`,
   `crm_account_lookup`, …).
4. Run your handler with strict timeouts.
5. POST the result back. Retry the HTTP call on 5xx; do not re-run the tool
   after a 2xx response.
6. Persist `workflow_id + tool_name` alongside your internal handler id.

## 6. Pattern: building an approval UI

1. Poll workflow status for the approver’s tenant.
2. On `WAITING_APPROVAL`, render `pending_action.approval_payload`.
3. On click, POST the decision with `approval_type` and either
   `approval_payload` or `reason`.
4. Always show `trace_id` and `workflow_id` to the approver for audit.

## 7. Security

* Tool/approval endpoints trust the same forwarded `x-tenant-id` /
  `x-principal-id` context as command endpoints; this service performs no
  authentication or authorization of its own. See
  [authentication.md](authentication.md).
* Callback safety comes from the opaque `workflow_id` plus strict matching of
  `tool_name` / `approval_type` against `pending_action`.
* Approval comments and reasons are stored verbatim. Do not include secrets.
* Approval decisions are recorded in `audit_logs` and `security_events`.

## 8. Tool name registry

The set of tool names a workflow can emit is declared on its plugin spec
(`WorkflowPluginSpec.tool_names`). Integrators **must** implement every
listed tool for any workflow they use. The authoritative list is
`GET /v1/workflows`; the table below is the built-in catalogue at the time
of writing.

| Workflow | Emitted `tool_name` values |
|----------|----------------------------|
| `calendar_workflow` | `calendar_create`, `calendar_update` |
| `meeting_scheduling_workflow` | `calendar_availability`, `calendar_create`, `invite_send` |
| `reminder_workflow` | `reminder_create` |
| `telegram_workflow` | `telegram_send` |
| `whatsapp_workflow` | `whatsapp_send` |
| `slack_workflow` | `slack_send` |
| `discord_workflow` | `discord_send` |
| `sms_workflow` | `sms_send` |
| `auto_followup_workflow` | `schedule_message` |
| `order_status_workflow` | `order_lookup` |
| `refund_workflow` | `order_lookup`, `refund_initiate` |
| `complaint_resolution_workflow` | `order_lookup`, `compensation_offer` |
| `customer_support_workflow` | `crm_lookup`, `ticket_create` |
| `tool_orchestration_workflow` | `tool_execute`, `tool_validate` |
| `notification_workflow` | `notification_send` |
| `agent_workflow` | `tool_execute`, `tool_search`, `tool_write` |
| `support_automation`, `ai_communication_automation`, others not listed above | tools are workflow-runtime decisions; the platform emits `pending_action.tool_name` exactly as the plugin requests it — implement defensively against the live `GET /v1/workflows` spec. |

## 9. Approval type registry

When a workflow enters `WAITING_APPROVAL`, `pending_action.approval_type`
is the value declared on the plugin spec (`WorkflowPluginSpec.approval_type`).
Approver UIs should switch on this value to render the correct review
surface.

| Workflow | `approval_type` |
|----------|-----------------|
| `email_workflow`, `email_reply_workflow` | `email_send_approval` |
| `refund_workflow` | `refund_approval` |
| `contract_review_workflow` | `contract_review_approval` |
| `agent_workflow` | `agent_action_approval` |
| `ai_communication_automation` | `communication_send_approval` |
| `recruiter_automation`, `recruiter_reply_workflow` | `recruiter_send_approval` |
| `crm_workflow`, `crm_workflows` | `crm_change_approval` |
| `tool_orchestration_workflow` | `tool_execution_approval` |
| `approval_workflow` | `manual_approval` |

Workflows not listed here do not gate on approvals by default. Operators
can attach approval gates per tenant via the workflow policy store.

## 10. Timeouts

* The tool/approval gate inherits the workflow's `timeout_seconds`. If no
  callback arrives before `timeout_at`, the engine emits
  `WORKFLOW_TIMEOUT` and either retries (attempts remaining) or moves the
  workflow to `DEAD`.
* There is no per-tool timeout — your tool service is responsible for its
  own latency budget. Keep tool work strictly under the workflow timeout
  with margin for jitter and queue lag.
