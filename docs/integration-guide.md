# Integration Guide

> **New here?** Read [business-flows.md](business-flows.md) first — it
> explains the platform in business terms with diagrams for every
> domain (support, commerce, recruitment, calendar, documents, CRM,
> communication, analytics) and gives you the end-to-end integration
> checklist. This guide is the per-channel **request/response cookbook**
> you use after that.

This guide contains eight end-to-end integrations. Each example shows:

1. The incoming trigger (email, message, webhook, …).
2. The exact platform API call.
3. The workflow selected by the platform.
4. The provider chain the router will consider.
5. The events emitted in order.
6. Any tool/approval round-trips.
7. The final response shape.
8. Error scenarios and how to handle them.

Read [getting-started.md](getting-started.md) and [api.md](api.md) first.

For environment setup, use the minimum profile in
[configuration.md](configuration.md#do-we-need-all-environment-variables)
instead of trying to set every `AI_PLATFORM_*` variable on day one.

> **Discover available workflows first.** The platform's full workflow
> catalog is exposed at `GET /v1/workflows` (see
> [api.md §5.5](api.md#55-workflow-discovery) and
> [workflows.md §1](workflows.md#1-workflow-plugin-registry)). New
> workflows ship without breaking changes, so integrations should fetch
> this list at startup rather than hardcoding workflow names.

> Common preamble (omitted from each example for brevity): every request
> carries `Content-Type: application/json`, `x-tenant-id`, and
> `x-principal-id` — forwarded by your API gateway, which is responsible for
> authenticating the caller. Use `Idempotency-Key` on any producer that may
> retry a POST. Replace `https://ai.example.com` with your platform URL.

## Advanced integration surfaces

The platform now exposes three integration patterns beyond submit/poll:

| Pattern | Endpoint | Use when |
|---------|----------|----------|
| SSE status | `GET /v1/realtime/workflows/{workflow_id}/events` | You have an active browser/admin view and want bounded live updates. |
| WebSocket status | `WS /v1/realtime/workflows/{workflow_id}/ws` | You already maintain a socket session for workflow progress. |
| Multi-agent orchestration | `POST /v1/agents/orchestrations` | You need several specialist workflows, such as classify + retrieve + draft, queued as one persisted unit. |

Memory, RAG, semantic response cache, reranking, and context compression are
platform features. Integrators opt in to memory/RAG by sending `memory`, `rag`,
or `context_assembly` hints in workflow payloads. Semantic cache and context
compression are controlled by platform configuration and require no client-side
cache key management.

## Documentation-only integration path

If you want to complete an integration using documentation only, this is the
minimum reading order:

1. [getting-started.md](getting-started.md) - required headers, first submit/poll cycle.
2. [api.md](api.md) - public request and response contract.
3. [workflows.md](workflows.md) - workflow lifecycle, retries, and discovery.
4. [tool-calls.md](tool-calls.md) - how to resume `WAITING_TOOL` and `WAITING_APPROVAL` workflows.
5. [authentication.md](authentication.md) - identity headers and the trust model.
6. [sdk-examples.md](sdk-examples.md) - ready-to-adapt Python and TypeScript clients.
7. [configuration.md](configuration.md#do-we-need-all-environment-variables) - minimum vs optional environment configuration profiles.

That set is sufficient to build a submit/poll/tool/approval integration
without reading the application code.

## Example 1 — Email automation (auto-reply)

**Trigger.** A customer email lands in your shared inbox. Your email
service classifies "intent unknown, looks like a status check" and asks the
platform to draft a reply.

**API call:**

```http
POST /v1/workflows/run
{
  "tenant_id": "tenant_acme",
  "workflow": "support_automation",
  "task": "generate_customer_reply",
  "payload": {
    "channel": "email",
    "subject": "Where is my order?",
    "body": "Hi, I ordered last week and have not received a tracking link.",
    "from": "customer@example.com",
    "tool_request": {
      "tool_name": "order_lookup",
      "tool_payload": { "customer_id": "customer_8821" }
    }
  },
  "context": {
    "brand_voice": "Use a concise, helpful support tone.",
    "policy": "Use verified order lookup data before making status claims.",
    "customer": { "id": "customer_8821" }
  }
}
```

**Pipeline.** `classify → extract → tool_request(order_lookup) → generate`.

**Router.** `STRUCTURED_JSON` → `OpenAI(gpt-4o-mini) → OpenRouter`.

**Event order.**

1. `REQUEST_RECEIVED`
2. `CONTEXT_RESOLVED`
3. `WORKFLOW_CREATED`
4. `JOB_QUEUED`
5. `WORKER_STARTED`
6. `PROVIDER_SELECTED` (classify)
7. `TOOL_REQUESTED` (`order_lookup`)
8. (Caller POSTs tool result; engine: `WORKFLOW_RESUMED`)
9. `JOB_QUEUED`
10. `WORKER_STARTED`
11. `PROVIDER_SELECTED` (generate)
12. `COMPLETED`

**Tool callback you must implement:**

```http
POST /v1/workflows/{workflow_id}/tool-results
{ "tenant_id": "tenant_acme",
  "tool_name": "order_lookup",
  "result": { "order_id": "8821", "shipped_at": "2026-05-17T09:00:00Z",
              "carrier": "BlueDart", "tracking_url": "https://example.com/8821" } }
```

**Final response (poll until terminal):**

```json
{ "status": "SUCCESS",
  "result": {
    "reply": "Hi! Your order #8821 shipped on May 17 via BlueDart…",
    "tone": "supportive",
    "tools_used": ["order_lookup"]
  } }
```

**Error scenarios.**

| Failure | Handling |
|---------|----------|
| `order_lookup` cannot find the order | Return a structured tool result your workflow can handle, or keep the workflow waiting and ask the user for clarification. |
| Tool not delivered in time | `WORKFLOW_TIMEOUT`; engine retries (1 of `max_attempts`). |
| Customer email is abusive | Pre-classify upstream; do not submit to platform. |

## Example 2 — Telegram bot

**Trigger.** Telegram webhook hits your bot for `/help refund`.

**API call:**

```http
POST /v1/generate
{
  "tenant_id": "tenant_acme",
  "workflow": "support_automation",
  "task": "telegram_reply",
  "context_ids": ["brand_voice_default", "policy_refunds_v1",
                  "telegram_user_99812"],
  "payload": {
    "channel": "telegram",
    "command": "/help",
    "message": "refund",
    "thread_id": "tg_chat_99812"
  },
  "token_budget": { "max_output_tokens": 512 },
  "timeout_seconds": 30
}
```

**Pipeline.** `classify → generate`.

**Router.** `STRUCTURED_JSON` → `OpenAI → OpenRouter`.

**Polling cadence.** Telegram expects fast replies; poll every 250 ms up
to 5 s, then fall back to a "still working…" message.

**Final response → reply to Telegram:**

```json
{ "status": "SUCCESS",
  "result": { "reply": "Refunds take 3–5 business days…",
              "buttons": ["Track refund", "Talk to human"] } }
```

**Error scenarios.**

| Failure | Handling |
|---------|----------|
| Workflow exceeds 30 s | Send "we’ll follow up shortly" and complete out of band. |
| Provider quota exceeded | Platform fails over via OpenRouter; you do nothing. |
| Unknown command | Upstream filter; do not submit. |

## Example 3 — WhatsApp

**Trigger.** WhatsApp Business API delivers a customer message.

**API call:**

```http
POST /v1/workflows/run
{
  "tenant_id": "tenant_acme",
  "workflow": "support_automation",
  "task": "whatsapp_reply",
  "context_ids": ["brand_voice_premium", "customer_8821",
                  "policy_returns_v3"],
  "payload": {
    "channel": "whatsapp",
    "from": "+919900112233",
    "message": "Pls share my last invoice",
    "language": "en-IN",
    "tool_request": {
      "tool_name": "invoice_lookup",
      "tool_payload": { "customer_id": "customer_8821" }
    }
  },
  "timeout_seconds": 60
}
```

**Pipeline.** `classify → extract → tool_request(invoice_lookup) → generate`.

**Router.** `STRUCTURED_JSON` → `OpenAI → OpenRouter`.

**Tool callback:**

```json
{ "tenant_id": "tenant_acme", "tool_name": "invoice_lookup",
  "result": { "invoice_url": "https://files.example.com/inv-99812.pdf",
              "amount_inr": 4499.00 } }
```

**Final response:**

```json
{ "status": "SUCCESS",
  "result": { "reply": "Here's your invoice for ₹4,499. Anything else?",
              "attachments": ["https://files.example.com/inv-99812.pdf"] } }
```

**Error scenarios.**

| Failure | Handling |
|---------|----------|
| PDF storage down | Tool returns error; workflow sends "I'll send the invoice shortly." |
| Long message (> 256 KiB) | Reject upstream; never grow payload. |
| Mixed languages | Set `payload.language`; the router still picks an English-capable model. |

## Example 4 — Job automation

**Trigger.** Recruiter clicks "Match candidate to JD" in your ATS.

**API call:**

```http
POST /v1/workflows/run
{
  "tenant_id": "tenant_acme",
  "workflow": "job_automation",
  "task": "extract_embed_rerank_generate",
  "context_ids": ["candidate_456", "candidate_456:resume",
                  "job_description_123"],
  "payload": {
    "priority": "standard",
    "source": "ats_ui",
    "recruiter_id": "user_42",
    "requires_approval": true
  },
  "token_budget": {
    "max_input_tokens": 80000,
    "max_output_tokens": 2048,
    "max_total_tokens": 100000
  },
  "timeout_seconds": 1800,
  "max_attempts": 3
}
```

**Pipeline.** `extract → embed → rerank → generate`.

**Router.** Per primitive:

* extract → DeepSeek (BULK_PROCESSING) → OpenRouter

## Example 8 — AI communication automation

**Trigger.** A CRM webhook marks a renewal account as stalled and asks the
platform to draft a follow-up email that must be reviewed before send.

**API call:**

```http
POST /v1/workflows/run
{
  "tenant_id": "tenant_acme",
  "workflow": "ai_communication_automation",
  "task": "draft_lead_follow_up",
  "payload": {
    "channel": "email",
    "objective": "renewal_reengagement",
    "audience": "existing_customer",
    "message": "Draft a renewal follow-up for the account that paused after pricing review.",
    "requires_approval": true,
    "tool_request": {
      "tool_name": "crm_account_lookup",
      "tool_payload": { "account_id": "acct_441", "lead_id": "lead_778" }
    }
  },
  "context": {
    "brand_voice": "Consultative, concise, commercially aware.",
    "campaign": { "name": "renewal_save_q2" }
  }
}
```

**Pipeline.** `tool_request(crm_account_lookup) → approval → generate`.

**Router.** `PREMIUM_COMMUNICATION` → `Anthropic → OpenRouter` unless tenant or
request overrides apply.

**Event order.**

1. `REQUEST_RECEIVED`
2. `CONTEXT_RESOLVED`
3. `WORKFLOW_CREATED`
4. `JOB_QUEUED`
5. `WORKER_STARTED`
6. `TOOL_REQUESTED` (`crm_account_lookup`)
7. (Caller POSTs tool result; engine: `WORKFLOW_RESUMED`)
8. `JOB_QUEUED`
9. `WORKER_STARTED`
10. `WAITING_APPROVAL`
11. (Caller POSTs approval; engine: `WORKFLOW_RESUMED`)
12. `JOB_QUEUED`
13. `WORKER_STARTED`
14. `PROVIDER_SELECTED` (generate)
15. `COMPLETED`

**Tool callback:**

```http
POST /v1/workflows/{workflow_id}/tool-results
{
  "tenant_id": "tenant_acme",
  "tool_name": "crm_account_lookup",
  "result": {
    "account_id": "acct_441",
    "owner": "ae_17",
    "stage": "renewal_30d",
    "last_contact_summary": "Customer paused after pricing review."
  }
}
```

**Approval callback:**

```http
POST /v1/workflows/{workflow_id}/approvals
{
  "tenant_id": "tenant_acme",
  "approval_type": "communication_send_approval",
  "decision": "approve",
  "approval_payload": { "comment": "Approved to send." }
}
```

**Final response:**

```json
{
  "status": "SUCCESS",
  "result": {
    "communication_type": "renewal_reengagement",
    "tone": "consultative",
    "message": "Hi, I wanted to follow up on your renewal review and answer any open questions...",
    "follow_up_required": true,
    "missing_facts": []
  }
}
```
* embed → OpenAI(text-embedding-3-small) → Gemini(text-embedding-004)
* rerank → DeepSeek → OpenRouter
* generate → Anthropic (PREMIUM_COMMUNICATION) → OpenRouter

**Approval.** This workflow is typically configured to require approval
before sending. The engine emits `WAITING_APPROVAL` with a `preview` of
the draft email; the recruiter approves via
`POST /v1/workflows/{id}/approvals`. See [tool-calls.md](tool-calls.md).

**Final response:**

```json
{ "status": "SUCCESS",
  "result": {
    "match_score": 0.81,
    "highlights": ["7y Python", "FastAPI", "AWS"],
    "draft_email": { "subject": "Senior Platform Engineer at Acme",
                     "body": "Hi Priya, …" } } }
```

**Error scenarios.**

| Failure | Handling |
|---------|----------|
| Resume context too large | Split into `candidate_456:resume:summary` + `:full`. |
| Approver rejects | `FAILED`; ATS notifies recruiter; resubmit if appropriate. |
| Embed provider degraded | Router falls over to Gemini; no caller action. |

## Example 5 — OCR / Document intelligence

**Trigger.** Document service ingests a scanned PDF contract.

**Step 1 — Submit the document pointer:**

```http
POST /v1/workflows/run
{
  "tenant_id": "tenant_acme",
  "workflow": "document_intelligence",
  "task": "ocr_extract_summarize",
  "context_ids": ["contract_template_2026q2_v1"],
  "payload": {
    "document_uri": "https://files.example.com/contracts/2026q2-acme.pdf",
    "document_id": "doc_2026q2_acme",
    "expected_clauses": ["term", "termination", "fees", "sla"]
  },
  "timeout_seconds": 3600,
  "max_attempts": 2
}
```

**Pipeline.** `ocr → extract → summarize`.

**Router.** OCR is performed by a local component, then:

* extract → Gemini (LONG_CONTEXT) → OpenAI → OpenRouter
* summarize → Gemini (LONG_CONTEXT) → OpenAI → OpenRouter

**Tool callback (`document_ocr`):**

```json
{ "tenant_id": "tenant_acme", "tool_name": "document_ocr",
  "result": { "text": "Full OCR text...", "page_count": 18 } }
```

**Final response:**

```json
{ "status": "SUCCESS",
  "result": {
    "clauses": {
      "term": "Two years renewable…",
      "termination": "Either party with 60 days' notice…",
      "fees": "₹X per month plus usage…",
      "sla": "99.9% monthly availability…"
    },
    "summary": "Two-year SaaS contract with a 60-day exit and 99.9% SLA.",
    "page_count": 18,
    "language": "en"
  } }
```

**Error scenarios.**

| Failure | Handling |
|---------|----------|
| OCR cannot read pages | `FAILED` with `error.code = "ocr_failed"`; queue a manual review. |
| Document exceeds context window | Router selects Gemini long-context; if still too large, split upstream. |
| Document URI expires | Pre-sign with > workflow timeout. |

## Example 6 — Calendar scheduling

**Trigger.** Customer email reads "let's meet next Tuesday at 3 PM IST".

**API call:**

```http
POST /v1/workflows/run
{
  "tenant_id": "tenant_acme",
  "workflow": "calendar_automation",
  "task": "extract_then_schedule",
  "context_ids": ["persona_account_manager_ana",
                  "calendar_account_ana@example.com"],
  "payload": {
    "channel": "email",
    "thread": [
      { "from": "customer@example.com",
        "body": "Let's meet next Tuesday at 3 PM IST about renewals." }
    ],
    "default_duration_minutes": 30,
    "tool_request": {
      "tool_name": "calendar_freebusy",
      "tool_payload": {
        "attendee": "ana@example.com",
        "requested_text": "next Tuesday at 3 PM IST",
        "duration_minutes": 30
      }
    }
  },
  "timeout_seconds": 600
}
```

**Pipeline.** `extract → validate → tool_request(freebusy) → generate`.

**Router.** extract → OpenAI; generate → Anthropic; fallback OpenRouter.

**Tool callback (`calendar_freebusy`):**

```json
{ "tenant_id": "tenant_acme", "tool_name": "calendar_freebusy",
  "result": {
    "requested_slot": { "start": "2026-05-26T09:30:00Z",
                        "end": "2026-05-26T10:00:00Z" },
    "is_free": true,
    "alternatives": [] } }
```

**Final response:**

```json
{ "status": "SUCCESS",
  "result": {
    "reply": "Tuesday 26 May at 3:00 PM IST works for Ana…",
    "calendar_event_request": {
      "title": "Renewals discussion — Acme × Customer",
      "start": "2026-05-26T09:30:00Z",
      "end":   "2026-05-26T10:00:00Z",
      "attendees": ["ana@example.com", "customer@example.com"]
    } } }
```

The CRM/calendar service consumes `calendar_event_request` and creates the
event. The platform never books calendars itself.

**Error scenarios.**

| Failure | Handling |
|---------|----------|
| Ambiguous date ("next week") | Workflow emits `TOOL_REQUESTED("ask_user")`; your bot prompts for clarification. |
| Slot not free | Tool returns `is_free:false` + `alternatives`; workflow proposes them. |
| Timezone unknown | Reject upstream — workflow requires a timezone in payload. |

## Example 7 — CRM follow-ups

**Trigger.** A "no-reply in 7 days" CRM rule fires for an account.

**API call:**

```http
POST /v1/workflows/run
{
  "tenant_id": "tenant_acme",
  "workflow": "crm_workflow",
  "task": "renewal_followup",
  "context_ids": [
    "brand_voice_premium",
    "account_acme_corp",
    "account_acme_corp:notes",
    "persona_account_manager_ana"
  ],
  "payload": {
    "stage": "renewal_30d",
    "channel": "email",
    "last_touch_at": "2026-05-10T10:00:00Z",
    "requires_approval": true
  },
  "timeout_seconds": 900,
  "max_attempts": 3
}
```

**Pipeline.** `classify → extract → generate`.

**Router.** classify → OpenAI; generate → Anthropic; fallback OpenRouter.

**Approval.** Outbound emails over a configured value threshold require
approval (configured per tenant). The workflow emits `WAITING_APPROVAL`
when needed.

**Final response:**

```json
{ "status": "SUCCESS",
  "result": {
    "email": {
      "subject": "Renewal options for Acme Corp",
      "body": "Hi Sam, here's a quick comparison…"
    },
    "next_action": "send_via_crm",
    "tone": "consultative"
  } }
```

**Error scenarios.**

| Failure | Handling |
|---------|----------|
| Account context missing | `context_resolution_error`; publish context, retry. |
| Approver SLA missed | Workflow times out; CRM either auto-sends a safe template or escalates. |
| Tenant cost ceiling reached | Router fails over to a cheaper provider automatically. |

## Example 8 — Tenant-defined custom workflow

**Trigger.** Your product team needs a tenant-specific workflow that is not in
the built-in catalog, but you do not want to deploy code for it yet.

**API call:**

```http
POST /v1/workflows/run
{
  "tenant_id": "tenant_acme",
  "workflow": "custom_workflow",
  "task": "partner_contract_summary",
  "payload": {
    "workflow_definition": {
      "name": "partner_contract_summary",
      "version": "2026-05-23",
      "system_prompt": "You are a contract operations analyst. Summarise the document and highlight commercial risks.",
      "rules": [
        "Use only facts present in the supplied input.",
        "If a requested field is missing, set missing=true and explain why.",
        "Return strict JSON only."
      ],
      "output_schema": {
        "type": "object",
        "required": ["summary", "risks", "missing"],
        "properties": {
          "summary": {"type": "string"},
          "risks": {
            "type": "array",
            "items": {"type": "string"}
          },
          "missing": {"type": "boolean"}
        }
      }
    },
    "input": {
      "document_text": "MSA effective 2026-01-01. 24-month term. Liability cap equal to 3 months of fees.",
      "counterparty": "Acme Distribution"
    },
    "available_tools": []
  },
  "provider": {
    "provider": "openai",
    "model": "gpt-4o-mini"
  },
  "timeout_seconds": 900,
  "max_attempts": 2
}
```

**Pipeline.** `generate`.

**Router.** `AUTO` unless you override provider/model in the request.

**Final response:**

```json
{
  "status": "SUCCESS",
  "result": {
    "summary": "24-month MSA with a liability cap of 3 months of fees.",
    "risks": ["Liability cap may be low for the buyer."],
    "missing": false,
    "executed_instructions": true
  }
}
```

**When to use this.**

| Need | Use `custom_workflow`? |
|------|------------------------|
| Tenant-specific logic without deployment | yes |
| Rapid experimentation | yes |
| Stable reusable workflow for many tenants | no - promote it to a first-class plugin |
| Strong server-side payload validation for the custom definition itself | no - validate it in your app before submit |

**Important limitations.**

* The public contract today is **runtime-supplied payload**. There is no public
  CRUD API yet for persisting workflow definitions over HTTP.
* The platform validates the outer command request, but the inner
  `workflow_definition` shape is your contract. Version it in your app.
* For long-lived or discoverable behavior, add a first-class plugin instead of
  keeping business-critical logic inside ad hoc request payloads.

**Error scenarios.**

| Failure | Handling |
|---------|----------|
| Custom instructions conflict with platform safety rules | Workflow returns a policy conflict explanation. |
| Your app sends an invalid inner schema | Validate `workflow_definition` client-side before submit. |
| The behavior becomes reusable across tenants | Promote it to a first-class workflow plugin. |

## Cross-cutting integration practices

* **Persist `trace_id`, `workflow_id`, `job_id`** alongside your business
  ids. They are your only handles into the platform’s observability stack.
* **Never retry POST commands on your side after HTTP 202** — the platform
  already owns retries. Re-submitting creates duplicate workflows unless
  you use `Idempotency-Key`.
* **Treat polling as a long-lived task.** Implement a single watcher per
  workflow with backoff; do not spawn per-poll connections.
* **Test the failure paths**: stop your tool service, expire approvals,
  send oversize payloads, drop `x-tenant-id` — verify your client behaves.
