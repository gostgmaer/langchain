# Tenant-Managed Custom Workflow Definition API Design

> Status: proposed, not implemented.
>
> This document defines a future public API for storing, versioning, activating,
> and using tenant-managed custom workflow definitions. It is intentionally
> separate from the current public contract in [api.md](api.md).

## 1. Why this API is needed

The platform already supports runtime custom behavior through
`workflow="custom_workflow"` and an inline `payload.workflow_definition`.
That is enough for experimentation, but it leaves three product gaps:

* Definitions are not persisted by the platform.
* Definitions are not versioned through a public API.
* Integrators must manage the full custom definition payload themselves on
  every request.

The database already contains `workflow_definitions`, and workflow runs already
reference `workflow_definition_id`, but there is no public CRUD surface yet.
This API fills that gap.

## 2. Goals

* Let a tenant create, version, read, activate, and archive custom workflow
  definitions over HTTP.
* Keep the existing `custom_workflow` execution path compatible.
* Make stored definitions safe to use from Postman, SDKs, and external apps.
* Support version pinning and explicit activation.
* Preserve tenant isolation and auditability.

## 3. Non-goals

* Replacing the plugin registry for first-class built-in workflows.
* Allowing arbitrary code execution.
* Creating a visual workflow builder in this iteration.
* Managing provider secrets or external tool credentials in this API.
* Exposing low-level internal DB rows directly.

## 4. Current state

Current public execution model:

```json
{
  "tenant_id": "tenant_acme",
  "workflow": "custom_workflow",
  "task": "candidate_screening_brief",
  "payload": {
    "workflow_definition": {
      "name": "candidate_screening_brief",
      "version": "2026-05-23",
      "system_prompt": "...",
      "rules": ["..."],
      "output_schema": {"type": "object"}
    },
    "input": {"resume": "..."}
  }
}
```

Current storage primitives already present:

* `workflow_definitions` table
* active-version uniqueness by (`tenant_id`, `workflow`)
* version uniqueness by (`tenant_id`, `workflow`, `version`)
* `workflow_definition_id` foreign key on workflow runs and steps

## 5. Proposed model

A tenant-managed custom workflow definition is a named, versioned template that
executes through the existing `custom_workflow` runner.

### 5.1 Resource shape

```json
{
  "tenant_id": "tenant_acme",
  "name": "candidate_screening_brief",
  "version": "2026-05-23",
  "description": "Summarise candidate fit against a target role.",
  "definition": {
    "system_prompt": "You are a senior recruiting operations analyst.",
    "rules": [
      "Use only supplied facts.",
      "Return strict JSON only."
    ],
    "input_schema": {
      "type": "object",
      "required": ["candidate_resume", "role_summary"],
      "properties": {
        "candidate_resume": {"type": "string"},
        "role_summary": {"type": "string"}
      }
    },
    "output_schema": {
      "type": "object",
      "required": ["summary", "fit_score"],
      "properties": {
        "summary": {"type": "string"},
        "fit_score": {"type": "number"}
      }
    },
    "available_tools": [],
    "default_provider": "openai",
    "default_model": "gpt-4o-mini",
    "timeout_seconds": 900,
    "metadata": {
      "owner_team": "talent-ops",
      "stability": "beta"
    }
  },
  "is_active": true,
  "created_at": "2026-05-23T12:00:00Z",
  "updated_at": "2026-05-23T12:00:00Z"
}
```

### 5.2 Storage mapping

This design maps directly onto the existing `workflow_definitions` table:

* `workflow_definitions.workflow` ← `name`
* `workflow_definitions.version` ← `version`
* `workflow_definitions.description` ← `description`
* `workflow_definitions.definition` ← `definition`
* `workflow_definitions.is_active` ← `is_active`

No schema change is required for the initial version of this API.

## 6. Proposed permissions

These permissions do not exist today. They are proposed additions to RBAC.

| Permission | Purpose | Suggested roles |
|---|---|---|
| `workflow_definition:read` | list and inspect stored definitions | `viewer`, `operator`, `admin` |
| `workflow_definition:write` | create new versions | `operator`, `admin` |
| `workflow_definition:activate` | switch active version | `operator`, `admin` |
| `workflow_definition:delete` | archive old versions | `admin` |

## 7. Proposed endpoints

### 7.1 Create a definition version

```text
POST /v1/custom-workflow-definitions
```

Request:

```json
{
  "tenant_id": "tenant_acme",
  "name": "candidate_screening_brief",
  "version": "2026-05-23",
  "description": "Summarise candidate fit against a target role.",
  "definition": {
    "system_prompt": "You are a senior recruiting operations analyst.",
    "rules": ["Use only supplied facts.", "Return strict JSON only."],
    "input_schema": {"type": "object"},
    "output_schema": {"type": "object"},
    "available_tools": [],
    "default_provider": "openai",
    "default_model": "gpt-4o-mini",
    "timeout_seconds": 900,
    "metadata": {"owner_team": "talent-ops"}
  },
  "activate": true
}
```

