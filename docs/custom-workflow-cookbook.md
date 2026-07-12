# Custom Workflow Cookbook

This guide shows how to use `custom_workflow` safely and consistently when you
need tenant-specific behavior without shipping a new plugin.

Read [api.md](api.md), [workflows.md](workflows.md), and
[integration-guide.md](integration-guide.md) first.

## 1. When to use `custom_workflow`

Use `custom_workflow` when all of these are true:

* The behavior is tenant-specific or still experimental.
* You want to submit instructions at runtime in the request payload.
* You can validate the inner `workflow_definition` in your own application.
* You do not need the platform to expose a dedicated public schema for that
  custom behavior.

Do not use `custom_workflow` when:

* The workflow should be shared across many tenants.
* The workflow should be discoverable as a stable product feature.
* You need server-side validation of the custom definition itself.
* You want dedicated tool contracts, approvals, or policy around that workflow.

In those cases, add a first-class plugin workflow instead. See
[workflows.md](workflows.md#9-adding-a-new-first-class-workflow-maintainer-reference).

If you need the platform to persist and version custom definitions for you,
see the proposed design in
[custom-workflow-definition-api-design.md](custom-workflow-definition-api-design.md).

## 2. Recommended payload contract

The platform validates the outer workflow request. The inner
`payload.workflow_definition` object is your client-side contract.

Recommended shape:

```json
{
  "tenant_id": "tenant_acme",
  "workflow": "custom_workflow",
  "task": "your_task_name",
  "payload": {
    "workflow_definition": {
      "name": "your_task_name",
      "version": "2026-05-23",
      "system_prompt": "High-level role for the model.",
      "rules": [
        "Rule 1",
        "Rule 2"
      ],
      "output_schema": {
        "type": "object",
        "required": ["result"],
        "properties": {
          "result": {}
        }
      }
    },
    "input": {},
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

Recommended client-side rules:

* Always include `workflow_definition.name`.
* Always include `workflow_definition.version` and bump it on breaking changes.
* Always include `workflow_definition.output_schema`.
* Keep `rules` explicit and short.
* Validate the inner schema before submit.
* Keep custom definitions in your own database or config store.

## 3. Integration flow

1. Build your `workflow_definition` in your app.
2. Validate it client-side.
3. Submit `POST /v1/workflows/run` with `workflow="custom_workflow"`.
4. Poll `GET /v1/workflows/{workflow_id}` until terminal.
5. Parse `result` against the same schema version you submitted.
6. Promote to a first-class plugin when the behavior becomes durable.

## 4. Example 1 - HR candidate screening brief

Use case: summarize a resume against a role and return a structured hiring
brief.

```json
{
  "tenant_id": "tenant_acme_hr",
  "workflow": "custom_workflow",
  "task": "candidate_screening_brief",
  "payload": {
    "workflow_definition": {
      "name": "candidate_screening_brief",
      "version": "2026-05-23",
      "system_prompt": "You are a senior recruiting operations analyst.",
      "rules": [
        "Use only facts present in the supplied resume and role summary.",
        "Do not invent missing skills or experience.",
        "Return strict JSON only."
      ],
      "output_schema": {
        "type": "object",
        "required": ["summary", "fit_score", "strengths", "risks"],
        "properties": {
          "summary": {"type": "string"},
          "fit_score": {"type": "number"},
          "strengths": {"type": "array", "items": {"type": "string"}},
          "risks": {"type": "array", "items": {"type": "string"}}
        }
      }
    },
    "input": {
      "candidate_resume": "7 years Python, FastAPI, Redis, PostgreSQL, Kubernetes.",
      "role_summary": "Staff AI infrastructure engineer with strong distributed systems experience."
    },
    "available_tools": []
  },
  "provider": {"provider": "openai", "model": "gpt-4o-mini"}
}
```

## 5. Example 2 - CRM renewal risk summary

Use case: produce an account-manager-ready renewal brief from account notes and
usage signals.

```json
{
  "tenant_id": "tenant_acme_sales",
  "workflow": "custom_workflow",
  "task": "renewal_risk_summary",
  "payload": {
    "workflow_definition": {
      "name": "renewal_risk_summary",
      "version": "2026-05-23",
      "system_prompt": "You are a revenue operations analyst.",
      "rules": [
        "Prioritize renewal risk, expansion signal, and next best action.",
        "Use only the supplied CRM notes and metrics.",
        "Return strict JSON only."
      ],
      "output_schema": {
        "type": "object",
        "required": ["health", "renewal_risk", "expansion_signal", "next_action"],
        "properties": {
          "health": {"type": "string"},
          "renewal_risk": {"type": "string"},
          "expansion_signal": {"type": "string"},
          "next_action": {"type": "string"}
        }
      }
    },
    "input": {
      "account_name": "RetailEdge",
      "usage_metrics": {"weekly_active_users": 52, "license_utilization": 0.61},
      "crm_notes": "Champion left the company. Finance asked for a price comparison. Product adoption is stable."
    },
    "available_tools": []
  },
  "provider": {"provider": "openai", "model": "gpt-4o-mini"}
}
```

## 6. Example 3 - Support refund triage

Use case: standardize a refund recommendation from a support message before a
human agent replies.

```json
{
  "tenant_id": "tenant_acme_support",
  "workflow": "custom_workflow",
  "task": "refund_triage_recommendation",
  "payload": {
    "workflow_definition": {
      "name": "refund_triage_recommendation",
      "version": "2026-05-23",
      "system_prompt": "You are an e-commerce support policy analyst.",
      "rules": [
        "Assess refund eligibility only from the supplied policy and case facts.",
        "If facts are missing, say what is missing.",
        "Return strict JSON only."
      ],
      "output_schema": {
        "type": "object",
        "required": ["recommendation", "reason", "missing_data"],
        "properties": {
          "recommendation": {"type": "string"},
          "reason": {"type": "string"},
          "missing_data": {"type": "array", "items": {"type": "string"}}
        }
      }
    },
    "input": {
      "message": "The product arrived damaged and I want a refund.",
      "order_age_days": 4,
      "refund_policy": "Damaged items within 14 days are eligible for full refund."
    },
    "available_tools": []
  },
  "provider": {"provider": "openai", "model": "gpt-4o-mini"}
}
```

## 7. Example 4 - Document exception extraction

Use case: extract only exception-worthy invoice issues for an operations queue.

```json
{
  "tenant_id": "tenant_acme_docs",
  "workflow": "custom_workflow",
  "task": "invoice_exception_extract",
  "payload": {
    "workflow_definition": {
      "name": "invoice_exception_extract",
      "version": "2026-05-23",
      "system_prompt": "You are an accounts payable exception analyst.",
      "rules": [
        "Identify only issues that require human review.",
        "Ignore normal values that match expectations.",
        "Return strict JSON only."
      ],
      "output_schema": {
        "type": "object",
        "required": ["has_exception", "exceptions"],
        "properties": {
          "has_exception": {"type": "boolean"},
          "exceptions": {
            "type": "array",
            "items": {
              "type": "object",
              "required": ["field", "issue"],
              "properties": {
                "field": {"type": "string"},
                "issue": {"type": "string"}
              }
            }
          }
        }
      }
    },
    "input": {
      "invoice_text": "Invoice total AUD 632.50. PO expects AUD 575.00 before tax. Bank details changed since last invoice.",
      "expected_po_amount": 575.00,
      "last_known_bank_account": "123456789"
    },
    "available_tools": []
  },
  "provider": {"provider": "openai", "model": "gpt-4o-mini"}
}
```

## 8. Example 5 - Internal ops incident digest

Use case: turn incident notes into a structured internal handoff for the next
shift.

```json
{
  "tenant_id": "tenant_acme_ops",
  "workflow": "custom_workflow",
  "task": "incident_shift_handoff",
  "payload": {
    "workflow_definition": {
      "name": "incident_shift_handoff",
      "version": "2026-05-23",
      "system_prompt": "You are an incident commander preparing an operations handoff.",
      "rules": [
        "Summarize timeline, current status, blockers, and next actions.",
        "Use only the supplied incident notes.",
        "Return strict JSON only."
      ],
      "output_schema": {
        "type": "object",
        "required": ["status", "summary", "blockers", "next_actions"],
        "properties": {
          "status": {"type": "string"},
          "summary": {"type": "string"},
          "blockers": {"type": "array", "items": {"type": "string"}},
          "next_actions": {"type": "array", "items": {"type": "string"}}
        }
      }
    },
    "input": {
      "incident_notes": [
        "10:04 UTC latency spike detected.",
        "10:08 UTC worker pool scaled from 4 to 8.",
        "10:14 UTC provider failover moved traffic from OpenAI to OpenRouter.",
        "10:20 UTC customer-facing latency improving but root cause not yet confirmed."
      ]
    },
    "available_tools": []
  },
  "provider": {"provider": "openai", "model": "gpt-4o-mini"}
}
```

## 9. Promotion checklist: when to turn a custom workflow into a plugin

Promote a custom workflow into a first-class plugin when any of these becomes
true:

* More than one tenant needs the same workflow.
* You need stable discovery via `GET /v1/workflows`.
* The workflow needs dedicated tool contracts or approval gates.
* You need server-side validation beyond the outer request shape.
* You want smoke-test coverage in `scripts/full_smoke_test.py`.

## 10. Common mistakes

* Treating `custom_workflow` as a permanent substitute for productized
  workflows.
* Omitting a schema version in the inner definition.
* Passing huge instruction blocks instead of stable `context_ids`.
* Expecting the platform to store and manage custom definitions for you.
* Returning non-JSON text when your own output schema expects strict JSON.
