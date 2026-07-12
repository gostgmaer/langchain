# Production Readiness Checklist

Use this checklist before pointing live traffic at the platform.

## 1. Identity

* [ ] Tenant id provisioned and shared with us.
* [ ] Principal ids defined for every human/service caller.
* [ ] Upstream API gateway authenticates every caller and forwards
      `x-tenant-id` / `x-principal-id` correctly (this service trusts these
      headers without validating them; see [authentication.md](authentication.md)).

## 2. Request handling

* [ ] All commands include `tenant_id` matching `x-tenant-id`.
* [ ] All commands include `task` with a stable, well-known value.
* [ ] All commands include `workflow` from the supported enum.
* [ ] Token budgets set explicitly for non-default workloads.
* [ ] `timeout_seconds` and `max_attempts` chosen per workflow.
* [ ] `Idempotency-Key` used wherever your producer may retry.
* [ ] `AI_PLATFORM_RATE_LIMIT_BACKEND=redis` and
      `AI_PLATFORM_IDEMPOTENCY_BACKEND=redis` in production.
* [ ] `AI_PLATFORM_PROVIDER_CIRCUIT_BREAKER_BACKEND=redis` in production.
* [ ] `AI_PLATFORM_PROVIDER_QUOTA_BACKEND=redis` in production.
* [ ] `AI_PLATFORM_PROVIDER_DAILY_TOKEN_QUOTAS__<provider>` configured for
      every provider key used by production.

## 3. Polling

* [ ] Exponential backoff on `GET /v1/jobs/{id}` (no fast loops).
* [ ] Polling watcher is **single-writer** per workflow id.
* [ ] Terminal statuses (`SUCCESS`, `FAILED`, `CANCELLED`, `DEAD`) stop polling.
* [ ] Watcher restart is safe (state persisted on your side).

## 4. Tool and approval callbacks

* [ ] Endpoint for `POST /v1/workflows/{id}/tool-results` implemented
      using `workflow_id` + `pending_action.tool_name` from status.
* [ ] Endpoint for `POST /v1/workflows/{id}/approvals` implemented for
      authorized approvers (authorization enforced by your upstream gateway,
      not this service).
* [ ] Tool service load-tested at 2× expected throughput.
* [ ] Tool errors are returned with `status:"error"` and a clear code.
* [ ] Tool callback timeout < workflow `timeout_seconds`.

## 5. Error handling

* [ ] HTTP 400/422 → do **not** retry; log and surface to the user.
* [ ] HTTP 401/403 from your gateway → page on-call; this service itself
      never returns 401/403 for auth reasons (auth is enforced upstream).
* [ ] HTTP 404 → tenant mismatch or workflow not in scope.
* [ ] HTTP 409 → idempotency conflict; use a new key.
* [ ] HTTP 429 → back off honoring `Retry-After`.
* [ ] HTTP 503 → exponential backoff with jitter; alert if persistent.

## 6. Contexts

* [ ] Every required context exists in your context store at the time of
      submission.
* [ ] Hot contexts (brand voice, frequent personas) are stable identifiers.
* [ ] Large contexts split into `:summary` and `:full` variants.
* [ ] PII minimized; sensitive fields kept out of `payload` where possible.

## 7. Observability (your side)

* [ ] Log `trace_id`, `workflow_id`, `job_id` alongside your business id.
* [ ] OpenTelemetry instrumentation propagates traceparent to the platform.
* [ ] Dashboards for: submission rate, success rate, time-to-terminal,
      retry count, DLQ count.
* [ ] Alerts for: sustained 5xx, sustained 4xx, DLQ
      growth, watcher backlog.
* [ ] Dead-letter replay runbook tested with a non-production workflow.

## 8. Security and compliance

* [ ] Upstream API gateway authenticates and authorizes every caller before
      forwarding requests to this service.
* [ ] mTLS terminating LB (deployment-dependent) in place if required.
* [ ] No provider API keys live in your codebase or logs.
* [ ] Sensitive fields in payloads are minimized or pre-redacted.
* [ ] Data residency confirmed with platform admin.
* [ ] Tenant erasure procedure documented on your side.

## 9. Capacity and quotas

* [ ] Tenant RPS and concurrency quotas agreed and configured.
* [ ] Daily token / cost ceilings agreed and configured.
* [ ] Per-workflow budgets matched to product economics.
* [ ] Bulk-only workflows routed through `BULK_PROCESSING`.
* [ ] API and worker replicas scaled independently.
* [ ] `/health/ready` is `ok` before opening traffic, including
      `workflow_worker` and all configured `provider:<name>` components.
* [ ] Load smoke test passes at expected peak traffic before cutover.

## 10. Runbooks and on-call

* [ ] On-call rota covers your integration code.
* [ ] You can find every request by `trace_id` in your sink.
* [ ] You have a runbook for: stuck `WAITING_TOOL`, stuck
      `WAITING_APPROVAL`, DEAD spike, encryption key rotation, tenant pause.
* [ ] Contact path to the platform team is documented and tested.

## 11. Disaster recovery

* [ ] Polling watcher survives your own restart.
* [ ] Idempotent submissions (idempotency keys) on your side.
* [ ] Backup plan if the platform is unavailable for an extended period
      (e.g. degraded mode with templated responses, or queueing).
* [ ] Periodic DR drill in staging.

## 12. Documentation

* [ ] Internal docs link to:
      [getting-started.md](getting-started.md),
      [deployment.md](deployment.md),
      [api.md](api.md),
      [authentication.md](authentication.md),
      [workflows.md](workflows.md),
      [integration-guide.md](integration-guide.md),
      [end-to-end-validation.md](end-to-end-validation.md),
      [sdk-examples.md](sdk-examples.md),
      [scaling.md](scaling.md),
      [security.md](security.md),
      [runbooks.md](runbooks.md),
      [disaster-recovery.md](disaster-recovery.md).
* [ ] Runbooks reference platform contact info.
* [ ] Sample requests/responses are captured for regression tests.

## 13. Go-live sign-off

* [ ] Staging soak run for at least 24 hours at expected load.
* [ ] Production rollout gated by progressive % of traffic.
* [ ] Rollback plan: switch your client back to the previous integration
      branch (or to a degraded template path) within 5 minutes.
* [ ] Stakeholders briefed (product, support, on-call, security).

Once every box is checked, you are ready to ship.
