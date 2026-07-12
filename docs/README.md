# Notification Service — Documentation

A unified, production-grade notification service built on **NestJS** that delivers messages through **Email** (SMTP/OAuth2) and **SMS** (33 providers). It supports BullMQ queuing, Kafka event streaming, multi-tenancy, idempotency, retry logic, 378 email templates, and webhook DLR callbacks.

---

## Quick Start

```bash
# Install
pnpm install

# Copy env file and fill in values
cp .env.example .env

# Start MongoDB + Redis
docker compose --profile infra up -d

# Start service in dev mode
pnpm run dev
# → Service: http://localhost:4000
# → Swagger: http://localhost:4000/docs  (non-production only)
```

**Authenticate every request:**
```
Authorization: Bearer <API_KEY>
x-api-key: <API_KEY>
x-tenant-id: your_tenant_id
```

---

## Documentation Index

| Document | Description |
|---|---|
| [architecture.md](architecture.md) | System design, components, data-flow diagrams |
| [api-reference.md](api-reference.md) | Every endpoint — method, URL, headers, schemas, examples |
| [integration-guide.md](integration-guide.md) | Step-by-step integration for Email, SMS, OTP, Bulk, Webhooks |
| [events.md](events.md) | Kafka published/consumed events with payload schemas |
| [queues.md](queues.md) | BullMQ queues, job types, retry policies |
| [database.md](database.md) | MongoDB schemas, indexes, ER diagram |
| [templates.md](templates.md) | All 378+ email templates + SMS template engine |
| [security.md](security.md) | Auth, API keys, webhook signatures, rate limiting |
| [deployment.md](deployment.md) | Docker, local dev, staging, production, monitoring |
| [troubleshooting.md](troubleshooting.md) | Common errors, debugging, FAQ |
| [sdk-examples.md](sdk-examples.md) | Code samples in JS/TS/Python/Java/Go/C# |
| [openapi.yaml](openapi.yaml) | Machine-readable OpenAPI 3.0 specification |

### Diagrams

| Diagram | Description |
|---|---|
| [high-level-architecture.mmd](diagrams/high-level-architecture.mmd) | Full system components |
| [request-flow.mmd](diagrams/request-flow.mmd) | HTTP request processing |
| [queue-flow.mmd](diagrams/queue-flow.mmd) | BullMQ job lifecycle |
| [event-flow.mmd](diagrams/event-flow.mmd) | Kafka publish/consume |
| [notification-lifecycle.mmd](diagrams/notification-lifecycle.mmd) | SMS/Email state machine |
| [database-er.mmd](diagrams/database-er.mmd) | MongoDB collection relationships |

---

## Integration Suite (`integration/`)

Detailed integration artifacts for service owners building against the Notification Service.

| Document | Description |
|---|---|
| [integration/integration-guide.md](integration/integration-guide.md) | Full guide with SDK examples for Node.js, TypeScript, NestJS, Express, Python, Go, Angular, Vue 3 |
| [integration/integration-audit.md](integration/integration-audit.md) | Channel coverage audit — what is fully/partially/not integrated |
| [integration/template-catalog.md](integration/template-catalog.md) | Complete 378-template reference with required `data` fields and header flags |
| [integration/email-templates.md](integration/email-templates.md) | HTML layout standards, dark mode, responsive design, CTA button patterns |
| [integration/sms-templates.md](integration/sms-templates.md) | SMS template catalog, DLT/TRAI compliance, 160-char limit guidance |
| [integration/push-templates.md](integration/push-templates.md) | Proposed push notification standard (NOT YET IMPLEMENTED) |
| [integration/inapp-templates.md](integration/inapp-templates.md) | Proposed in-app notification standard (NOT YET IMPLEMENTED) |
| [integration/event-contracts.md](integration/event-contracts.md) | JSON Schema for all 6 Kafka topics with NestJS code examples |
| [integration/webhook-guide.md](integration/webhook-guide.md) | All 19 SMS provider webhook endpoints with signature verification |
| [integration/postman_collection.json](integration/postman_collection.json) | Postman v2.1 collection — import directly |
| [integration/bruno/](integration/bruno/) | Bruno API client collection (`.bru` files) |

---

## Channels

| Channel | Status | Notes |
|---|---|---|
| **Email** | Implemented | SMTP + OAuth2 (Gmail), 378 templates, CC/BCC, idempotency, circuit breaker, fallback SMTP |
| **SMS** | Implemented | 33 providers, OTP flow, bulk campaigns, GDPR purge, analytics, retry worker |
| Push Notifications | Not implemented | No module exists in the current codebase |
| In-App Notifications | Not implemented | No module exists in the current codebase |

---

## Feature Summary

| Feature | Detail |
|---|---|
| **SMS Providers** | 33 providers: Twilio, MSG91, Vonage, Fast2SMS, AWS SNS, Gupshup, Kaleyra, Infobip, Telnyx, Sinch, Plivo, TextLocal, Exotel, D7Networks, RouteMobile, ValueFirst, MessageBird, AirtelIQ, JioCX, SMSCountry, SMSGateway, 2Factor, MTalkz, Clickatell, Brevo, BulkSMS, TextMagic, NetCore, Sarv, Pinnacle, Unifonic, Mock |
| **Email Templates** | 378 built-in typed templates across Auth, Orders, Payments, Subscriptions, Cart, Org, System, Marketing, and more |
| **Queuing** | BullMQ (Redis-backed), exponential backoff, 3 attempts, 30-day failure retention |
| **Kafka** | Producer + consumer for sms.send, email.send, sms.delivered, sms.failed, email.delivered, email.failed |
| **Multi-tenancy** | Soft isolation via `x-tenant-id` header — all queries and logs scoped per tenant |
| **Idempotency** | `x-idempotency-key` (email) and `referenceId` (SMS) prevent duplicate sends |
| **Analytics** | Delivery summary, per-provider health, bulk campaign tracking |
| **Webhooks** | Inbound DLR callbacks from 19 SMS providers, public endpoints |
| **Retry** | BullMQ retry (queued mode) + background retry worker (direct mode), 3 attempts with delays 30s/2m/10m |
| **Security** | API key guard (timing-safe compare), Helmet, CORS, ThrottlerModule rate limiting |
| **Health** | Three probes: `/v1/health`, `/v1/health/detailed`, `/v1/health/live` |

---

## Minimal Request Examples

### Send Email
```bash
curl -X POST http://localhost:4000/v1/email/send \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -H "x-tenant-id: tenant_abc" \
  -H "x-app-name: MyApp" \
  -H "x-app-url: https://app.example.com" \
  -H "x-path: /dashboard" \
  -H "x-idempotency-key: welcome-user123" \
  -d '{
    "to": "john@example.com",
    "template": "USER_WELCOME",
    "data": { "username": "John Doe", "email": "john@example.com" }
  }'
```

### Send SMS
```bash
curl -X POST http://localhost:4000/v1/sms/send \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -H "x-tenant-id: tenant_abc" \
  -d '{
    "to": "+919876543210",
    "message": "Your OTP is 847291. Valid for 10 minutes.",
    "messageType": "OTP"
  }'
```

### Send OTP
```bash
curl -X POST http://localhost:4000/v1/sms/otp/send \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -H "x-tenant-id: tenant_abc" \
  -d '{ "to": "+919876543210", "otpLength": 6, "expiresInMinutes": 10 }'
```

---

## Default Service Port

```
4000
```

> Swagger UI: `GET http://localhost:4000/docs` (available only when `NODE_ENV != production`)
