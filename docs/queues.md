# Queues (BullMQ)

BullMQ is the optional job queue backed by Redis. Enable it with `ENABLE_BULL=true`.

When enabled:
- SMS sends are enqueued in the `sms` queue
- Email sends are enqueued in the `email` queue
- Processors consume jobs asynchronously with retry logic

---

## Configuration

```env
ENABLE_BULL=true
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_DB=0
BULL_QUEUE_PREFIX=notification
```

---

## Queues

### `sms` Queue

Handles SMS send operations.

| Job Name | Description |
|---|---|
| `sms.send` | Send a single SMS |
| `sms.bulk` | Send a bulk SMS campaign |

**Job options:**

```typescript
{
  attempts: 3,
  backoff: {
    type: 'exponential',
    delay: 5000  // 5s, 25s, 125s
  },
  removeOnComplete: { count: 1000 },
  removeOnFail: { count: 500 }
}
```

**`sms.send` job payload:**

```json
{
  "tenantId": "tenant_abc",
  "to": "+919876543210",
  "message": "Your OTP is 847291",
  "templateCode": "OTP_VERIFICATION",
  "variables": { "otp": "847291" },
  "messageType": "OTP",
  "referenceId": "otp-usr_123-20260602",
  "from": "MYAPP",
  "dltTemplateId": "1234567890",
  "dltEntityId": "9876543210",
  "metadata": {}
}
```

**`sms.bulk` job payload:**

```json
{
  "campaignId": "550e8400-...",
  "tenantId": "tenant_abc",
  "recipients": [
    { "to": "+919876543210", "variables": { "name": "Alice" } }
  ],
  "templateCode": "PROMO_CODE",
  "batchSize": 50
}
```

---

### `email` Queue

Handles email send operations.

| Job Name | Description |
|---|---|
| `email.send` | Send a single email |

**Job options:**

```typescript
{
  attempts: 3,
  backoff: {
    type: 'exponential',
    delay: 5000  // 5s, 25s, 125s
  },
  removeOnComplete: { count: 1000 },
  removeOnFail: { count: 500 }
}
```

**`email.send` job payload:**

```json
{
  "tenantId": "tenant_abc",
  "appName": "MyApp",
  "appUrl": "https://myapp.com",
  "ctaPath": "/orders/ORD-001",
  "idempotencyKey": "order-confirm-ORD-001",
  "to": "user@example.com",
  "from": "noreply@myapp.com",
  "fromName": "MyApp",
  "template": "ORDER_CONFIRMED",
  "data": {
    "username": "John",
    "orderId": "ORD-001",
    "totalAmount": "1499.00"
  },
  "cc": [],
  "bcc": [],
  "metadata": {}
}
```

---

## Job Flow

```
HTTP Request (POST /v1/sms/send or POST /v1/email/send)
    │
    ├─ Validates payload
    ├─ Saves log to MongoDB (status=queued)
    └─ queue.add(jobName, payload, options)
          │ returns { jobId }
          ▼
    202 Accepted → { success: true, data: { jobId, queued: true } }

BullMQ Worker (SmsProcessor / EmailProcessor)
    │
    ├─ Picks up job from Redis
    ├─ Calls SmsService.sendSms() / EmailService.sendEmail()
    ├─ Success → updates log status to SENT / sent
    └─ Failure → BullMQ retries (exponential backoff)
                 After 3 failures → updates log status to FAILED
```

---

## Retry Behaviour

| Queue | Max Attempts | Backoff Strategy | Delays |
|---|---|---|---|
| `sms` (BullMQ) | 3 | Exponential (5s base) | 5s, 25s, 125s |
| `email` (BullMQ) | 3 | Exponential (5s base) | 5s, 25s, 125s |
| SMS background retry worker | 3 | Fixed delays | 30s, 2m, 10m |

The **SMS background retry worker** (`SmsRetryService`) runs every 60 seconds independently of BullMQ. It picks up logs with `status=RETRYING` and retries them using the fixed delay schedule. This is active regardless of `ENABLE_BULL` setting.

---

## Monitoring

### Get Job Status

You can poll job status via the BullMQ Job ID (not exposed through the public API — use the Bull Dashboard or connect directly to Redis).

### Redis Key Pattern

Jobs are stored with keys matching:
```
{BULL_QUEUE_PREFIX}:{queue}:*
```

Default prefix: `notification`

Example keys:
```
notification:sms:waiting
notification:sms:active
notification:sms:completed
notification:sms:failed
notification:email:waiting
notification:email:active
```

---

## Running Without BullMQ

Set `ENABLE_BULL=false` (default). Send requests are processed synchronously:

- SMS: `POST /v1/sms/send` calls `SmsService.sendSms()` directly, returns result immediately
- Email: `POST /v1/email/send` calls `EmailService.sendEmail()` directly

The `POST /v1/email/send-sync` endpoint always bypasses the queue regardless of `ENABLE_BULL`.

---

## Docker Compose

BullMQ requires Redis. Start Redis with:

```bash
docker compose --profile infra up -d
```

Or start the full stack:

```bash
docker compose --profile full up -d
```
