# Authentication & Identity Headers

This service is a fully internal microservice. It sits behind a trusted API
gateway (or is called only by other trusted internal services) and performs
**no authentication or authorization of its own**. No endpoint in this
service returns `401`/`403` for auth reasons — those checks happen upstream,
before a request ever reaches this service.

## Trust model

* The API gateway (or trusted internal caller) is solely responsible for
  authenticating the original caller and deciding whether the request is
  allowed.
* Once a request is authenticated and authorized upstream, the gateway
  forwards two identity headers to this service:
  * `x-tenant-id` — the tenant the request is for.
  * `x-principal-id` — the human or service acting on behalf of the tenant.
* This service reads those headers into request context (for propagation,
  logging, and tenant-scoped data access) but does **not** validate,
  cross-check, or enforce them. It trusts that the gateway has already done
  that work correctly.
* If a header is missing, this service does not reject the request; the
  request simply proceeds with an empty/absent value in that part of the
  context.

## Headers

| Header | Config field | Purpose |
|--------|--------------|---------|
| `x-tenant-id` | `AI_PLATFORM_REQUEST_TENANT_HEADER` (default `x-tenant-id`) | Identifies the tenant for the request; used to scope data access and propagate `tenant_id` through logs, events, and worker leases. |
| `x-principal-id` | `AI_PLATFORM_REQUEST_PRINCIPAL_HEADER` (default `x-principal-id`) | Identifies the caller acting on behalf of the tenant; propagated through logs and traces. |
| `x-trace-id` | `AI_PLATFORM_REQUEST_TRACE_HEADER` (default `x-trace-id`) | Optional. If omitted, this service generates one and returns it in the response and every log line for that request. |

These are just header *names* — configurable in case the gateway uses
different conventions — not enforcement toggles. There is no setting that
makes tenant or principal headers required, and no role/permission check is
performed on them.

## What this service does NOT do

* It does not verify that the caller is who they claim to be.
* It does not check roles or permissions.
* It does not verify request signatures.
* It does not reject a request because `x-tenant-id` is missing, malformed,
  or mismatched with anything in the body.

All of the above is the responsibility of the API gateway / trusted caller
in front of this service.

## Related, but separate, controls

A few settings sound auth-related but are not part of the (removed) inbound
authentication/authorization layer:

* `AI_PLATFORM_BILLING_ENFORCED` — a tenant billing/subscription gate. When
  enabled, workflow execution is blocked (`402 Payment Required`) for
  tenants whose billing account is not active. This is a business rule, not
  an authentication check. See [business-flows.md](business-flows.md).
* `AI_PLATFORM_SECURITY_ENCRYPTION_KEYS__*` /
  `AI_PLATFORM_SECURITY_ACTIVE_KEY_VERSION` — data-at-rest envelope
  encryption for stored payloads/secrets. Unrelated to inbound request
  authentication. See [security.md](security.md).

See also [security.md](security.md) for the trust-boundary summary and
[configuration.md](configuration.md) for the full settings catalog.
