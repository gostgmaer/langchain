# Webhooks and Polling

> **Current supported contract:** integrations discover workflow progress by
> polling `GET /v1/workflows/{workflow_id}` and `GET /v1/jobs/{job_id}`.
> When a workflow is paused, the status response exposes `pending_action`,
> which is the supported way to drive tool calls and approvals today.
> This document also records the planned webhook shape so teams can design
> receivers that will be forward-compatible when delivery is enabled.

If your workflow is mission-critical, do not block your roadmap on
webhooks; the polling contract is stable and sufficient. See
[event-model.md](event-model.md) for the underlying events.

## 1. Subscription model

Per tenant, an admin will register one or more **subscriptions**:

| Field | Notes |
|-------|-------|
| `subscription_id` | platform-assigned |
| `url` | HTTPS endpoint owned by the integrator |
| `events` | subset of `EventName` |
| `workflows` | optional allow-list of workflow names |
| `signing_key_version` | for HMAC verification |
| `retry_policy` | bounded exponential backoff |

Subscription management endpoints will live under
`/v1/admin/webhook-subscriptions` and require `admin` role.

## 2. Delivery contract (target)

* Each event will be POSTed to `url` once with at-least-once semantics.
* Body is the same `EventEnvelope` shape as the event store (see
  [event-model.md](event-model.md)).
* Headers include:
  * `x-tenant-id`
  * `x-trace-id`
  * `x-webhook-event` (the `event_name`)
  * `x-webhook-id` (unique per delivery)
  * `x-signature-key-version`, `x-signature-timestamp`, `x-signature`
* The signing payload mirrors API request signing:
  `POST\n<path>\n<timestamp>\nSHA256_HEX(body)`.

## 3. Receiver requirements

* **Idempotent handlers.** Deduplicate by `event_id` (preferred) or
  `(workflow_id, event_name, occurred_at)`.
* **Fast acknowledgement.** Return HTTP 2xx within 5 seconds; offload work
  to your queues. Slow handlers trigger redelivery.
* **Verify the signature** before doing anything with the body.
* **Tolerate unknown fields and unknown `event_name` values** — silently
  drop or persist for later interpretation.

Example minimal handler (Node.js Express):

```javascript
app.post("/webhooks/ai-platform", express.raw({ type: "application/json" }),
  (req, res) => {
    if (!verifySignature(req)) return res.sendStatus(401);
    queue.enqueue("ai_platform_event", req.body); // your queue
    return res.sendStatus(204);
  });
```

## 4. Retries and dead-lettering

* The platform will retry failed deliveries with exponential backoff
  (capped, e.g. up to 24h).
* Persistent failures (HTTP 4xx other than 408/429, repeated 5xx beyond
  cap) move the delivery to a dead-letter store accessible to admins.
* Disabling a subscription pauses deliveries; pending deliveries are
  retained for inspection.

## 5. Polling-first design

Even after webhooks ship, every integrator must keep polling working:

* During webhook outages or subscription dead-letters, polling is the
  fallback.
* Late or missed events do not delay your business: the workflow status
  endpoint always shows the latest truth.
* Use webhooks to **reduce polling frequency**, not to replace it.

## 6. Why delivery is polling-first today

The event log, transactional outbox, and idempotency primitives are all
implemented internally. Building a robust public webhook surface requires:

* Subscription management UI/API.
* Receiver health monitoring.
* Per-subscription back-pressure to protect platform throughput.
* Dead-letter inspection for operators.

This work is sequenced after platform GA. Integration teams should design
for the contract above so adoption is a configuration change, not a
rework.

## 7. Interim guidance

* Build a single **status watcher** service for your workflows.
* Implement an internal pub/sub from the watcher so your downstream
  consumers can subscribe to your shape, not the platform’s.
* When webhooks ship, replace the watcher’s polling loop with a webhook
  receiver. The downstream contract you publish to your own teams will
  not change.
