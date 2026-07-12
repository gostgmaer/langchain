# Disaster Recovery

The platform is designed so that no single failure causes permanent
workflow loss. This document explains what is recoverable, what is not,
and how integrators should design their side accordingly.

## 1. Failure classes

| Class | Examples | Impact | Recovery |
|-------|----------|--------|----------|
| Transient | provider 5xx, redis blip, worker crash | retried automatically | none for caller |
| Region | full AZ/region outage | tenant unreachable until manually failed over | manual, tenant-by-tenant (see below) - not minutes |
| Database | Postgres primary down | writes 503 | replica promotion |
| Queue | Redis queue down | submissions 503 | replica promotion |
| Data corruption | bad migration, bad replay | reads may be wrong | event replay |
| Catastrophic | data center loss | inactive workflows until DR | cold-storage restore |

## 2. RPO and RTO targets

These are deployment defaults; your tenant may negotiate stricter values:

| Component | RPO | RTO |
|-----------|-----|-----|
| Workflow state (event_store) | 0 (sync to replica) | minutes |
| Workflow projection | seconds (rebuilt) | minutes (rebuild on demand) |
| Redis queue (AOF) | seconds | minutes |
| `ai_generations` (cost/audit) | seconds | minutes |
| `audit_logs`, `security_events` | seconds | minutes |

## 3. What survives a Postgres failure

Once a workflow is accepted (HTTP 202 returned), its existence is durable:

* `event_store` is the source of truth.
* The projection (workflow_runs) is rebuildable from events.
* In-flight tool/approval callbacks return 503 until DB recovers; clients
  should retry per the standard contract.

## 4. What survives a Redis queue failure

* Submissions return HTTP 503; clients back off.
* In-flight workers cannot ACK; on Redis recovery, leases time out and
  workers resume. Idempotency prevents duplicate provider calls.
* No event is lost because events are written to the DB first
  (transactional outbox), then fanned out via the queue.

## 5. Event-store replay

Operators can rebuild any workflow’s state at any time:

1. Read all events for `workflow_id` ordered by `version`.
2. Apply via the state machine to produce a snapshot.
3. Optionally repopulate the projection.

This is the foundation of recovery: as long as `event_store` survives,
workflows can be reconstructed.

## 6. Cold archive

* `event_store` partitions older than the online retention are archived
  to cold storage (e.g. object storage with WORM).
* Archived partitions can be re-attached for compliance reads or
  reconstructions.
* Cold reads are not real-time; expect minutes to hours.

## 7. Backup strategy (platform-side)

* Postgres: point-in-time recovery (WAL) + daily base backups, retained
  per compliance.
* Redis queue: AOF + RDB snapshots; replicas pinned to a separate failure
  domain.
* Configuration, prompt files, and deployment manifests: versioned in Git.

## 8. Failover playbook

See [runbooks.md](runbooks.md) for the step-by-step procedures:

* Failover Redis queue.
* Failover Postgres.
* Restore from cold archive.

## 9. Integrator-side DR practices

* **Idempotent submission.** Use `Idempotency-Key` so accidental
  re-submission during your DR is safe.
* **Persistent workflow ids.** Store `workflow_id`, `job_id`, and
  `trace_id` next to your business records; these are how you reconnect
  after your own failover.
* **Stateless polling watcher.** Build it so a restart resumes from your
  store, not from a polling cursor.
* **Idempotent tool callbacks.** Correlate by `workflow_id` plus
  `pending_action.tool_name` and make your own tool execution idempotent.
* **Time tolerance.** Allow your business processes to absorb minutes of
  platform unavailability — design SLAs with that buffer.

## 10. What is not recoverable

* A specific provider call is not replayable byte-for-byte; replays may
  produce different text. Treat workflow output as canonical only via
  the platform’s persisted `result`.
* External tool side-effects (booking a calendar, charging a card)
  cannot be undone by the platform. Make your tools idempotent and use
  compensating actions when needed.
* Cold archives older than legal hold may be irrecoverable; check the
  retention policy of your deployment before assuming long-term replay.

## 11. Communication during incidents

* The platform exposes a status page (deployment-specific URL).
* Every incident references `trace_id`s and affected workflows where
  possible.
* Tenants are notified for incidents with material customer impact.
* Post-incident reviews share root cause, timeline, and follow-ups.

## 12. DR validation

The platform team performs periodic DR drills:

* Quarterly Postgres failover drill.
* Quarterly Redis queue failover drill.
* Bi-annual cold archive restoration drill.

**Region failover is not currently drilled.** The current deployment
(`k8s/*.yaml`) is a single region/cluster with no region or availability-zone
affinity, no per-region manifests, and no automated cross-region traffic
shifting - there is no second region's stack standing by for §16's procedure
to fail over to. [runbooks.md §16](runbooks.md#16-multi-region-failover)
documents what a tenant-by-tenant region failover *would* involve if a
deployment stood up a second region, but it is a manual playbook, not an
exercised, automated capability, and no drill against it has been run against
this deployment. Treat the platform's actual DR posture as single-region
today; integrators whose own SLAs assume a tested region-failover capability
should confirm that directly with the platform team rather than relying on
this document.

Integrators are encouraged to run their own drills (chaos in staging) to
verify their idempotency and polling resilience.
