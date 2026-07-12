# Security

This is the integration-facing security model. It complements
[authentication.md](authentication.md) and
[provider-routing.md](provider-routing.md).

## 1. Trust boundary

* This service is a fully internal microservice. It does **not** authenticate
  or authorize inbound requests.
* Authentication and authorization are enforced upstream, by the API gateway
  (or whichever trusted internal caller sits in front of this service).
* This service trusts the `x-tenant-id` and `x-principal-id` headers
  forwarded by the gateway and reads them into request context without
  validating or re-checking them. See [authentication.md](authentication.md)
  for the full header contract.
* The platform never returns provider API keys, never echoes back stored
  secrets, and never logs prompts whose fields are marked sensitive.

## 2. Identity model

* **Tenant** — identified via `x-tenant-id`, forwarded by the gateway and
  used to scope data access; not validated by this service.
* **Principal** — the human or service acting (e.g. `user_42`, `svc_bot`),
  identified via `x-principal-id`; not validated by this service.

## 3. Data protection

### 3.1 In transit

* TLS 1.2+ required everywhere; mTLS optional at the LB tier.
* Provider egress is encrypted by each provider's SDK/HTTPS.

### 3.2 At rest

* Workflow projection payloads, event payloads, and context payloads are
  encrypted with **AES-GCM** using **versioned platform keys** when
  `AI_PLATFORM_SECURITY_ACTIVE_KEY_VERSION` is configured.
* Provider API keys are represented as `SecretStr` in configuration and must
  be injected from a secrets manager.
* Encryption metadata records the key version per ciphertext, so rotation
  never breaks decryption.
* Rotation procedure: see [runbooks.md](runbooks.md). New ciphertexts use
  the current key; old ciphertexts decrypt with their original version
  until re-encrypted.

### 3.3 Sensitive fields

* Prompts and payloads pass through a redaction layer before logging.
* Fields recognized as sensitive (API keys, salaries, emails when
  configured) are replaced with `***` in logs and traces.
* Structured logs use `structlog` with sensitive-field processors.

## 4. Tenant isolation

* Every row in every operational table is tenant-scoped.
* Partial unique indexes prevent cross-tenant id collisions on the same
  resource type.
* Query layer always parameterizes `tenant_id` from the request context.
* Workers refuse to act on a workflow whose `tenant_id` does not match
  the leased message's `tenant_id`.
* `audit_logs` and `security_events` are also tenant-partitioned.

This isolation operates on the `tenant_id` forwarded in request context; it
does not itself authenticate the caller (see [Trust boundary](#1-trust-boundary)).

## 5. Audit and security events

Every request and every security-relevant action emits a record:

* `audit_logs` — business event audit (workflow created, approved,
  rejected, retried, dead-lettered).
* `security_events` — suspicious patterns (high error rate from a single
  principal, repeated cross-tenant attempts) and other security-relevant
  outcomes.

Both are time-partitioned and indexed by `tenant_id` and `trace_id` for
investigation.

## 6. Provider key handling

* Provider API keys are platform secrets, never tenant secrets.
* Per-tenant overrides for provider keys (BYO-keys) are stored encrypted
  and used only for that tenant's requests.
* Keys are never logged, never returned by any API, never embedded in
  events.

## 7. Compliance posture

* PII minimization: prefer pointer contexts over inlined PII.
* Data retention: `event_store` and `audit_logs` retained per policy
  (default 365 days online; cold archive thereafter).
* Right-to-erasure: tenant-scoped erasure removes workflow projections,
  contexts, and audit entries (subject to legal hold). Event data is
  redacted where possible; references are tombstoned.
* Data residency: enforced by routing policy and tenant configuration.

## 8. Threat model highlights

| Threat | Mitigation |
|--------|------------|
| Cross-tenant data access | Tenant binding in middleware, ORM, and worker leasing, based on the trusted `x-tenant-id` context. |
| Prompt injection | Strict schemas on outputs; tool calls are platform-mediated. |
| Provider exfiltration | Per-tenant egress allow-list, no opaque tool execution from prompts. |
| Cross-tenant realtime subscriptions | Tenant id validation before SSE/WebSocket stream creation. |
| Agent fan-out abuse | Tenant in-flight workflow caps. |
| Insider DLQ inspection | DLQ read access is audited. |
| Log scraping for PII | Redaction at the structlog processor level. |

Authentication and authorization threats (spoofed callers, stolen
credentials, unauthorized access) are the responsibility of the API gateway
in front of this service and are out of scope here.

## 9. Vulnerability response

* Report security issues privately to the platform team.
* The platform commits to acknowledging within 24h and providing a
  remediation timeline within 5 business days.
* Critical issues may trigger emergency rotation of encryption keys;
  operators must be ready to follow the rotation runbook on short notice.