Response:

```json
{
  "success": true,
  "trace_id": "trace-abc123",
  "data": {
    "name": "candidate_screening_brief",
    "version": "2026-05-23",
    "is_active": true
  }
}
```

Rules:

* Creating an existing (`tenant_id`, `name`, `version`) returns HTTP 409.
* `activate=true` deactivates the previously active version atomically.
* The `definition` payload is JSON Schema validated before persistence.

### 7.2 List definitions

```text
GET /v1/custom-workflow-definitions
GET /v1/custom-workflow-definitions?name=candidate_screening_brief
GET /v1/custom-workflow-definitions?active_only=true
```

Response:

```json
{
  "definitions": [
    {
      "name": "candidate_screening_brief",
      "version": "2026-05-23",
      "description": "Summarise candidate fit against a target role.",
      "is_active": true,
      "created_at": "2026-05-23T12:00:00Z",
      "updated_at": "2026-05-23T12:00:00Z"
    }
  ],
  "summary": {
    "total": 1,
    "active": 1
  }
}
```

### 7.3 Get a definition version

```text
GET /v1/custom-workflow-definitions/{name}/versions/{version}
```

Returns the full stored definition payload.

### 7.4 Activate a version

```text
POST /v1/custom-workflow-definitions/{name}/versions/{version}/activate
```

Response returns the activated version and the previously active version, if any.

### 7.5 Archive a version

```text
DELETE /v1/custom-workflow-definitions/{name}/versions/{version}
```

Rules:

* Archive is soft-delete only.
* If the archived version is active, the caller must first activate another
  version or explicitly pass `allow_deactivate=true`.

## 8. Proposed execution contract

Stored definitions should execute through the existing public workflow runner.

### 8.1 Submit using a stored definition

```text
POST /v1/workflows/run
```

Request:

```json
{
  "tenant_id": "tenant_acme",
  "workflow": "custom_workflow",
  "task": "candidate_screening_brief",
  "payload": {
    "definition_name": "candidate_screening_brief",
    "definition_version": "2026-05-23",
    "input": {
      "candidate_resume": "7 years Python, FastAPI, Redis.",
      "role_summary": "Staff AI infrastructure engineer."
    }
  }
}
```

Version behavior:

* If `definition_version` is supplied, use that exact version.
* If it is omitted, resolve the tenant’s active version.
* If `workflow_definition` is supplied inline, it overrides the stored
  definition for that single request.

Resolution precedence:

1. `payload.workflow_definition` inline
2. `payload.definition_name` + `payload.definition_version`
3. `payload.definition_name` + active stored version
4. error `workflow_definition_not_found`

## 9. Validation rules

* `name` matches `^[a-z][a-z0-9_]*$` and is 3–128 chars.
* `version` max length 32.
* `definition.system_prompt` is required.
* `definition.output_schema` is required.
* `definition.input_schema`, if present, must be a valid JSON Schema object.
* `definition.available_tools` is descriptive only unless the platform later
  adds a tool registry integration.
* `default_provider` must be one of the supported provider names.

## 10. Error model

Proposed error codes:

| Code | HTTP | Meaning |
|---|---|---|
| `workflow_definition_validation_error` | 422 | invalid stored definition payload |
| `workflow_definition_not_found` | 404 | no matching tenant-scoped definition |
| `workflow_definition_version_conflict` | 409 | duplicate name/version |
| `workflow_definition_active_conflict` | 409 | active version conflict during activation |
| `workflow_definition_in_use` | 409 | attempted to delete an active or referenced version |

## 11. Audit and observability

Every mutation should emit:

* audit log with `tenant_id`, `principal_id`, `name`, `version`, and action
  (`created`, `activated`, `archived`)
* security event for denied access
* structured log with `trace_id`

Workflow runs created from stored definitions should persist
`workflow_definition_id` on the run record so operators can reconstruct which
version produced a result.

## 12. Rollout plan

### Phase 1

* Public CRUD API for stored definitions.
* `custom_workflow` resolves `definition_name` / `definition_version`.
* Inline `workflow_definition` remains supported.

### Phase 2

* SDK helpers for create/list/activate.
* Postman collection examples for managed definitions.
* Import/export support.

### Phase 3

* Optional promotion path from stored definition to first-class plugin.
* Tenant-level governance policies for allowed tools/providers.

## 13. Why this design is safe

* It reuses the existing `workflow_definitions` table.
* It preserves today’s public execution contract.
* It does not claim server-side validation of arbitrary business logic beyond
  schema and envelope checks.
* It keeps custom definitions tenant-scoped and auditable.
* It avoids mixing experimental tenant logic into the global plugin registry.
