# Integration Architecture — Connecting Your Application to the AI Operating Platform

> **Audience**: Backend engineers on the existing application team (Node.js / any HTTP client).
> **Goal**: Fully integrate without reading platform source code.

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Authentication & Tenant Isolation](#2-authentication--tenant-isolation)
3. [API Reference Quick Map](#3-api-reference-quick-map)
4. [Triggering AI Workflows](#4-triggering-ai-workflows)
5. [Polling for Results](#5-polling-for-results)
6. [Tool Callbacks](#6-tool-callbacks)
7. [Approval Callbacks](#7-approval-callbacks)
8. [Dead-Letter Management](#8-dead-letter-management)
9. [Context Management](#9-context-management)
10. [Communication Channels](#10-communication-channels)
11. [Webhook Integration Pattern](#11-webhook-integration-pattern)
12. [Queue Integration](#12-queue-integration)
13. [Event Synchronization](#13-event-synchronization)
14. [Retry & Error Handling](#14-retry--error-handling)
15. [Scalability](#15-scalability)
16. [Security](#16-security)
17. [Deployment Topology](#17-deployment-topology)
18. [Migration Strategy](#18-migration-strategy)
19. [Integration Gaps & Risks](#19-integration-gaps--risks)
20. [Node.js SDK Reference Implementation](#20-nodejs-sdk-reference-implementation)

---

## 1. Architecture Overview

### Integration Topology

```
┌──────────────────────────────────────────────────────────────────┐
│                     YOUR EXISTING APPLICATION                    │
│                                                                  │
│  ┌───────────┐  ┌──────────┐  ┌──────────┐  ┌───────────────┐  │
│  │  Node.js  │  │  Auth    │  │  Queue   │  │  Database     │  │
│  │  Backend  │  │  System  │  │  (Bull)  │  │  (Postgres/   │  │
│  │           │  │  (JWT)   │  │          │  │   MongoDB)    │  │
│  └─────┬─────┘  └────┬─────┘  └────┬─────┘  └───────┬───────┘  │
│        │              │             │                │          │
│        ▼              ▼             ▼                ▼          │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │              AI Platform Integration Layer              │    │
│  │  (HTTP Client + Poller + Webhook Receiver + Context Sync)│   │
│  └──────────────────────────┬──────────────────────────────┘    │
└─────────────────────────────┼───────────────────────────────────┘
                              │
                    HTTPS / mTLS
                              │
┌─────────────────────────────▼───────────────────────────────────┐
│                    AI OPERATING PLATFORM                         │
│                                                                  │
│  ┌────────────┐  ┌───────────┐  ┌────────────┐  ┌───────────┐  │
│  │  FastAPI   │  │  Workflow  │  │  Provider  │  │  Event    │  │
│  │  Gateway   │  │  Engine   │  │  Router    │  │  Store    │  │
│  │  :8000     │  │           │  │            │  │  (PG)     │  │
│  └──────┬─────┘  └─────┬─────┘  └──────┬─────┘  └─────┬─────┘  │
│         │              │               │              │         │
│  ┌──────┴──────┐ ┌─────┴────┐  ┌───────┴──────┐      │         │
│  │  Context    │ │  Redis   │  │  OpenAI /    │      │         │
│  │  Resolver   │ │  Queue   │  │  Anthropic / │      │         │
│  │  (PG+Redis) │ │          │  │  Gemini /    │      │         │
│  └─────────────┘ └──────────┘  │  DeepSeek /  │      │         │
│                                │  OpenRouter  │      │         │
│                                └──────────────┘      │         │
└──────────────────────────────────────────────────────────────────┘
```

### Integration Principles

| Principle | Rule |
|---|---|
| **Stateless** | Platform holds no in-memory tenant state; every request self-describes via headers + payload |
| **Async-first** | Every AI operation returns immediately with `job_id` / `workflow_id`; poll or webhook for result |
| **Tenant-isolated** | All data is keyed by `tenant_id`; one tenant cannot see another's workflows |
| **Provider-agnostic** | Your app never calls OpenAI/Anthropic directly; the platform routes, retries, and fails over |
| **Structured output** | Every workflow returns validated JSON, not raw LLM text |

---

## 2. Trust Boundary & Tenant Isolation

This service performs no authentication or authorization of its own. It is a
fully internal microservice that must sit behind a trusted API gateway (or be
called only by other trusted internal services); that gateway is solely
responsible for authenticating callers and authorizing their requests.

### Required HTTP Headers

Every request **must** include these headers, forwarded by your gateway after
it has authenticated the caller:

| Header | Required | Description | Example |
|---|---|---|---|
| `x-tenant-id` | Yes | Tenant identifier, forwarded by your gateway; trusted without validation | `tenant_acme_corp` |
| `x-trace-id` | Recommended | Distributed trace correlation ID; platform auto-generates if missing | `trace-abc123` |
| `x-principal-id` | Recommended | Authenticated user/service ID, forwarded by your gateway; trusted without validation | `user_42` |

### Auth Integration Pattern

Your existing auth gateway authenticates the caller and authorizes the
request, then forwards the identity headers:

```
┌──────────────┐       ┌──────────────┐       ┌──────────────┐
│  Client      │──────▶│  Your Auth   │──────▶│  AI Platform │
│  (Browser /  │       │  Gateway     │       │  :8000       │
│   Mobile)    │       │              │       │              │
└──────────────┘       │  1. Verify   │       │  Trusts:     │
                       │     JWT      │       │  x-tenant-id │
                       │  2. Authorize│       │  x-principal │
                       │     request  │       │    -id       │
                       │  3. Forward  │       │  (no further │
                       │     headers  │       │  validation) │
                       └──────────────┘       └──────────────┘
```

See [authentication.md](authentication.md) for the full header contract and
trust model.

---

## 3. API Reference Quick Map

### Base URL

```
http://<platform-host>:8000/v1
```

### Endpoints

| Method | Path | Purpose | Returns |
|---|---|---|---|
| `POST` | `/v1/generate` | Trigger text generation workflow | `202 QueuedWorkflowResponse` |
| `POST` | `/v1/classify` | Trigger classification workflow | `202 QueuedWorkflowResponse` |
| `POST` | `/v1/extract` | Trigger extraction workflow | `202 QueuedWorkflowResponse` |
| `POST` | `/v1/embed` | Trigger embedding workflow | `202 QueuedWorkflowResponse` |
| `POST` | `/v1/rerank` | Trigger reranking workflow | `202 QueuedWorkflowResponse` |
| `POST` | `/v1/summarize` | Trigger summarization workflow | `202 QueuedWorkflowResponse` |
| `POST` | `/v1/workflows/run` | Trigger any named workflow | `202 QueuedWorkflowResponse` |
| `GET` | `/v1/workflows/{workflow_id}` | Poll workflow status | `200 WorkflowStatusResponse` |
| `GET` | `/v1/jobs/{job_id}` | Poll job status | `200 JobStatusResponse` |
| `POST` | `/v1/workflows/{workflow_id}/tool-results` | Submit tool callback data | `200 WorkflowStatusResponse` |
| `POST` | `/v1/workflows/{workflow_id}/approvals` | Approve/reject a pending workflow | `200 WorkflowStatusResponse` |
| `DELETE` | `/v1/workflows/{workflow_id}` | Cancel a running workflow | `200 WorkflowStatusResponse` |
| `GET` | `/v1/workflows/dead-letter` | List dead-lettered workflows | `200 DeadLetterListResponse` |
| `POST` | `/v1/workflows/{workflow_id}/dead-letter/replay` | Replay a dead-lettered workflow | `200 WorkflowStatusResponse` |
| `GET` | `/v1/workflows` | Discover registered workflows | `200 WorkflowListResponse` |
| `GET` | `/health` | Aggregate health check | `200 / 503 HealthResponse` |
| `GET` | `/health/live` | Liveness probe | `200 HealthResponse` |
| `GET` | `/health/ready` | Readiness probe | `200 / 503 HealthResponse` |
| `GET` | `/metrics` | Prometheus metrics scrape | `200 text/plain` |

---

## 4. Triggering AI Workflows

### Sequence Diagram: Trigger → Poll → Result

```
Your App                      AI Platform                  LLM Provider
   │                              │                            │
   │  POST /v1/generate           │                            │
   │  { tenant_id, workflow,      │                            │
   │    task, payload,            │                            │
   │    context_ids }             │                            │
   │─────────────────────────────▶│                            │
   │                              │  Validate + Resolve Context│
   │                              │  Create Workflow (QUEUED)   │
   │                              │  Enqueue to Redis           │
   │  202 { job_id, workflow_id,  │                            │
   │        status: "QUEUED" }    │                            │
   │◀─────────────────────────────│                            │
   │                              │                            │
   │                              │  Worker picks up job       │
   │                              │  (state → RUNNING)         │
   │                              │───────────────────────────▶│
   │                              │                            │
   │                              │  ◀── LLM response ────────│
   │                              │  Parse + Validate JSON     │
   │                              │  (state → SUCCESS)         │
   │                              │                            │
   │  GET /v1/workflows/{id}      │                            │
   │  ?tenant_id=...              │                            │
   │─────────────────────────────▶│                            │
   │                              │                            │
   │  200 { status: "SUCCESS",    │                            │
   │        result: { ... } }     │                            │
   │◀─────────────────────────────│                            │
```

### Request Body (All Capability Endpoints)

```jsonc
{
  // Required
  "tenant_id": "tenant_acme_corp",
  "workflow": "support_automation",     // registered workflow name
  "task": "generate_customer_reply",    // free-text task identifier

  // Data sources (at least one required for /v1/workflows/run)
  "context_ids": ["ctx_brand_acme", "ctx_case_1234"],  // pre-stored contexts
  "context": {                          // inline context (merged with stored)
    "customer": { "name": "Jane", "tier": "premium" },
    "order": { "id": "ORD-8821", "status": "shipped" }
  },
  "payload": {                          // business payload passed to prompt
    "message": "Where is my order?",
    "channel": "email"
  },

  // Optional: override provider selection
  "provider": {
    "provider": "openrouter",           // openai | gemini | anthropic | deepseek | openrouter | xai
    "model": "deepseek/deepseek-v4-flash:free"
  },

  // Optional: token budget
  "token_budget": {
    "max_input_tokens": 100000,
    "max_output_tokens": 4096,
    "max_total_tokens": 120000,
    "estimated_input_tokens": 2000
  },

  // Optional: execution controls
  "timeout_seconds": 300,              // 1–604800 (7 days)
  "max_attempts": 3                    // 1–10, overrides platform default
}
```

### Response (202 Accepted)

```json
{
  "success": true,
  "job_id": "a9f3c1f7e8c44f4ba642cfb0c2d6764e",
  "workflow_id": "d65cb4dc8e624d209344a41c1f7922dd",
  "trace_id": "trace-abc123",
  "status": "QUEUED",
  "workflow": "support_automation"
}
```

### Available Workflows

| Workflow Name | Category | Routing Hint | Approval | Description |
|---|---|---|---|---|
| `support_automation` | legacy | bulk_processing | — | E-commerce support triage + response |
| `job_automation` | legacy | bulk_processing | — | JD extraction, embed, rerank, generate |
| `recruiter_automation` | legacy | premium_communication | `recruiter_send_approval` | Recruiter outreach drafting |
| `calendar_automation` | legacy | structured_json | — | Meeting extraction from text |
| `crm_workflow` | legacy | structured_json | `crm_change_approval` | CRM record enrichment |
| `document_intelligence` | legacy | long_context | — | Document OCR + extraction |
| `ai_communication_automation` | legacy | premium_communication | `communication_send_approval` | Multi-channel AI communication |

Additional plugin categories: `core_ai`, `tooling`, `documents`, `communication`, `calendar`, `recruitment`, `crm`, `commerce`, `analytics`. Query `GET /v1/workflows` for the live registry.

---

## 5. Polling for Results

### Workflow States

```
QUEUED ──▶ RUNNING ──┬──▶ SUCCESS     (terminal)
                     ├──▶ FAILED      (terminal)
                     ├──▶ DEAD        (terminal, after max retries)
                     ├──▶ CANCELLED   (terminal)
                     ├──▶ WAITING_TOOL ──▶ (resume) ──▶ RUNNING
                     └──▶ WAITING_APPROVAL ──▶ (resume) ──▶ RUNNING
```

Terminal states: `SUCCESS`, `FAILED`, `DEAD`, `CANCELLED`.

### Poll by Workflow ID

```
GET /v1/workflows/{workflow_id}?tenant_id=tenant_acme_corp
```

### Poll by Job ID

```
GET /v1/jobs/{job_id}?tenant_id=tenant_acme_corp
```

### Response Structure

```jsonc
{
  "success": true,
  "workflow_id": "d65cb4dc8e624d209344a41c1f7922dd",
  "job_id": "a9f3c1f7e8c44f4ba642cfb0c2d6764e",
  "trace_id": "trace-abc123",
  "status": "SUCCESS",                  // workflow state
  "workflow": "support_automation",
  "attempt_count": 1,
  "max_attempts": 3,
  "next_attempt_at": null,             // set when retry is scheduled
  "timeout_at": "2026-05-19T12:30:00Z",
  "pending_action": null,              // non-null when WAITING_TOOL or WAITING_APPROVAL
  "result": {                          // non-null on SUCCESS
    "reply": "Your order ORD-8821 shipped on May 17...",
    "confidence": 0.95,
    "intent": "order_status"
  },
  "error": null                        // non-null on FAILED / DEAD
}
```

### Pending Action Shapes

When `status` is `WAITING_TOOL`:

```json
{
  "pending_action": {
    "kind": "tool",
    "tool_name": "order_lookup",
    "tool_payload": { "order_id": "8821" }
  }
}
```

When `status` is `WAITING_APPROVAL`:

```json
{
  "pending_action": {
    "kind": "approval",
    "approval_type": "communication_send_approval",
    "approval_payload": {
      "generated_text": "Dear customer, your order...",
      "channel": "email"
    }
  }
}
```

### Recommended Polling Strategy

```
Initial:     200ms wait
Backoff:     exponential 200ms → 400ms → 800ms → 1600ms → cap at 5s
Timeout:     match request timeout_seconds (default 1800s)
```

---

## 6. Tool Callbacks

### Sequence Diagram: Tool Request Flow

```
Your App                      AI Platform               Your Backend
   │                              │                          │
   │  POST /v1/generate           │                          │
   │─────────────────────────────▶│                          │
   │  202 { workflow_id }         │                          │
   │◀─────────────────────────────│                          │
   │                              │                          │
   │  ... worker runs ...         │                          │
   │  LLM requests tool call      │                          │
   │                              │                          │
   │  GET /v1/workflows/{id}      │                          │
   │─────────────────────────────▶│                          │
   │  200 { status:               │                          │
   │    "WAITING_TOOL",           │                          │
   │    pending_action: {         │                          │
   │      kind: "tool",           │                          │
   │      tool_name:              │                          │
   │        "order_lookup",       │                          │
   │      tool_payload:           │                          │
   │        { order_id: "8821" }  │                          │
   │    }                         │                          │
   │  }                           │                          │
   │◀─────────────────────────────│                          │
   │                              │                          │
   │  Execute tool locally ───────┼─────────────────────────▶│
   │  (query your own DB/API)     │                          │
   │  ◀──────────────────────────┼──── tool result ──────────│
   │                              │                          │
   │  POST /v1/workflows/{id}/    │                          │
   │    tool-results              │                          │
   │  { tenant_id, tool_name,     │                          │
   │    result: { ... } }         │                          │
   │─────────────────────────────▶│                          │
   │  200 { status: "RUNNING" }   │  Worker resumes with     │
   │◀─────────────────────────────│  tool data injected      │
   │                              │  into prompt context     │
```

### Tool Result Request

```
POST /v1/workflows/{workflow_id}/tool-results
```

```json
{
  "tenant_id": "tenant_acme_corp",
  "tool_name": "order_lookup",
  "result": {
    "order_id": "8821",
    "status": "shipped",
    "tracking_url": "https://track.example.com/8821",
    "shipped_at": "2026-05-17T14:30:00Z"
  }
}
```

### Validation Rules

- `tool_name` **must** match the `pending_action.tool_name` — a mismatch returns `409 Conflict`
- Workflow **must** be in `WAITING_TOOL` state — otherwise returns `409 Conflict`
- `tenant_id` **must** match the workflow's tenant — otherwise returns `403 Forbidden`

### Known Tool Names

| Tool Name | Workflow | Purpose |
|---|---|---|
| `order_lookup` | support_automation | Fetch order details from your e-commerce DB |
| `refund_initiate` | support_automation | Trigger refund in your payment system |
| `crm_lookup` | crm_workflow | Fetch CRM record |
| `calendar_create` | calendar_automation | Create calendar event in your system |
| `calendar_availability` | calendar_automation | Check calendar availability |
| `document_ocr` | document_intelligence | OCR a document (return extracted text) |
| `ticket_create` | support_automation | Create support ticket |
| `notification_send` | ai_communication_automation | Send notification via your channels |

---

## 7. Approval Callbacks

### Sequence Diagram

```
Your App                      AI Platform               Approver UI
   │                              │                          │
   │  POST /v1/generate           │                          │
   │  workflow: recruiter_        │                          │
   │    automation                │                          │
   │─────────────────────────────▶│                          │
   │  202 { workflow_id }         │                          │
   │◀─────────────────────────────│                          │
   │                              │                          │
   │  ... LLM generates draft ... │                          │
   │                              │                          │
   │  GET /v1/workflows/{id}      │                          │
   │─────────────────────────────▶│                          │
   │  200 { status:               │                          │
   │    "WAITING_APPROVAL",       │                          │
   │    pending_action: {         │                          │
   │      kind: "approval",      │                          │
   │      approval_type:          │                          │
   │        "recruiter_send_      │                          │
   │          approval",          │                          │
   │      approval_payload: {     │                          │
   │        generated_text: "..." │                          │
   │      }                       │                          │
   │    }                         │                          │
   │  }                           │                          │
   │◀─────────────────────────────│                          │
   │                              │                          │
   │  Show draft to approver ─────┼─────────────────────────▶│
   │  ◀──── approve / reject ────┼──────────────────────────│
   │                              │                          │
   │  POST /v1/workflows/{id}/    │                          │
   │    approvals                 │                          │
   │  { tenant_id,                │                          │
   │    approval_type,            │                          │
   │    decision: "approve",      │                          │
   │    approval_payload: {       │                          │
   │      comment: "LGTM" } }    │                          │
   │─────────────────────────────▶│                          │
   │  200 { status: "RUNNING" }   │                          │
   │◀─────────────────────────────│                          │
```

### Approve

```json
{
  "tenant_id": "tenant_acme_corp",
  "approval_type": "recruiter_send_approval",
  "decision": "approve",
  "approval_payload": { "comment": "Looks good, send it" }
}
```

### Reject

```json
{
  "tenant_id": "tenant_acme_corp",
  "approval_type": "recruiter_send_approval",
  "decision": "reject",
  "reason": "Tone is too informal, please regenerate"
}
```

> `reason` is **required** when `decision` is `"reject"`.

### Known Approval Types

| Approval Type | Workflow | When Triggered |
|---|---|---|
| `communication_send_approval` | ai_communication_automation | Before sending AI-composed message |
| `recruiter_send_approval` | recruiter_automation | Before sending recruiter outreach |
| `crm_change_approval` | crm_workflow | Before writing CRM mutations |

---

## 8. Dead-Letter Management

Workflows that exhaust all retry attempts land in the dead-letter queue with state `DEAD`.

### List Dead-Lettered Workflows

```
GET /v1/workflows/dead-letter?tenant_id=tenant_acme_corp&limit=100
```

### Replay a Dead-Lettered Workflow

```
POST /v1/workflows/{workflow_id}/dead-letter/replay

{
  "tenant_id": "tenant_acme_corp",
  "reason": "provider recovered, retrying"
}
```

This resets the workflow back to `QUEUED` with a fresh attempt counter.

---

## 9. Context Management

### What is a Context?

A context is a versioned JSON document stored in the AI platform's PostgreSQL database, keyed by `(tenant_id, context_id)`. Contexts inject domain data (brand rules, customer profiles, product catalogs) into prompts without passing large payloads on every request.

### Database Schema

```sql
CREATE TABLE contexts (
    context_id   VARCHAR(128) NOT NULL,
    tenant_id    VARCHAR(128) NOT NULL,
    version      INTEGER      NOT NULL DEFAULT 1,
    payload      JSONB        NOT NULL DEFAULT '{}',
    created_at   TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ  NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, context_id)
);
```

### Mapping Your Data to Contexts

| Your Data | Context ID Pattern | Payload Example |
|---|---|---|
| Company brand & tone | `brand_{company_id}` | `{ "tone": "professional", "policy": "use order data only" }` |
| Customer profile | `customer_{customer_id}` | `{ "name": "Jane", "tier": "premium", "language": "en" }` |
| Job description | `job_{job_id}` | `{ "title": "SRE", "requirements": [...], "company": "..." }` |
| Candidate resume | `candidate_{candidate_id}` | `{ "name": "...", "experience": [...] }` |
| Product catalog | `catalog_{category}` | `{ "products": [...] }` |
| CRM record | `crm_{record_id}` | `{ "lead_score": 85, "stage": "qualified" }` |

### Synchronization Strategy

```
┌──────────────┐                    ┌──────────────────────┐
│  Your App    │                    │  AI Platform DB      │
│  Database    │                    │  (contexts table)    │
│              │                    │                      │
│  UPDATE      │   INSERT/UPDATE    │  context_id          │
│  customer ──▶│──────────────────▶ │  tenant_id           │
│  record      │   (your sync      │  version++           │
│              │    worker/hook)    │  payload = { ... }   │
└──────────────┘                    └──────────────────────┘
```

**Option A — Direct SQL write** (recommended for co-located deployments):

```sql
INSERT INTO contexts (context_id, tenant_id, version, payload)
VALUES ('customer_789', 'tenant_acme', 1, '{"name":"Jane","tier":"premium"}')
ON CONFLICT (tenant_id, context_id)
DO UPDATE SET
    version = contexts.version + 1,
    payload = EXCLUDED.payload,
    updated_at = now();
```

**Option B — Context sync API** (if the platform adds a context write endpoint):

Not yet implemented. Use direct SQL or a shared-database pattern.

### Context Resolution Flow

When your request includes `context_ids`:

1. Platform checks **Redis cache** first (TTL: configurable, default 300s)
2. Cache miss → **PostgreSQL lookup** → cache backfill
3. All referenced `context_ids` **must** exist — missing IDs return `404`
4. Resolved contexts are merged and injected into the LLM prompt

### Inline Context

For ephemeral data that shouldn't be stored, use the `context` field directly:

```json
{
  "context_ids": ["brand_acme"],
  "context": {
    "conversation_history": [
      { "role": "customer", "text": "Where is my order?" }
    ]
  }
}
```

Both stored contexts and inline context are merged before prompt rendering.

---

## 10. Communication Channels

### Email Automation

```json
{
  "tenant_id": "tenant_acme_corp",
  "workflow": "ai_communication_automation",
  "task": "compose_email_reply",
  "payload": {
    "channel": "email",
    "from": "support@acme.com",
    "to": "customer@example.com",
    "subject": "Re: Order #8821",
    "thread_context": "Customer asked about delivery status"
  },
  "context_ids": ["brand_acme", "customer_789"]
}
```

The workflow generates an email draft → enters `WAITING_APPROVAL` (approval type: `communication_send_approval`) → your app polls, presents the draft to an operator, then approves or rejects → on approval, your app uses the `result.generated_text` to send via your own SMTP/email service.

### Telegram / WhatsApp / SMS

Same workflow, different `channel` in payload:

```json
{
  "payload": {
    "channel": "telegram",       // or "whatsapp", "sms"
    "recipient_id": "tg_12345",
    "message_context": "Customer inquiry about refund"
  }
}
```

The platform composes the message; **your app handles actual delivery** through your existing Telegram Bot API / WhatsApp Business API / SMS gateway.

### Calendar Events

```json
{
  "tenant_id": "tenant_acme_corp",
  "workflow": "calendar_automation",
  "task": "extract_meeting",
  "payload": {
    "raw_text": "Let's meet Thursday at 3pm EST on Zoom"
  }
}
```

Result (on SUCCESS):

```json
{
  "result": {
    "date": "2026-05-22",
    "time": "15:00",
    "timezone": "America/New_York",
    "meeting_link": "https://zoom.us/...",
    "attendees": ["..."]
  }
}
```

Your app then creates the event in Google Calendar / Outlook via your existing integration.

### OCR / Document Intelligence

```json
{
  "tenant_id": "tenant_acme_corp",
  "workflow": "document_intelligence",
  "task": "extract_invoice",
  "payload": {
    "document_uri": "https://storage.example.com/invoices/inv-001.pdf",
    "document_type": "invoice"
  }
}
```

If the workflow needs OCR, it enters `WAITING_TOOL` with `tool_name: "document_ocr"`. Your app performs OCR (using your own OCR service or Tesseract) and returns the extracted text via tool callback.

---

## 11. Webhook Integration Pattern

The platform currently uses a **poll-based** model. To convert this into push-based webhooks for your existing system, implement a **Webhook Bridge** in your integration layer:

### Webhook Bridge Architecture

```
┌──────────────────────────────────────────────────────────┐
│  YOUR APPLICATION                                        │
│                                                          │
│  ┌────────────────────────────────────────────────────┐  │
│  │  Webhook Bridge (runs in your Node.js backend)     │  │
│  │                                                    │  │
│  │  1. Submit workflow → get workflow_id               │  │
│  │  2. Poll at interval (exponential backoff)         │  │
│  │  3. On state change → emit internal event:         │  │
│  │     - WAITING_TOOL  → route to tool handler        │  │
│  │     - WAITING_APPROVAL → route to approval UI      │  │
│  │     - SUCCESS → route to result handler            │  │
│  │     - FAILED/DEAD → route to error handler         │  │
│  │  4. Auto-respond to tool requests if handler exists│  │
│  └────────────────────────────────────────────────────┘  │
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │ Tool Handlers│  │ Approval     │  │ Result       │   │
│  │ (order_lookup│  │ Queue        │  │ Processor    │   │
│  │  crm_lookup) │  │              │  │              │   │
│  └──────────────┘  └──────────────┘  └──────────────┘   │
└──────────────────────────────────────────────────────────┘
```

See the [Node.js SDK](#20-nodejs-sdk-reference-implementation) for a production-ready implementation.

---

## 12. Queue Integration

### Your Queue → AI Platform

If your existing app uses BullMQ / RabbitMQ / SQS, add a consumer that forwards AI tasks to the platform:

```
┌────────────┐       ┌──────────────┐       ┌──────────────┐
│ Your Queue │──────▶│  AI Bridge   │──────▶│  AI Platform │
│ (BullMQ)   │       │  Consumer    │       │  POST /v1/   │
│            │       │              │       │   generate   │
│ job: {     │       │ 1. Dequeue   │       │              │
│   type:    │       │ 2. Map to    │       │              │
│   "ai_gen" │       │    request   │       │              │
│   data:{}  │       │ 3. POST      │       │              │
│ }          │       │ 4. Store     │       │              │
│            │       │    workflow_id│       │              │
│            │       │ 5. Poll/ack  │       │              │
└────────────┘       └──────────────┘       └──────────────┘
```

### AI Platform → Your Queue

For result delivery back into your queue system, the Webhook Bridge polls and enqueues results:

```typescript
// In your BullMQ worker
const result = await aiClient.pollUntilTerminal(workflowId, tenantId);
await resultQueue.add('ai_result', {
  workflow_id: workflowId,
  status: result.status,
  result: result.result,
  error: result.error,
});
```

---

## 13. Event Synchronization

### Platform Event Types

The platform persists every state transition in its event store (PostgreSQL, hash-partitioned):

| Event | When |
|---|---|
| `REQUEST_RECEIVED` | API receives the request |
| `REQUEST_VALIDATED` | Schema validation passes |
| `CONTEXT_RESOLVED` | Context IDs resolved from cache/DB |
| `JOB_QUEUED` | Workflow enqueued to Redis |
| `WORKFLOW_CREATED` | Projection row created |
| `WORKER_STARTED` | Worker picks up the job |
| `PROVIDER_SELECTED` | Provider router makes a decision |
| `TOOL_REQUESTED` | LLM emits a tool call → `WAITING_TOOL` |
| `WAITING_APPROVAL` | Workflow requires human approval |
| `WORKFLOW_RESUMED` | Tool result or approval received |
| `COMPLETED` | Workflow finishes successfully |
| `FAILED` | Non-terminal failure (may retry) |
| `RETRY_SCHEDULED` | Retry scheduled with backoff |
| `WORKFLOW_TIMEOUT` | Workflow exceeded timeout |
| `WORKFLOW_CANCELLED` | Explicitly cancelled |
| `DEAD_LETTER` | All retries exhausted |
| `DEAD_LETTER_REPLAYED` | Dead-lettered workflow replayed |

### Consuming Events (Advanced)

For real-time event synchronization, query the `event_store` table directly (read-only access):

```sql
SELECT event_id, event_name, tenant_id, workflow_id, trace_id,
       payload, occurred_at
FROM event_store
WHERE tenant_id = 'tenant_acme_corp'
  AND occurred_at > :last_sync_at
ORDER BY occurred_at ASC
LIMIT 1000;
```

Or build a CDC (Change Data Capture) pipeline from PostgreSQL logical replication to your event bus.

---

## 14. Retry & Error Handling

### Platform Retry Behaviour

| Scenario | Retried? | Max Attempts |
|---|---|---|
| Provider timeout | Yes | 3 (configurable) |
| Provider rate limit (429) | Yes | 3 |
| Malformed LLM JSON | Yes | 3 |
| Network failure | Yes | 3 |
| Schema validation failure | **No** | — |
| Invalid business input | **No** | — |
| Context not found | **No** | — |

### Retry Backoff Formula

```
base_delay = min(B × 2^(n-1), M)
delay = max(0, base_delay + U(-J × base_delay, +J × base_delay))
next_attempt_at = now + delay
```

Where:
- `B` = initial backoff (default 5s)
- `M` = max backoff (default 300s)
- `J` = jitter ratio (default 0.1)
- `n` = attempt number

### Error Response Format

```json
{
  "success": true,
  "workflow_id": "...",
  "status": "FAILED",
  "error": {
    "error_type": "ProviderRateLimitError",
    "message": "No provider available for generate (hint=bulk_processing); tried: openrouter",
    "retryable": true
  }
}
```

### Client-Side Retry Decision Tree

```
Is status terminal?
├── SUCCESS → process result
├── FAILED  → check error.retryable
│   ├── true  → platform already retried; consider DLQ replay later
│   └── false → fix input and resubmit
├── DEAD    → inspect via dead-letter API; fix and replay
├── CANCELLED → resubmit if appropriate
└── Not terminal → keep polling
```

### Idempotency

The platform supports idempotency via the `Idempotency-Key` header. Duplicate requests with the same key within the TTL window (default 24h) return the original response without re-executing.

```
Idempotency-Key: order-reply-ORD-8821-attempt-1
```

---

## 15. Scalability

### Capacity Design (500–1000 Concurrent Jobs)

| Component | Scaling Strategy | Recommendation |
|---|---|---|
| **API** | Horizontal, stateless | 2–4 replicas behind load balancer |
| **Worker** | Horizontal, lease-based | 3–6 replicas; each polls Redis independently |
| **PostgreSQL** | Vertical + read replicas | Event store is hash-partitioned (16 partitions); ai_generations range-partitioned monthly |
| **Redis** | Sentinel or Cluster | Single node handles ~10k ops/s; cluster for >50k |
| **LLM Providers** | Auto-failover via routing chains | Platform rotates through provider chains on failure |

### Burst Traffic

- **Rate limiting**: Configurable per-tenant (default 600 req/min, burst 120)
- **Queue buffering**: Redis absorbs bursts; workers drain at their own pace
- **Per-tenant inflight cap**: Prevents one tenant from starving others (default 100 concurrent)
- **Provider circuit breakers**: Trip after 5 failures; half-open after 30s recovery

### Provider Failure Handling

```
Preferred provider fails
    ↓
Circuit breaker trips
    ↓
Router tries next in routing chain:
  BULK_PROCESSING: deepseek → openrouter
  PREMIUM_COMMUNICATION: anthropic → openrouter
  STRUCTURED_JSON: openai → openrouter
  LONG_CONTEXT: gemini → openai → openrouter
    ↓
All providers fail → RetryableExecutionError → backoff → retry
    ↓
Max attempts exhausted → DEAD (dead-letter queue)
```

---

## 16. Security

### Checklist

| Concern | Implementation |
|---|---|
| **Transport** | TLS between your app and the platform; mTLS for production |
| **Tenant isolation** | Every query/mutation is scoped by `tenant_id` from request context; enforced at middleware and DB layers |
| **API authentication** | Enforced entirely by your gateway, which verifies the caller and forwards identity as `x-principal-id` / `x-tenant-id`. This service trusts those headers without validation |
| **Rate limiting** | Per-tenant token-bucket (600/min default) |
| **Idempotency** | Prevents duplicate workflow creation |
| **Secrets** | Provider API keys stored as `SecretStr`, never logged |
| **PII** | Platform never logs resumes, salaries, emails, or prompt secrets |
| **Webhook validation** | When implementing webhooks, validate HMAC signature on incoming callbacks |

### Tenant ID Conventions

| Pattern | Example |
|---|---|
| Single-tenant SaaS | `tenant_default` |
| Multi-tenant by company | `tenant_{company_slug}` |
| Multi-tenant by environment | `tenant_{company}_{env}` |

---

## 17. Deployment Topology

### Development (Local Docker)

```
Your App (localhost:3000)
    │
    └──▶ AI Platform (localhost:8000)
              │
              ├── PostgreSQL (localhost:5432)
              └── Redis (localhost:6379)
```

### Production

```
                    ┌──────────────────┐
                    │  Load Balancer   │
                    │  (nginx/ALB)     │
                    └────────┬─────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
        ┌─────▼─────┐ ┌─────▼─────┐ ┌─────▼─────┐
        │  API (1)  │ │  API (2)  │ │  API (3)  │
        └───────────┘ └───────────┘ └───────────┘
              │              │              │
              └──────────────┼──────────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
        ┌─────▼─────┐ ┌─────▼─────┐ ┌─────▼─────┐
        │ Worker(1) │ │ Worker(2) │ │ Worker(3) │
        └───────────┘ └───────────┘ └───────────┘
              │              │              │
              └──────────────┼──────────────┘
                             │
                  ┌──────────┴──────────┐
                  │                     │
            ┌─────▼─────┐        ┌─────▼─────┐
            │ PostgreSQL │        │   Redis   │
            │ (primary   │        │ (Sentinel │
            │  + replica)│        │  or       │
            │            │        │  Cluster) │
            └────────────┘        └───────────┘
```

### Environment Variables for Your Integration

```bash
# In your Node.js .env
AI_PLATFORM_BASE_URL=http://ai-platform-api:8000
AI_PLATFORM_TENANT_ID=tenant_acme_corp
AI_PLATFORM_POLL_INTERVAL_MS=1000
AI_PLATFORM_POLL_TIMEOUT_MS=180000
AI_PLATFORM_MAX_CONCURRENT_POLLS=50
```

---

## 18. Migration Strategy

### Phase 1: Shadow Mode (Week 1–2)

```
Customer request
    │
    ├──▶ Existing AI logic (primary, serves response)
    │
    └──▶ AI Platform (shadow, logs only, compare results)
```

- Deploy platform alongside existing AI
- Forward same inputs to both
- Compare outputs in a dashboard
- Zero customer impact

### Phase 2: Canary (Week 3–4)

```
Customer request
    │
    ├──▶ Feature flag: 10% → AI Platform (primary)
    │
    └──▶ 90% → Existing AI (primary)
```

- Route 10% of traffic to the platform
- Monitor latency, accuracy, cost
- Gradually increase percentage

### Phase 3: Primary (Week 5–6)

```
Customer request → AI Platform (100%)
    │
    └──▶ Existing AI (fallback, removed after stabilization)
```

### Migration Mapping

| Existing AI Feature | Platform Workflow | Notes |
|---|---|---|
| Direct OpenAI calls for support replies | `support_automation` | Replace `openai.chat.completions.create()` with POST `/v1/generate` |
| Inline email generation | `ai_communication_automation` | Move to async; add approval step |
| Resume parsing | `document_intelligence` | Add OCR tool callback handler |
| Calendar extraction (regex-based) | `calendar_automation` | LLM-based extraction replaces regex |
| CRM lead scoring (custom model) | `crm_workflow` | Feed scoring criteria via context |
| Telegram bot AI replies | `ai_communication_automation` | Set `channel: "telegram"` in payload |

### Code Changes Required in Your App

1. **Add HTTP client** for AI platform (see SDK below)
2. **Add poller** or webhook bridge for async results
3. **Add tool handlers** for `order_lookup`, `crm_lookup`, etc.
4. **Add approval UI** for workflows requiring human review
5. **Add context sync** worker to keep contexts table updated
6. **Remove direct LLM SDK calls** (openai, anthropic packages)
7. **Update queue consumers** to use platform instead of direct inference

---

## 19. Integration Gaps & Risks

### Current Gaps

| Gap | Impact | Mitigation |
|---|---|---|
| **No push-based webhooks** | Requires polling; adds latency | Implement Webhook Bridge (see §11); platform may add webhooks in future |
| **No context write API** | Must write to contexts table via SQL | Use shared database or add a thin context management endpoint |
| **No batch API** | 1 request = 1 workflow | Use queue integration to parallelize; platform handles concurrency internally |
| **No streaming** | Results delivered as complete JSON | Poll-based is already async; streaming rarely needed for structured outputs |

### Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| **Provider rate limiting** on free-tier models | High | Use paid tier models or set `provider_rate_limit_min_backoff_seconds` higher |
| **Context staleness** | Medium | Set cache TTL appropriately; version field enables optimistic concurrency |
| **Workflow timeout** for complex multi-step flows | Medium | Set `timeout_seconds` per request; monitor `WORKFLOW_TIMEOUT` events |
| **Single Redis as queue** | Low (for <1k concurrent) | Add Redis Sentinel; platform is stateless and reconnects automatically |
| **Schema drift** between your app and platform | Medium | Pin workflow versions; test with `GET /v1/workflows` discovery |

### Coupling Issues

| Issue | Recommendation |
|---|---|
| Your app depends on specific `result` JSON shape | Define result contracts per workflow; validate on your side |
| Tool names are implicit contracts | Document tool names in a shared registry; version them |
| Approval types are implicit contracts | Same — maintain a shared enum |
| Context ID naming conventions | Enforce naming convention (e.g. `{entity}_{id}`) via validation |

### Duplicate AI Responsibilities

| Responsibility | Keep In | Remove From |
|---|---|---|
| LLM inference | AI Platform | Your app (remove openai/anthropic SDKs) |
| Prompt management | AI Platform (prompt registry) | Your app (remove hardcoded prompts) |
| Provider failover | AI Platform (routing chains) | Your app |
| Retry logic for AI calls | AI Platform (workflow engine) | Your app |
| Business data (users, orders) | Your app | AI Platform (never stores business entities) |
| Authentication | Your app | AI Platform (receives headers) |
| Message delivery (email/TG/WA) | Your app | AI Platform (generates content only) |

---

## 20. Node.js SDK Reference Implementation

### Installation

```bash
npm install undici  # or use native fetch in Node 18+
```

### AI Platform Client

```typescript
// ai-platform-client.ts

interface AIWorkflowRequest {
  tenant_id: string;
  workflow: string;
  task: string;
  payload?: Record<string, unknown>;
  context_ids?: string[];
  context?: Record<string, unknown>;
  provider?: { provider: string; model?: string };
  token_budget?: {
    max_input_tokens?: number;
    max_output_tokens?: number;
    max_total_tokens?: number;
    estimated_input_tokens?: number;
  };
  timeout_seconds?: number;
  max_attempts?: number;
}

interface QueuedResponse {
  success: boolean;
  job_id: string;
  workflow_id: string;
  trace_id: string;
  status: string;
  workflow: string;
}

interface PendingAction {
  kind: 'tool' | 'approval';
  tool_name?: string;
  tool_payload?: Record<string, unknown>;
  approval_type?: string;
  approval_payload?: Record<string, unknown>;
}

interface WorkflowStatus {
  success: boolean;
  workflow_id: string;
  job_id: string | null;
  trace_id: string;
  status: 'QUEUED' | 'RUNNING' | 'WAITING_TOOL' | 'WAITING_APPROVAL'
        | 'SUCCESS' | 'FAILED' | 'CANCELLED' | 'DEAD';
  workflow: string;
  attempt_count: number;
  max_attempts: number;
  next_attempt_at: string | null;
  timeout_at: string | null;
  pending_action: PendingAction | null;
  result: Record<string, unknown> | null;
  error: { error_type: string; message: string; retryable: boolean } | null;
}

const TERMINAL_STATES = new Set(['SUCCESS', 'FAILED', 'CANCELLED', 'DEAD']);

export class AIPlatformClient {
  private baseUrl: string;
  private defaultTenantId: string;
  private defaultHeaders: Record<string, string>;

  constructor(opts: {
    baseUrl: string;
    tenantId: string;
    principalId?: string;
  }) {
    this.baseUrl = opts.baseUrl.replace(/\/$/, '');
    this.defaultTenantId = opts.tenantId;
    this.defaultHeaders = {
      'content-type': 'application/json',
      'x-tenant-id': opts.tenantId,
    };
    if (opts.principalId) {
      this.defaultHeaders['x-principal-id'] = opts.principalId;
    }
  }

  // ── Trigger ──────────────────────────────────────────────

  async generate(req: AIWorkflowRequest): Promise<QueuedResponse> {
    return this.post('/v1/generate', req);
  }

  async classify(req: AIWorkflowRequest): Promise<QueuedResponse> {
    return this.post('/v1/classify', req);
  }

  async extract(req: AIWorkflowRequest): Promise<QueuedResponse> {
    return this.post('/v1/extract', req);
  }

  async runWorkflow(req: AIWorkflowRequest): Promise<QueuedResponse> {
    return this.post('/v1/workflows/run', req);
  }

  // ── Poll ─────────────────────────────────────────────────

  async getWorkflow(workflowId: string, tenantId?: string): Promise<WorkflowStatus> {
    const tid = tenantId ?? this.defaultTenantId;
    return this.get(`/v1/workflows/${workflowId}?tenant_id=${tid}`);
  }

  async getJob(jobId: string, tenantId?: string): Promise<WorkflowStatus> {
    const tid = tenantId ?? this.defaultTenantId;
    return this.get(`/v1/jobs/${jobId}?tenant_id=${tid}`);
  }

  async pollUntilTerminal(
    workflowId: string,
    opts?: { tenantId?: string; timeoutMs?: number; intervalMs?: number },
  ): Promise<WorkflowStatus> {
    const tenantId = opts?.tenantId ?? this.defaultTenantId;
    const timeout = opts?.timeoutMs ?? 180_000;
    const baseInterval = opts?.intervalMs ?? 500;
    const maxInterval = 5_000;
    const deadline = Date.now() + timeout;
    let interval = baseInterval;

    while (Date.now() < deadline) {
      const status = await this.getWorkflow(workflowId, tenantId);
      if (TERMINAL_STATES.has(status.status)) return status;
      if (status.status === 'WAITING_TOOL' || status.status === 'WAITING_APPROVAL') {
        return status; // Caller must handle tool/approval
      }
      await sleep(interval);
      interval = Math.min(interval * 2, maxInterval);
    }
    throw new Error(`Workflow ${workflowId} did not reach terminal state within ${timeout}ms`);
  }

  // ── Callbacks ────────────────────────────────────────────

  async submitToolResult(
    workflowId: string,
    toolName: string,
    result: Record<string, unknown>,
    tenantId?: string,
  ): Promise<WorkflowStatus> {
    return this.post(`/v1/workflows/${workflowId}/tool-results`, {
      tenant_id: tenantId ?? this.defaultTenantId,
      tool_name: toolName,
      result,
    });
  }

  async approve(
    workflowId: string,
    approvalType: string,
    payload?: Record<string, unknown>,
    tenantId?: string,
  ): Promise<WorkflowStatus> {
    return this.post(`/v1/workflows/${workflowId}/approvals`, {
      tenant_id: tenantId ?? this.defaultTenantId,
      approval_type: approvalType,
      decision: 'approve',
      approval_payload: payload ?? {},
    });
  }

  async reject(
    workflowId: string,
    approvalType: string,
    reason: string,
    tenantId?: string,
  ): Promise<WorkflowStatus> {
    return this.post(`/v1/workflows/${workflowId}/approvals`, {
      tenant_id: tenantId ?? this.defaultTenantId,
      approval_type: approvalType,
      decision: 'reject',
      reason,
    });
  }

  // ── Cancel ───────────────────────────────────────────────

  async cancel(
    workflowId: string,
    reason: string,
    tenantId?: string,
  ): Promise<WorkflowStatus> {
    const tid = tenantId ?? this.defaultTenantId;
    return this.delete(
      `/v1/workflows/${workflowId}?tenant_id=${tid}&reason=${encodeURIComponent(reason)}`,
    );
  }

  // ── Dead Letter ──────────────────────────────────────────

  async listDeadLetters(tenantId?: string, limit = 100) {
    const tid = tenantId ?? this.defaultTenantId;
    return this.get(`/v1/workflows/dead-letter?tenant_id=${tid}&limit=${limit}`);
  }

  async replayDeadLetter(workflowId: string, reason: string, tenantId?: string) {
    return this.post(`/v1/workflows/${workflowId}/dead-letter/replay`, {
      tenant_id: tenantId ?? this.defaultTenantId,
      reason,
    });
  }

  // ── Health ───────────────────────────────────────────────

  async health(): Promise<{ status: string }> {
    return this.get('/health');
  }

  // ── Discovery ────────────────────────────────────────────

  async listWorkflows() {
    return this.get('/v1/workflows');
  }

  // ── HTTP internals ───────────────────────────────────────

  private async post(path: string, body: unknown): Promise<any> {
    const res = await fetch(`${this.baseUrl}${path}`, {
      method: 'POST',
      headers: this.defaultHeaders,
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      const text = await res.text();
      throw new Error(`AI Platform ${res.status}: ${text}`);
    }
    return res.json();
  }

  private async get(path: string): Promise<any> {
    const res = await fetch(`${this.baseUrl}${path}`, {
      method: 'GET',
      headers: this.defaultHeaders,
    });
    if (!res.ok) {
      const text = await res.text();
      throw new Error(`AI Platform ${res.status}: ${text}`);
    }
    return res.json();
  }

  private async delete(path: string): Promise<any> {
    const res = await fetch(`${this.baseUrl}${path}`, {
      method: 'DELETE',
      headers: this.defaultHeaders,
    });
    if (!res.ok) {
      const text = await res.text();
      throw new Error(`AI Platform ${res.status}: ${text}`);
    }
    return res.json();
  }
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
```

### Usage: Support Automation with Tool Callback

```typescript
import { AIPlatformClient } from './ai-platform-client';
import { db } from './database'; // your existing database

const ai = new AIPlatformClient({
  baseUrl: process.env.AI_PLATFORM_BASE_URL!,
  tenantId: 'tenant_acme_corp',
  principalId: 'service_backend',
  roles: ['operator'],
});

// Tool handlers — map tool names to your business logic
const toolHandlers: Record<string, (payload: any) => Promise<any>> = {
  async order_lookup({ order_id }) {
    const order = await db.orders.findOne({ id: order_id });
    if (!order) return { error: 'order_not_found' };
    return {
      order_id: order.id,
      status: order.status,
      tracking_url: order.trackingUrl,
      shipped_at: order.shippedAt,
      items: order.items.map((i: any) => ({ name: i.name, qty: i.qty })),
    };
  },
  async crm_lookup({ record_id }) {
    const record = await db.crm.findOne({ id: record_id });
    return record ?? { error: 'record_not_found' };
  },
};

async function handleCustomerMessage(
  tenantId: string,
  message: string,
  customerId: string,
) {
  // 1. Trigger workflow
  const queued = await ai.generate({
    tenant_id: tenantId,
    workflow: 'support_automation',
    task: 'generate_customer_reply',
    payload: { message, channel: 'email' },
    context_ids: [`brand_${tenantId}`, `customer_${customerId}`],
  });

  console.log(`Workflow ${queued.workflow_id} queued (job: ${queued.job_id})`);

  // 2. Poll with automatic tool resolution
  let status = await ai.pollUntilTerminal(queued.workflow_id, { tenantId });

  while (status.status === 'WAITING_TOOL') {
    const { tool_name, tool_payload } = status.pending_action!;
    const handler = toolHandlers[tool_name!];
    if (!handler) throw new Error(`No handler for tool: ${tool_name}`);

    const toolResult = await handler(tool_payload);
    status = await ai.submitToolResult(
      queued.workflow_id, tool_name!, toolResult, tenantId,
    );

    // Resume polling after tool submission
    if (!['SUCCESS', 'FAILED', 'DEAD', 'CANCELLED'].includes(status.status)) {
      status = await ai.pollUntilTerminal(queued.workflow_id, { tenantId });
    }
  }

  // 3. Process result
  if (status.status === 'SUCCESS') {
    return status.result; // { reply: "...", intent: "...", confidence: ... }
  } else {
    console.error('Workflow failed:', status.error);
    throw new Error(status.error?.message ?? 'AI workflow failed');
  }
}
```

### Usage: Approval Flow

```typescript
async function handleRecruiterDraft(
  tenantId: string,
  candidateId: string,
  jobId: string,
) {
  const queued = await ai.generate({
    tenant_id: tenantId,
    workflow: 'recruiter_automation',
    task: 'draft_outreach',
    payload: { candidate_id: candidateId, job_id: jobId },
    context_ids: [`candidate_${candidateId}`, `job_${jobId}`],
  });

  const status = await ai.pollUntilTerminal(queued.workflow_id, { tenantId });

  if (status.status === 'WAITING_APPROVAL') {
    // Present to recruiter in your UI
    const draft = status.pending_action!.approval_payload;
    return {
      workflow_id: queued.workflow_id,
      approval_type: status.pending_action!.approval_type,
      draft, // { generated_text: "Dear candidate, ..." }
    };
  }
}

// Called when recruiter clicks "Approve" in your UI
async function approveRecruiterDraft(workflowId: string, tenantId: string) {
  const status = await ai.approve(
    workflowId, 'recruiter_send_approval', {}, tenantId,
  );
  // Resume polling for final result
  const final = await ai.pollUntilTerminal(workflowId, { tenantId });
  return final.result;
}
```

### Usage: BullMQ Integration

```typescript
import { Queue, Worker } from 'bullmq';

const aiTaskQueue = new Queue('ai-tasks', { connection: redisConfig });
const aiResultQueue = new Queue('ai-results', { connection: redisConfig });

// Producer: your business logic enqueues AI tasks
await aiTaskQueue.add('support_reply', {
  tenant_id: 'tenant_acme',
  workflow: 'support_automation',
  task: 'generate_customer_reply',
  payload: { message: 'Where is my order?', channel: 'email' },
  context_ids: ['brand_acme', 'customer_789'],
});

// Consumer: bridge between your queue and AI platform
const aiWorker = new Worker('ai-tasks', async (job) => {
  const queued = await ai.generate(job.data);
  let status = await ai.pollUntilTerminal(queued.workflow_id, {
    tenantId: job.data.tenant_id,
    timeoutMs: 300_000,
  });

  // Handle tool callbacks inline
  while (status.status === 'WAITING_TOOL') {
    const handler = toolHandlers[status.pending_action!.tool_name!];
    const result = await handler(status.pending_action!.tool_payload);
    status = await ai.submitToolResult(
      queued.workflow_id,
      status.pending_action!.tool_name!,
      result,
      job.data.tenant_id,
    );
    if (!['SUCCESS', 'FAILED', 'DEAD', 'CANCELLED'].includes(status.status)) {
      status = await ai.pollUntilTerminal(queued.workflow_id, {
        tenantId: job.data.tenant_id,
      });
    }
  }

  // Enqueue result for downstream processing
  await aiResultQueue.add('ai_result', {
    original_job_id: job.id,
    workflow_id: queued.workflow_id,
    status: status.status,
    result: status.result,
    error: status.error,
  });
}, { connection: redisConfig, concurrency: 20 });
```

### Context Sync Worker

```typescript
import { db } from './database';
import { Pool } from 'pg';

// Connect directly to the AI platform's PostgreSQL
const aiDb = new Pool({
  connectionString: process.env.AI_PLATFORM_DATABASE_URL,
});

async function syncCustomerContext(tenantId: string, customerId: string) {
  const customer = await db.customers.findOne({ id: customerId });
  if (!customer) return;

  await aiDb.query(
    `INSERT INTO contexts (context_id, tenant_id, version, payload)
     VALUES ($1, $2, 1, $3)
     ON CONFLICT (tenant_id, context_id)
     DO UPDATE SET
       version = contexts.version + 1,
       payload = $3,
       updated_at = now()`,
    [
      `customer_${customerId}`,
      tenantId,
      JSON.stringify({
        name: customer.name,
        email: customer.email,
        tier: customer.subscriptionTier,
        language: customer.preferredLanguage,
        previous_tickets: customer.ticketCount,
      }),
    ],
  );
}

// Hook into your existing change events
db.customers.on('change', async (event) => {
  await syncCustomerContext(event.tenantId, event.customerId);
});
```
