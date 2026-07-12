# Runbooks

This file lists operational procedures both the platform team and
integrators need. Procedures here assume access to the admin tooling
(internal CLI / dashboard). Integrators have a strict subset of these.

## 1. Rotate a tenant signing secret

Goal: introduce a new signing key version without downtime.

1. Admin generates a new key version `vN+1` for the tenant.
2. Distribute `vN+1` to the integrator securely (out-of-band).
3. Integrator deploys clients that prefer `vN+1`; servers accept `vN`
   and `vN+1` simultaneously.
4. Verify success rate stays at 100% for both versions over 24h.
5. Admin retires `vN`. From this moment, requests with `vN` return
   HTTP 401 `signature_invalid`.

Verification command (admin): `secrets verify --tenant <id> --version vN+1`.

## 2. Rotate a platform encryption key

Goal: rotate the AES-GCM envelope key used to encrypt secrets at rest.

1. Generate a new envelope key version (`KV` increments).
2. Re-encrypt existing ciphertexts: new ciphertexts use `KV`; old
   ciphertexts continue to decrypt with their stored version.
3. Verify with a sample read.
4. Retire the previous version once re-encryption is complete.

The `SecretEncryptor.rotate(...)` flow keeps the system available while
re-encryption runs; readers never fail because of in-progress rotation.

## 3. Replay a `DEAD` workflow

1. Inspect: `workflows show <workflow_id>`. Verify the failure was
   external (e.g. provider outage that has since recovered).
2. Confirm with the requesting tenant that a re-run is desired.
3. Replay: `workflows replay <workflow_id>`. This emits `JOB_QUEUED` with
   a fresh `job_id` and a new `attempt_count`.
4. Monitor: ensure the workflow progresses; abort if it regresses.

Never replay blindly: always inspect a representative sample of DLQ
entries before bulk replay.

## 4. Bulk replay by error class

For DLQ surges sharing the same root cause (e.g. all `parse_failure`
after a bad prompt change), use:

```
workflows replay --tag parse_failure --since "2026-05-18T10:00:00Z" --limit 1000
```

Pre-conditions:

* Root cause fixed and deployed.
* A canary replay of 10 workflows succeeded.
* Tenant ops informed.

## 5. Drain a worker pool

Goal: rolling restart without losing in-flight workflows.

1. Send SIGTERM to a worker. The process stops claiming new messages.
2. Wait for current leases to complete; the worker exits.
3. Repeat per replica with `--max-unavailable=1`.
4. Verify queue depth has not grown abnormally.

`terminationGracePeriodSeconds` must be ≥ the workflow default timeout
for the queue.

## 6. Pause a tenant

Goal: stop accepting new workflows for a tenant (e.g. abuse, billing
freeze) while letting in-flight workflows complete.

1. Admin sets the tenant to `paused`.
2. New submissions return HTTP 403 `tenant_access_denied` with a clear
   message.
3. In-flight workflows run to terminal.
4. Notify the tenant; provide an ETA for resumption if applicable.

## 7. Update tenant routing policy

Goal: change provider preference or restrictions for a tenant.

1. Update the deployment's configured tenant policy store. The standalone
   build exposes an in-memory store for tests and local operation; production
   deployments should back `TenantPolicyStore` with a durable control plane.
2. Apply the new `preferred_hint`, `allowed_providers`, `blocked_providers`,
   or `daily_token_quota` values atomically.
3. Verify with a probe workflow that `PROVIDER_SELECTED` reflects the
   expected provider chain.
4. Watch provider error rate, fallback count, and tenant latency for one
   evaluation window.

Never partially apply a policy update across worker replicas.

## 8. Investigate elevated 5xx

1. Open the platform dashboard, filter by `status>=500` for the last 15
   minutes.
2. Group by `route` and `tenant_id` to find concentration.
3. Pull a sample `trace_id`; inspect the full trace in OTel.
4. Common causes:
   * Redis queue not reachable → restart connection, check AOF disk.
   * Postgres slow → check write IOPS, replication lag, autovacuum.
   * Provider outage cascading → check circuit breaker dashboard.

Communicate every incident with `trace_id`s.

## 9. Investigate elevated 401/403

1. Filter security events by outcome `denied_signature` or
   `denied_tenant` or `denied_role`.
2. Group by `tenant_id` and `principal_id`.
3. Common causes:
   * Client deployed with stale signing key version (rotate runbook).
   * Client mis-formed canonical request (path/query mismatch).
   * Tenant header missing from a proxied path.
   * Clock skew (> 5 minutes).

Engage the tenant if concentration is on one client.

## 10. Failover Redis queue

Procedure (platform team only):

1. Confirm primary unhealthy via direct probe.
2. Promote replica to primary.
3. Update workers’ `REDIS_QUEUE_URL` (rolling restart).
4. Verify XLEN per stream returns to normal.
5. Inspect any `inflight` set members for orphan leases; expire them.

Integrators see brief 503s during failover; they should back off and
retry per the standard error contract.

## 11. Failover Postgres

