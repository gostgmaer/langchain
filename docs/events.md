# Events (Kafka)

Kafka integration is optional and controlled by `ENABLE_KAFKA=true`.

When enabled, the service operates as a NestJS hybrid microservice — it listens to Kafka topics in addition to serving HTTP.

---

## Configuration

```env
ENABLE_KAFKA=true
KAFKA_BROKERS=localhost:9092
KAFKA_CLIENT_ID=notification-service
KAFKA_GROUP_ID=notification-service-group
```

Multiple brokers: `KAFKA_BROKERS=broker1:9092,broker2:9092`

---

## Consumer Topics

The service subscribes to these topics and processes them as inbound notification requests.

### `sms.notification.send`

Trigger an SMS send via Kafka event.

**Payload schema:**

```json
{
  "tenantId": "tenant_abc",
  "to": "+919876543210",
  "from": "MYAPP",
  "message": "Your order has shipped!",
  "templateCode": "ORDER_SHIPPED",
  "variables": {
    "orderId": "ORD-001",
    "trackingUrl": "https://track.example.com/ORD-001"
  },
  "messageType": "TRANSACTIONAL",
  "referenceId": "order-shipped-ORD-001",
  "dltTemplateId": "1234567890",
  "dltEntityId": "9876543210",
  "metadata": {}
}
```

**Required fields:** `to`  
**Optional:** All other fields mirror the HTTP `/v1/sms/send` request body.

---

### `email.notification.send`

Trigger an email send via Kafka event.

**Payload schema:**

```json
{
  "tenantId": "tenant_abc",
  "appName": "MyApp",
  "appUrl": "https://myapp.com",
  "ctaPath": "/dashboard",
  "idempotencyKey": "welcome-usr_123",
  "to": "user@example.com",
  "from": "noreply@myapp.com",
  "fromName": "MyApp",
  "subject": "Welcome to MyApp",
  "template": "USER_WELCOME",
  "data": {
    "username": "John Doe",
    "email": "user@example.com"
  },
  "cc": [],
  "bcc": [],
  "metadata": {}
}
```

**Required fields:** `to`, `template` or `templateId`  
**Optional:** All other fields mirror the HTTP `/v1/email/send` request body.

---

## Producer Topics

The service publishes delivery events to these topics after processing each notification.

### `sms.notification.delivered`

Published when an SMS is successfully accepted by a provider.

```json
{
  "messageId": "550e8400-e29b-41d4-a716-446655440000",
  "tenantId": "tenant_abc",
  "to": "+919876543210",
  "status": "SENT",
  "provider": "twilio",
  "providerMessageId": "SMxxxxxxxx",
  "sentAt": "2026-06-02T10:00:01.000Z",
  "cost": 0.0075,
  "currency": "INR",
  "referenceId": "order-shipped-ORD-001",
  "metadata": {}
}
```

---

### `sms.notification.failed`

Published when an SMS permanently fails (all retry attempts exhausted).

```json
{
  "messageId": "550e8400-e29b-41d4-a716-446655440000",
  "tenantId": "tenant_abc",
  "to": "+919876543210",
  "status": "FAILED",
  "provider": "twilio",
  "error": "Invalid phone number",
  "attempts": 3,
  "failedAt": "2026-06-02T10:00:30.000Z",
  "referenceId": "order-shipped-ORD-001",
  "metadata": {}
}
```

---

### `email.notification.delivered`

Published when an email is accepted by the SMTP server.

```json
{
  "requestId": "550e8400-e29b-41d4-a716-446655440000",
  "tenantId": "tenant_abc",
  "to": "user@example.com",
  "template": "USER_WELCOME",
  "status": "sent",
  "messageId": "<msg-id@smtp.server>",
  "idempotencyKey": "welcome-usr_123",
  "sentAt": "2026-06-02T10:00:02.000Z"
}
```

---

### `email.notification.failed`

Published when an email permanently fails.

```json
{
  "requestId": "550e8400-e29b-41d4-a716-446655440000",
  "tenantId": "tenant_abc",
  "to": "user@example.com",
  "template": "USER_WELCOME",
  "status": "failed",
  "error": "SMTP connection refused",
  "idempotencyKey": "welcome-usr_123",
  "failedAt": "2026-06-02T10:00:10.000Z"
}
```

---

## Topic Summary

| Direction | Topic | Description |
|---|---|---|
| Consumer | `sms.notification.send` | Inbound: trigger SMS send |
| Consumer | `email.notification.send` | Inbound: trigger email send |
| Producer | `sms.notification.delivered` | Outbound: SMS accepted by provider |
| Producer | `sms.notification.failed` | Outbound: SMS permanently failed |
| Producer | `email.notification.delivered` | Outbound: Email accepted by SMTP |
| Producer | `email.notification.failed` | Outbound: Email permanently failed |

---

## Docker Compose (Kafka)

Use the `kafka` profile to start Zookeeper + Kafka alongside the service:

```bash
docker compose --profile kafka up -d
```

This starts:
- Zookeeper on port `2181`
- Kafka broker on port `9092`

---

## Disable Kafka

Set `ENABLE_KAFKA=false` (the default) to run the service in pure HTTP mode. All Kafka consumers and producers are disabled. This has no effect on BullMQ queue functionality.
