# API Reference

Base URL: `http://localhost:4000` (default port 4000)

All protected endpoints require:
```
Authorization: Bearer <API_KEY>
```
or
```
x-api-key: <API_KEY>
```

---

## Table of Contents

- [SMS — Send Single](#post-v1smssend)
- [SMS — Send Bulk](#post-v1smssend-bulk)
- [SMS — List Messages](#get-v1sms)
- [SMS — Get Message](#get-v1smsmessageid)
- [SMS — GDPR Purge](#delete-v1smsmessageidgdpr-purge)
- [SMS — Send OTP](#post-v1smsotpsend)
- [SMS — Verify OTP](#post-v1smsotpverify)
- [Templates — Create](#post-v1templates)
- [Templates — List](#get-v1templates)
- [Templates — Get](#get-v1templatestemplateid)
- [Templates — Update](#put-v1templatestemplateid)
- [Templates — Delete](#delete-v1templatestemplateid)
- [Templates — Import](#post-v1templatesimport)
- [Analytics — Summary](#get-v1analyticssummary)
- [Analytics — Provider Health](#get-v1analyticsprovider-health)
- [Analytics — Campaign Stats](#get-v1analyticscampaignscampaignid)
- [Analytics — List Campaigns](#get-v1analyticscampaigns)
- [Webhooks — Provider DLR](#post-v1webhooksprovider)
- [Email — Send](#post-v1emailsend)
- [Email — Send Sync](#post-v1emailsend-sync)
- [Email — Metrics](#get-v1emailmetrics)
- [Email — List Logs](#get-v1emaillogs)
- [Email — Get Log](#get-v1emaillogsrequestid)
- [Email — SMTP Health](#get-v1emailhealth)
- [Health — Check](#get-v1health)
- [Health — Detailed](#get-v1healthdetailed)
- [Health — Liveness](#get-v1healthlive)

---

## SMS Endpoints

### POST /v1/sms/send

Send a single SMS message.

**Authentication:** Required (`x-api-key` / `Authorization: Bearer`)  
**Tag:** SMS  
**Response:** 202 Accepted

#### Headers

| Header | Required | Description |
|---|---|---|
| `x-api-key` | Yes* | API authentication key (*or Authorization) |
| `x-tenant-id` | No | Tenant identifier for data isolation |

#### Request Body

```json
{
  "to": "+919876543210",
  "from": "MYAPP",
  "message": "Your OTP is 847291",
  "templateId": "6650a1f2e4b0c23d4f8a91bc",
  "templateCode": "otp_verification",
  "templateName": "OTP Verification",
  "variables": { "otp": "847291", "name": "John" },
  "messageType": "OTP",
  "unicode": false,
  "referenceId": "login-otp-123",
  "dltTemplateId": "1234567890",
  "dltEntityId": "9876543210",
  "metadata": { "userId": "usr_123" }
}
```

**Field Descriptions:**

| Field | Type | Required | Description |
|---|---|---|---|
| `to` | string | Yes | Recipient phone number in E.164 format (`+91...`) |
| `from` | string | No | Sender ID or number |
| `message` | string | Conditional | Message body (required if no template reference) |
| `templateId` | string | Conditional | MongoDB ObjectId of an SMS template |
| `templateCode` | string | Conditional | Template code (e.g. `OTP_VERIFICATION`) |
| `templateName` | string | Conditional | Template name |
| `variables` | object | No | Key-value pairs substituted into the template body `{{key}}` |
| `messageType` | enum | No | `TRANSACTIONAL` \| `PROMOTIONAL` \| `OTP` \| `FLASH` (default: `TRANSACTIONAL`) |
| `unicode` | boolean | No | Send as Unicode SMS |
| `referenceId` | string | No | Your reference ID — used for idempotency deduplication |
| `dltTemplateId` | string | No | India TRAI DLT Template ID |
| `dltEntityId` | string | No | India TRAI DLT Principal Entity ID |
| `metadata` | object | No | Arbitrary key-value metadata stored with the log |

**Validation Rules:**
- `to` must be a string (phone normalisation is applied internally via libphonenumber-js)
- `message` max 1600 characters
- `messageType` must be one of the four enum values
- At least one of `message`, `templateId`, `templateCode`, or `templateName` must be provided

#### Response 202 (queued mode: `ENABLE_BULL=true`)

```json
{
  "success": true,
  "data": {
    "jobId": "1234",
    "queued": true
  }
}
```

#### Response 202 (direct mode: `ENABLE_BULL=false`)

```json
{
  "success": true,
  "data": {
    "messageId": "550e8400-e29b-41d4-a716-446655440000",
    "status": "SENT",
    "to": "+919876543210",
    "provider": "twilio",
    "providerMessageId": "SM1234567890abcdef",
    "cost": 0.0075,
    "currency": "INR",
    "segmentCount": 1,
    "queuedAt": "2026-06-02T10:00:00.000Z",
    "sentAt": "2026-06-02T10:00:01.123Z"
  }
}
```

#### Error Responses

| Status | Condition |
|---|---|
| 400 | Validation error (missing/invalid fields) |
| 401 | Invalid or missing API key |
| 404 | Template not found |
| 429 | Rate limit exceeded |
| 500 | Provider error |

---

### POST /v1/sms/send-bulk

Send SMS to multiple recipients as a named campaign.

**Authentication:** Required  
**Tag:** SMS  
**Response:** 202 Accepted

#### Request Body

```json
{
  "recipients": [
    { "to": "+919876543210", "variables": { "name": "Alice" } },
    { "to": "+919876543211", "variables": { "name": "Bob" } },
    { "to": "+919876543212", "message": "Custom message for this recipient" }
  ],
  "message": "Hello {{name}}, your order is ready.",
  "templateCode": "ORDER_READY",
  "from": "MYAPP",
  "name": "June Flash Sale",
  "messageType": "PROMOTIONAL",
  "batchSize": 50,
  "dltTemplateId": "1234567890",
  "dltEntityId": "9876543210"
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `recipients` | array | Yes | List of recipient objects |
| `recipients[].to` | string | Yes | Phone number |
| `recipients[].message` | string | No | Per-recipient override message |
| `recipients[].variables` | object | No | Per-recipient template variables |
| `message` | string | Conditional | Shared message for all recipients (if no template) |
| `templateCode` | string | Conditional | Shared template code |
| `templateId` | string | Conditional | Shared template MongoDB ID |
| `name` | string | No | Campaign display name |
| `messageType` | enum | No | `TRANSACTIONAL` \| `PROMOTIONAL` \| `OTP` \| `FLASH` |
| `batchSize` | integer | No | Recipients per batch, 1–500 (default: 50) |
| `dltTemplateId` | string | No | TRAI DLT Template ID |
| `dltEntityId` | string | No | TRAI DLT Entity ID |

#### Response 202

```json
{
  "success": true,
  "data": {
    "campaignId": "550e8400-e29b-41d4-a716-446655440000",
    "totalCount": 3,
    "status": "RUNNING"
  }
}
```

> The campaign runs asynchronously. Poll `GET /v1/analytics/campaigns/:campaignId/detail` for progress.

---

### GET /v1/sms

List SMS messages with pagination and filters.

**Authentication:** Required  
**Tag:** SMS

#### Query Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `page` | integer | 1 | Page number |
| `limit` | integer | 20 | Items per page |
| `status` | string | — | Filter by status (`QUEUED`, `SENT`, `DELIVERED`, `FAILED`, etc.) |

#### Response 200

```json
{
  "success": true,
  "data": [ /* SmsLog objects */ ],
  "pagination": {
    "total": 150,
    "page": 1,
    "limit": 20,
    "pages": 8
  }
}
```

---

### GET /v1/sms/:messageId

Get a single SMS message log by its internal message ID.

**Authentication:** Required  
**Tag:** SMS

#### Path Parameters

| Parameter | Description |
|---|---|
| `messageId` | UUID message ID returned when the SMS was sent |

#### Response 200

```json
{
  "success": true,
  "data": {
    "messageId": "550e8400-e29b-41d4-a716-446655440000",
    "status": "DELIVERED",
    "to": "+919876543210",
    "from": "MYAPP",
    "message": "Your OTP is 847291",
    "provider": "twilio",
    "providerMessageId": "SMxxx",
    "tenantId": "tenant_abc",
    "segmentCount": 1,
    "cost": 0.0075,
    "currency": "INR",
    "dlrReceived": true,
    "dlrTimestamp": "2026-06-02T10:00:05.000Z",
    "sentAt": "2026-06-02T10:00:01.000Z",
    "deliveredAt": "2026-06-02T10:00:05.000Z",
    "createdAt": "2026-06-02T10:00:00.000Z",
    "attempts": [
      { "attemptNumber": 1, "provider": "twilio", "status": "SENT", "timestamp": "2026-06-02T10:00:01.000Z" }
    ],
    "statusHistory": [
      { "status": "QUEUED", "timestamp": "2026-06-02T10:00:00.000Z" },
      { "status": "SENT",   "timestamp": "2026-06-02T10:00:01.000Z" },
      { "status": "DELIVERED", "timestamp": "2026-06-02T10:00:05.000Z" }
    ]
  }
}
```

---

### DELETE /v1/sms/:messageId/gdpr-purge

Permanently erase PII from an SMS log (GDPR right to erasure).

**Authentication:** Required  
**Tag:** SMS

#### Response 200

```json
{
  "success": true,
  "data": {
    "messageId": "...",
    "gdprPurgedAt": "2026-06-02T10:00:00.000Z",
    "status": "PURGED"
  }
}
```

---

### POST /v1/sms/otp/send

Generate and send a one-time password via SMS.

**Authentication:** Required  
**Tag:** SMS  
**Response:** 202 Accepted

#### Request Body

```json
{
  "to": "+919876543210",
  "templateCode": "otp_verification",
  "templateId": "6650a1f2e4b0c23d4f8a91bc",
  "variables": { "name": "John" },
  "otpLength": 6,
  "expiresInMinutes": 10
}
```

| Field | Type | Required | Constraints | Description |
|---|---|---|---|---|
| `to` | string | Yes | — | Recipient phone number |
| `templateCode` | string | No | — | Template code for OTP message body |
| `templateId` | string | No | — | Template MongoDB ID |
| `variables` | object | No | — | Extra template variables (OTP is auto-injected as `{{otp}}`) |
| `otpLength` | integer | No | 4–8 | Length of generated OTP (default: 6) |
| `expiresInMinutes` | integer | No | 1–60 | OTP validity in minutes (default: 10) |

#### Response 202

```json
{
  "success": true,
  "data": {
    "referenceId": "550e8400-e29b-41d4-a716-446655440001",
    "to": "+919876543210",
    "expiresAt": "2026-06-02T10:10:00.000Z",
    "messageId": "550e8400-e29b-41d4-a716-446655440000"
  }
}
```

---

### POST /v1/sms/otp/verify

Verify an OTP that was previously sent.

**Authentication:** Required  
**Tag:** SMS

#### Request Body

```json
{
  "to": "+919876543210",
  "otp": "847291"
}
```

#### Response 200

```json
{
  "success": true,
  "data": {
    "valid": true,
    "to": "+919876543210"
  }
}
```

---

## SMS Template Endpoints

### POST /v1/templates

Create a new SMS template.

**Authentication:** Required  
**Tag:** SMS Templates

#### Request Body

```json
{
  "name": "OTP Verification",
  "code": "OTP_VERIFICATION",
  "body": "Your OTP is {{otp}}. Valid for {{minutes}} minutes. — {{appName}}",
  "category": "OTP",
  "dltTemplateId": "1234567890",
  "dltEntityId": "9876543210",
  "senderId": "MYAPP"
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `name` | string | Yes | Human-readable template name (unique per tenant) |
| `code` | string | No | Auto-generated from name if omitted; uppercase, unique per tenant |
| `body` | string | Yes | Template body with `{{variable}}` placeholders |
| `category` | enum | No | `TRANSACTIONAL` \| `PROMOTIONAL` \| `OTP` (default: `TRANSACTIONAL`) |
| `dltTemplateId` | string | No | TRAI DLT Template ID |
| `dltEntityId` | string | No | TRAI DLT Entity ID |
| `senderId` | string | No | Default sender ID for this template |

#### Response 201

```json
{
  "success": true,
  "data": {
    "_id": "6650a1f2e4b0c23d4f8a91bc",
    "name": "OTP Verification",
    "code": "OTP_VERIFICATION",
    "body": "Your OTP is {{otp}}. Valid for {{minutes}} minutes.",
    "variables": ["otp", "minutes"],
    "category": "OTP",
    "isActive": true,
    "tenantId": "tenant_abc",
    "createdAt": "2026-06-02T10:00:00.000Z"
  }
}
```

---

### GET /v1/templates

List SMS templates with pagination.

**Authentication:** Required

#### Query Parameters

| Parameter | Type | Description |
|---|---|---|
| `page` | integer | Page number (default: 1) |
| `limit` | integer | Items per page (default: 20) |
| `search` | string | Filter by name |

#### Response 200

```json
{
  "success": true,
  "data": [ /* SmsTemplate objects */ ],
  "pagination": { "total": 5, "page": 1, "limit": 20, "pages": 1 }
}
```

---

### GET /v1/templates/:templateId

Get a single SMS template by its MongoDB ID.

**Authentication:** Required

#### Response 200

```json
{
  "success": true,
  "data": {
    "_id": "6650a1f2e4b0c23d4f8a91bc",
    "name": "OTP Verification",
    "code": "OTP_VERIFICATION",
    "body": "Your OTP is {{otp}}.",
    "variables": ["otp"],
    "category": "OTP",
    "isActive": true
  }
}
```

---

### PUT /v1/templates/:templateId

Update an SMS template.

**Authentication:** Required

#### Request Body (partial update)

```json
{
  "body": "Your new OTP: {{otp}}. Do not share.",
  "dltTemplateId": "9999999999"
}
```

#### Response 200

```json
{ "success": true, "data": { /* updated template */ } }
```

---

### DELETE /v1/templates/:templateId

Soft-delete an SMS template (sets `isDeleted=true`).

**Authentication:** Required

#### Response 200

```json
{ "success": true, "data": { "_id": "...", "isDeleted": true, "deletedAt": "..." } }
```

---

### POST /v1/templates/import

Auto-import sample templates from the `sample-templates.json` file.

**Authentication:** Required

#### Response 200

```json
{
  "success": true,
  "data": { "imported": 5, "skipped": 2 }
}
```

---

## Analytics Endpoints

### GET /v1/analytics/summary

Get SMS delivery summary statistics.

**Authentication:** Required  
**Tag:** SMS Analytics

#### Query Parameters

| Parameter | Type | Description |
|---|---|---|
| `from` | ISO date string | Start of date range |
| `to` | ISO date string | End of date range |

#### Response 200

```json
{
  "success": true,
  "data": {
    "summary": {
      "total": 10000,
      "sent": 9500,
      "delivered": 9200,
      "failed": 300,
      "queued": 100,
      "retrying": 100,
      "totalCost": 750.50,
      "totalSegments": 10250
    },
    "byProvider": [
      { "_id": "twilio", "total": 5000, "sent": 4900, "delivered": 4750, "failed": 100, "totalCost": 375.25 }
    ],
    "byStatus": [
      { "_id": "SENT", "count": 9500 },
      { "_id": "DELIVERED", "count": 9200 }
    ]
  }
}
```

> Results are cached for 60 seconds per tenant.

---

### GET /v1/analytics/provider-health

Get per-provider success/error rates for the last 24 hours.

**Authentication:** Required  
**Tag:** SMS Analytics

#### Response 200

```json
{
  "success": true,
  "data": [
    {
      "provider": "twilio",
      "total": 1200,
      "sent": 1180,
      "failed": 20,
      "successRate": 0.9833,
      "errorRate": 0.0167
    }
  ]
}
```

---

### GET /v1/analytics/campaigns/:campaignId

Get summary statistics for a bulk SMS campaign.

**Authentication:** Required

#### Response 200

```json
{
  "success": true,
  "data": {
    "campaignId": "550e8400-...",
    "name": "June Flash Sale",
    "status": "COMPLETED",
    "totalCount": 1000,
    "sentCount": 980,
    "deliveredCount": 960,
    "failedCount": 20,
    "startedAt": "2026-06-02T09:00:00.000Z",
    "completedAt": "2026-06-02T09:05:00.000Z"
  }
}
```

---

### GET /v1/analytics/campaigns

List all bulk SMS campaigns.

**Authentication:** Required

#### Query Parameters

| Parameter | Description |
|---|---|
| `page` | Page number |
| `limit` | Items per page |

#### Response 200

```json
{
  "success": true,
  "data": [ /* SmsCampaign objects */ ],
  "pagination": { "total": 15, "page": 1, "limit": 20, "pages": 1 }
}
```

---

### GET /v1/analytics/campaigns/:campaignId/detail

Get full detail of a specific campaign.

**Authentication:** Required

#### Response 200

```json
{
  "success": true,
  "data": { /* full SmsCampaign document */ }
}
```

---

## Webhook Endpoints (Public — No Auth Required)

These endpoints receive inbound delivery receipt (DLR) callbacks from SMS providers.

All paths follow the pattern: `POST /v1/webhooks/:provider`

| Endpoint | Provider | Signature Header |
|---|---|---|
| `POST /v1/webhooks/twilio` | Twilio | `x-twilio-signature` |
| `POST /v1/webhooks/vonage` | Vonage (Nexmo) | `x-nexmo-signature` |
| `POST /v1/webhooks/msg91` | MSG91 | `x-msg91-signature` |
| `POST /v1/webhooks/fast2sms` | Fast2SMS | `x-fast2sms-signature` |
| `POST /v1/webhooks/textlocal` | TextLocal | `x-textlocal-hash` |
| `POST /v1/webhooks/gupshup` | Gupshup | `x-hub-signature-256` |
| `POST /v1/webhooks/kaleyra` | Kaleyra | `x-kaleyra-signature` |
| `POST /v1/webhooks/exotel` | Exotel | `x-exotel-signature` |
| `POST /v1/webhooks/infobip` | Infobip | `ibm-signature` |
| `POST /v1/webhooks/telnyx` | Telnyx | `telnyx-signature-ed25519` |
| `POST /v1/webhooks/sinch` | Sinch | `x-sinch-signature` |
| `POST /v1/webhooks/plivo` | Plivo | `x-plivo-signature-v2` |
| `POST /v1/webhooks/d7networks` | D7Networks | `x-d7-signature` |
| `POST /v1/webhooks/jiocx` | JioCX | `x-jiocx-signature` |
| `POST /v1/webhooks/airteliq` | AirtelIQ | `x-airtel-signature` |
| `POST /v1/webhooks/routemobile` | RouteMobile | `x-rm-signature` |
| `POST /v1/webhooks/valuefirst` | ValueFirst | `x-vf-signature` |
| `POST /v1/webhooks/smscountry` | SMSCountry | `x-smscountry-signature` |
| `POST /v1/webhooks/smsgateway` | SMSGateway | `x-hub-signature` |

#### Response 200

```json
{ "received": true, "provider": "twilio", "processed": true }
```

---

## Email Endpoints

### POST /v1/email/send

Send an email using a named template. Supports idempotency, optional BullMQ queuing, CC, and BCC.

**Authentication:** Required  
**Tag:** Email  
**Response:** 202 Accepted

#### Required Headers

| Header | Description |
|---|---|
| `x-tenant-id` | Tenant identifier |
| `x-app-name` (or `x-app`) | Application display name for email branding |
| `x-app-url` | Base URL for footer links / CTA buttons |
| `x-path` | CTA path appended to `x-app-url` |
| `x-idempotency-key` | Deduplication key (same key = silently skipped) |

#### Optional Headers

| Header | Description |
|---|---|
| `x-from-email` | Override sender email address |
| `x-from-name` | Override sender display name |

#### Request Body

```json
{
  "to": "john@example.com",
  "from": "noreply@myapp.com",
  "fromName": "MyApp",
  "cc": ["manager@myapp.com"],
  "bcc": ["audit@myapp.com"],
  "subject": "Custom subject (optional if template generates one)",
  "template": "ORDER_CONFIRMED",
  "templateId": "6650a1f2e4b0c23d4f8a91bc",
  "data": {
    "username": "John Doe",
    "orderId": "ORD-2026-001",
    "totalAmount": "1499.00"
  },
  "idempotencyKey": "order-ORD-2026-001-confirm",
  "metadata": { "source": "checkout" },
  "appUrl": "https://app.myapp.com",
  "ctaPath": "/orders/ORD-2026-001"
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `to` | email | Yes | Recipient email address |
| `from` | email | No | Sender override (falls back to `EMAIL_FROM` / `DEFAULT_FROM_EMAIL`) |
| `fromName` | string | No | Sender name override |
| `cc` | email[] | No | Carbon copy recipients |
| `bcc` | email[] | No | Blind carbon copy recipients |
| `subject` | string | No | Subject line (auto-generated by template if omitted) |
| `template` | string | Conditional | Template name from the 378-template registry |
| `templateId` | string | Conditional | Custom template MongoDB ObjectId |
| `data` | object | Conditional | Template data — required fields depend on chosen template |
| `idempotencyKey` | string | No | Prevents duplicate sends (header preferred over body field) |
| `metadata` | object | No | Arbitrary metadata stored with the log |
| `appUrl` | string | No | Base URL fallback (header `x-app-url` takes precedence) |
| `ctaPath` | string | No | CTA path fallback (header `x-path` takes precedence) |

#### Response 202 (queued)

```json
{
  "success": true,
  "message": "Email queued for processing",
  "requestId": "550e8400-e29b-41d4-a716-446655440000",
  "jobId": "42"
}
```

#### Response 202 (direct, idempotent duplicate)

```json
{
  "success": true,
  "message": "Email already processed",
  "idempotencyKey": "order-ORD-2026-001-confirm",
  "requestId": "550e8400-e29b-41d4-a716-446655440000"
}
```

#### Response 202 (direct, sent)

```json
{
  "success": true,
  "message": "Email sent successfully",
  "messageId": "<msg-id@smtp.server>",
  "requestId": "550e8400-e29b-41d4-a716-446655440000"
}
```

#### Error Responses

| Status | Condition |
|---|---|
| 400 | Missing required headers or template data fields |
| 401 | Invalid API key |
| 429 | Rate limit exceeded |
| 500 | SMTP error or circuit breaker open |

---

### POST /v1/email/send-sync

Send an email synchronously — waits for SMTP response. Same request/response shape as `/v1/email/send` but always bypasses the queue and always returns the SMTP messageId.

**Authentication:** Required  
**Response:** 200 OK

---

### GET /v1/email/metrics

Get email delivery metrics and circuit breaker status.

**Authentication:** Required

#### Response 200

```json
{
  "circuitBreaker": { "state": "CLOSED", "failures": 0 },
  "smtpConfigured": true,
  "database": { "connected": true },
  "dbStats": {
    "queued": 10,
    "sent": 9500,
    "failed": 50,
    "retrying": 5
  }
}
```

---

### GET /v1/email/logs

List email delivery logs.

**Authentication:** Required

#### Query Parameters

| Parameter | Type | Description |
|---|---|---|
| `status` | string | Filter: `queued` \| `sent` \| `failed` \| `retrying` |
| `startDate` | ISO date | Start of date range |
| `endDate` | ISO date | End of date range |
| `limit` | integer | Max results (default: 100) |
| `skip` | integer | Offset for pagination |

#### Response 200

```json
{
  "success": true,
  "data": [ /* EmailLog objects */ ],
  "total": 500
}
```

---

### GET /v1/email/logs/:requestId

Get a single email log by its `requestId`.

**Authentication:** Required

#### Response 200

```json
{
  "success": true,
  "data": {
    "requestId": "550e8400-...",
    "tenantId": "tenant_abc",
    "to": ["john@example.com"],
    "from": "noreply@myapp.com",
    "template": "ORDER_CONFIRMED",
    "subject": "Your order #ORD-2026-001 has been confirmed!",
    "status": "sent",
    "messageId": "<msg-id@smtp.server>",
    "idempotencyKey": "order-ORD-2026-001-confirm",
    "sentAt": "2026-06-02T10:00:02.000Z",
    "createdAt": "2026-06-02T10:00:00.000Z"
  }
}
```

---

### GET /v1/email/health

Verify SMTP connection health by sending a `verify()` probe.

**Authentication:** Required

#### Response 200

```json
{ "success": true, "ready": true }
```

---

## Health Endpoints

### GET /v1/health

Health check — MongoDB ping + heap memory ≤ 512 MB.

**Authentication:** None (public)

#### Response 200

```json
{
  "status": "ok",
  "info": {
    "mongodb": { "status": "up" },
    "memory_heap": { "status": "up" }
  },
  "error": {},
  "details": {
    "mongodb": { "status": "up" },
    "memory_heap": { "status": "up" }
  }
}
```

---

### GET /v1/health/detailed

Detailed health — MongoDB ping + heap ≤ 512 MB + RSS ≤ 1 GB.

**Authentication:** None

---

### GET /v1/health/live

Kubernetes liveness probe — always returns 200 while the process is running.

**Authentication:** None

#### Response 200

```json
{ "status": "ok", "timestamp": "2026-06-02T10:00:00.000Z" }
```

---

## SMS Status Values

| Status | Description |
|---|---|
| `QUEUED` | Accepted but not yet dispatched |
| `SENDING` | Dispatch in progress |
| `SENT` | Accepted by provider |
| `DELIVERED` | DLR confirmation received |
| `FAILED` | Permanent failure |
| `UNDELIVERED` | Provider could not deliver |
| `REJECTED` | Provider rejected the message |
| `RETRYING` | Scheduled for retry |
| `UNKNOWN` | Status not determinable |
| `PURGED` | PII erased by GDPR purge |

## Email Status Values

| Status | Description |
|---|---|
| `queued` | Logged but not yet sent |
| `sent` | Accepted by SMTP server |
| `failed` | Permanent SMTP failure |
| `retrying` | Scheduled for retry |
