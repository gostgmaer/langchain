# Context Management

The platform does not own your business data. Brand voices, candidate
profiles, order details, contract clauses, and similar references are
delivered to a workflow through **contexts**.

## 1. Concept

A context is a named, versioned JSON object scoped to a tenant. You publish
it once (or update it over time), and reference it from a workflow request
by its `context_id`. The workflow’s worker hydrates contexts before running
prompts.

| Property | Notes |
|----------|-------|
| `context_id` | string, identifier pattern, max 128 chars |
| `tenant_id` | the owning tenant |
| `version` | monotonically increasing integer (≥ 1) |
| `payload` | arbitrary JSON object |

## 2. Why contexts (instead of payload inlining)

| Concern | Inline payload | Context reference |
|---------|----------------|-------------------|
| Reuse across workflows | duplicated | single source of truth |
| Audit (which version was used?) | impossible | `version_hash` in event log |
| Cacheability | poor (random payload) | high (Redis + Postgres) |
| Size pressure | 256 KiB cap easily hit | cap mostly avoided |
| Cross-team ownership | one team owns the prompt and the data | data teams own contexts |

Use payload for *this-request-only* values (the message body to reply to,
the JD pasted by a user). Use contexts for *reusable* values (brand voice,
candidate profile, policy doc, persona).

## 3. Resolution flow

```text
client request ──► gateway ──► context resolver
                              │
                              ├─► Redis cache lookup (per (tenant_id, context_id))
                              │      hit → use
                              │      miss → Postgres lookup
                              │             miss → ContextResolutionError
                              │
                              └─► version_hash = sha256(sorted(context_id:version))
                                  emitted in CONTEXT_RESOLVED event
```

If any `context_id` cannot be resolved, the workflow fails immediately with
`context_resolution_error` — it is a business input error, not a transient
failure, and is **not** retried.

## 4. Versioning and cache invalidation

* Contexts are immutable per (id, version). Updates produce a new version.
* The cache key includes the version, so cache lookups always return either
  the requested version or a miss.
* When you publish a new version, optionally invalidate the latest pointer.
  In-flight workflows continue to use whatever version they resolved at
  submission time.

## 5. Limits

| Limit | Value |
|-------|-------|
| Context IDs per request | 50 |
| Payload size per context | 256 KiB (recommended ≤ 64 KiB for fast caching) |
| Payload nesting depth | 16 |
| Identifier length | 128 |

## 6. Multi-tenancy

* Contexts are strictly scoped: a `context_id` in tenant A is invisible to
  tenant B even if the id string is identical.
* Cross-tenant references are rejected at the resolver.

## 7. Recommended context taxonomy

| Family | Example ids | Typical owner |
|--------|-------------|---------------|
| Brand | `brand_voice_default`, `brand_voice_premium` | Marketing |
| Persona | `persona_recruiter_sara`, `persona_support_ana` | Product |
| Policy | `policy_returns_v3`, `policy_disputes_v2` | Legal/ops |
| Customer | `customer_8821`, `customer_8821:summary` | CRM |
| Candidate | `candidate_456`, `candidate_456:resume` | ATS |
| Document | `contract_2026q2_v1`, `invoice_99812` | DMS |

## 8. Pre-flight checks

Before calling the platform, ensure:

* Every `context_id` exists (use your own DB).
* Every context is fresh enough for the workflow’s needs.
* Sensitive fields are stripped or encrypted at rest by your service —
  the platform protects in transit and at rest, but minimization is your
  responsibility.

## 9. Failure modes

| Symptom | Cause | Fix |
|---------|-------|-----|
| `context_resolution_error` | Unknown `context_id` for tenant | Publish the context, retry workflow |
| Stale output | Workflow used older context version | Publish new version, resubmit workflow |
| 422 `validation_error` | Inline payload too big or too deeply nested | Move data into contexts |
| Slow workflows | Context cache miss rate high | Pre-warm cache with frequent ids |

## 10. Where contexts live

* Hot store: Redis cache (LRU).
* Warm store: PostgreSQL (`contexts` table), tenant-scoped, with unique
  active partial index per (tenant, context_id, version).
* The platform never copies contexts to providers — they are merged into
  prompts and discarded after generation.