Procedure (platform team only):

1. Pause writes (or accept failure) momentarily.
2. Trigger replica promotion.
3. Verify schema version and migrations.
4. Resume traffic.

Integrators see 503s and possibly stalled `WAITING_*` states until the
engine reconnects.

## 12. Restore from cold archive

For very old workflows or audit lookups:

1. Identify the time range needed.
2. Detach-attach the relevant partition (event_store, audit_logs,
   ai_generations) from cold storage.
3. Run the read-only query.
4. Detach the partition again.

This is a rare, slow operation. Plan ahead for compliance requests.

## 13. Capacity scale-up

Sustained queue depth growth indicates undersized worker pools:

1. Increase HPA `maxReplicas` for the affected worker.
2. Verify provider quotas can absorb the additional concurrency; if not,
   spread load via routing policy.
3. Confirm latency normalizes; revert if provider 429 rate climbs.

## 14. On-call quick reference

| Signal | First action |
|--------|--------------|
| DLQ growth alert | Sample 5 entries; identify `error_class`. |
| Provider degraded alert | Check breaker state; verify routing falls back. |
| Redis pending alert | Inspect queue lengths and worker liveness. |
| Postgres write latency alert | Check replication lag, IOPS, autovacuum. |
| Tenant 429 alert | Confirm not an abuse spike; check quotas. |
| Signature failure alert | Check signing key rotation status. |

## 15. Rotate a provider API key

Goal: replace an `AI_PLATFORM_PROVIDER_API_KEYS__<provider>` value with no
visible failure window. Provider adapters are stateless and re-read the
key from `Settings` on each request, but `Settings` is loaded once per
process — rotation therefore requires a rolling restart.

1. Mint the new key in the provider console; record its scopes and rate
   limits.
2. Add the new key to the secrets backend under the same logical name.
   Keep the old key available as `AI_PLATFORM_PROVIDER_API_KEYS__<provider>_previous`
   if your secret store supports shadow keys; otherwise stage the change
   on a single canary pod first.
3. Roll the API Deployment with `--max-unavailable=1`. Verify
   `provider:<name>` stays `ok` in `/health/ready` between rollouts.
4. Roll the worker Deployment the same way; workers refresh provider
   adapters from `Settings` on the next claim.
5. Monitor `ai_platform_provider_calls_total{status="failure", provider="<name>"}`
   for 1 hour after rollout.
6. Revoke the old key from the provider console once the failure-rate
   sample is clean.

Backout: re-apply the previous secret value and re-roll. The platform
never persists provider keys to durable storage, so the rollback is a
pure config change.

Per-tenant overrides (`PROVIDER_API_KEYS__<provider>__<tenant>` where
supported by the deployment's policy store) rotate via the same flow but
require updating only the affected tenant's policy record.

## 16. Multi-region failover

The platform pins each tenant to a single region. Cross-region failover is
a tenant-by-tenant operation, not a global flip.

> **Precondition not currently met by this deployment:** this procedure
> assumes a second region's full stack (API, workers, Postgres, secret
> store) is already provisioned and healthy. The current `k8s/` manifests
> describe a single region/cluster with no region or AZ affinity and no
> per-region deployment - there is no standing target region to fail over
> to today, and this procedure has not been drilled. See
> [disaster-recovery.md §12](disaster-recovery.md#12-dr-validation).

Pre-conditions:

* Target region is healthy: `/health/ready` returns `ok` and every
  `provider:<name>` component is `ok`.
* Tenant's `contexts` rows are replicated to the target region's Postgres
  (or were published to both regions at creation time). The platform does
  not replicate context payloads cross-region for you.
* Active workflows in the source region are drained or accepted as
  losses; in-flight `WAITING_TOOL` / `WAITING_APPROVAL` workflows will
  surface in the target region only after the source region's event
  stream is replayed there (step 4).

Procedure:

1. **Pause submissions** in the source region by switching the tenant
   to `paused` (see §6). Capability endpoints return HTTP 403
   `tenant_access_denied`.
2. **Drain in-flight workflows.** Wait until `workflow_runs` for that
   tenant in the source region reports no rows in non-terminal states,
   or accept the in-flight set as a controlled loss with the tenant's
   approval.
3. **Repoint clients.** Update DNS / load-balancer routing for the
   tenant to the target region's API endpoint. Re-issue signing keys if
   regions hold independent secret stores.
4. **Replay history if required.** If long-running workflows must
   resume in the target region, copy the relevant `event_store`
   partitions and `event_snapshots` rows for that tenant from source to
   target, then run the engine's projection rebuild against the target
   region's `workflow_runs`.
5. **Unpause** the tenant in the target region. Verify a probe workflow
   succeeds end-to-end, including a provider call and a tool callback.
6. **Garbage-collect** the source region by archiving the tenant's
   `event_store` and `audit_logs` partitions per
   [disaster-recovery.md](disaster-recovery.md).

`trace_id` is globally unique, so post-failover incident investigation
can correlate logs from both regions on the same `trace_id`.
