# Notification Service — Integration Guide

> **This document supersedes `docs/integration-guide.md` for new integrations.**
> See also: [Template Catalog](./template-catalog.md), [Event Contracts](./event-contracts.md), [Webhook Guide](./webhook-guide.md).

---

## Service Overview

The Notification Service handles email and SMS delivery with async queuing (BullMQ), Kafka event streaming, idempotency, rate limiting, and circuit breaking. It does **not** implement Push or In-App channels at this time.

**Base URL (local):** `http://localhost:4000`
**Auth:** `Authorization: Bearer <API_KEY>` or `x-api-key: <API_KEY>`

---

## Required Headers

| Header | Required for | Notes |
|---|---|---|
| `Authorization` | All requests | `Bearer <key>` or use `x-api-key` |
| `x-tenant-id` | Email + SMS | Tenant isolation |
| `x-idempotency-key` | Email sends | Dedup via Redis; must be unique per logical operation |
| `x-app-name` | Templates with `requireApplicationName` | Used as `applicationName` in template context |
| `x-app-url` | Templates with `requireAppUrl` | Used as `appUrl`; CTA base URL |
| `x-path` | Templates with `requireCtaPath` | Appended to `appUrl` to form CTA: `appUrl + ctaPath` |

---

## Quick Start: Send Your First Email

```bash
curl -X POST http://localhost:4000/v1/email/send \
  -H "Authorization: Bearer $NOTIFICATION_API_KEY" \
  -H "Content-Type: application/json" \
  -H "x-tenant-id: tenant_abc" \
  -H "x-app-name: MyApp" \
  -H "x-app-url: https://myapp.com" \
  -H "x-path: /dashboard" \
  -H "x-idempotency-key: welcome-usr_123" \
  -d '{
    "to": "john@example.com",
    "template": "USER_WELCOME",
    "data": {
      "username": "John Doe",
      "email": "john@example.com",
      "verifyLink": "https://myapp.com/verify?token=abc123"
    }
  }'
```

Success response (async, queued):

```json
{ "success": true, "messageId": "msg_xxxx", "status": "queued" }
```

---

## SDK Examples

### Node.js (fetch)

```javascript
const NOTIFICATION_URL = process.env.NOTIFICATION_SERVICE_URL;
const API_KEY = process.env.NOTIFICATION_API_KEY;

async function sendWelcomeEmail({ to, username, email, verifyLink, tenantId }) {
  const response = await fetch(`${NOTIFICATION_URL}/v1/email/send`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${API_KEY}`,
      'Content-Type': 'application/json',
      'x-tenant-id': tenantId,
      'x-app-name': process.env.APP_NAME,
      'x-app-url': process.env.APP_URL,
      'x-path': '/dashboard',
      'x-idempotency-key': `welcome-${email}-${Date.now()}`,
    },
    body: JSON.stringify({
      to,
      template: 'USER_WELCOME',
      data: { username, email, verifyLink },
    }),
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(`Notification failed: ${err.message || response.statusText}`);
  }
  return response.json();
}
```

### TypeScript / axios

```typescript
import axios from 'axios';

interface SendEmailOptions {
  to: string;
  template: string;
  data: Record<string, string | number | boolean>;
  tenantId: string;
  idempotencyKey: string;
  appName?: string;
  appUrl?: string;
  ctaPath?: string;
}

const notificationClient = axios.create({
  baseURL: process.env.NOTIFICATION_SERVICE_URL,
  headers: { Authorization: `Bearer ${process.env.NOTIFICATION_API_KEY}` },
});

export async function sendEmail(opts: SendEmailOptions): Promise<void> {
  const headers: Record<string, string> = {
    'x-tenant-id': opts.tenantId,
    'x-idempotency-key': opts.idempotencyKey,
  };
  if (opts.appName) headers['x-app-name'] = opts.appName;
  if (opts.appUrl) headers['x-app-url'] = opts.appUrl;
  if (opts.ctaPath) headers['x-path'] = opts.ctaPath;

  await notificationClient.post('/v1/email/send', {
    to: opts.to,
    template: opts.template,
    data: opts.data,
  }, { headers });
}
```

### NestJS Injectable Service

```typescript
import { Injectable, Logger } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { HttpService } from '@nestjs/axios';
import { firstValueFrom } from 'rxjs';

@Injectable()
export class NotificationService {
  private readonly logger = new Logger(NotificationService.name);
  private readonly baseUrl: string;
  private readonly apiKey: string;

  constructor(
    private readonly http: HttpService,
    private readonly config: ConfigService,
  ) {
    this.baseUrl = this.config.getOrThrow<string>('NOTIFICATION_SERVICE_URL');
    this.apiKey = this.config.getOrThrow<string>('NOTIFICATION_API_KEY');
  }

  async sendEmail(opts: {
    to: string;
    template: string;
    data: Record<string, unknown>;
    tenantId: string;
    idempotencyKey: string;
    appName?: string;
    appUrl?: string;
    ctaPath?: string;
  }): Promise<void> {
    const headers: Record<string, string> = {
      Authorization: `Bearer ${this.apiKey}`,
      'x-tenant-id': opts.tenantId,
      'x-idempotency-key': opts.idempotencyKey,
      ...(opts.appName && { 'x-app-name': opts.appName }),
      ...(opts.appUrl && { 'x-app-url': opts.appUrl }),
      ...(opts.ctaPath && { 'x-path': opts.ctaPath }),
    };
    try {
      await firstValueFrom(
        this.http.post(`${this.baseUrl}/v1/email/send`, {
          to: opts.to,
          template: opts.template,
          data: opts.data,
        }, { headers }),
      );
    } catch (err) {
      this.logger.error('Failed to dispatch email notification', err);
      // Non-blocking: swallow to avoid breaking the calling flow
    }
  }
}
```

### Express.js

```javascript
const axios = require('axios');

const notification = axios.create({
  baseURL: process.env.NOTIFICATION_SERVICE_URL,
  headers: { Authorization: `Bearer ${process.env.NOTIFICATION_API_KEY}` },
});

// Non-blocking fire-and-forget helper
function dispatchEmail({ to, template, data, tenantId, idempotencyKey, appName, appUrl, ctaPath }) {
  const headers = { 'x-tenant-id': tenantId, 'x-idempotency-key': idempotencyKey };
  if (appName) headers['x-app-name'] = appName;
  if (appUrl) headers['x-app-url'] = appUrl;
  if (ctaPath) headers['x-path'] = ctaPath;

  notification.post('/v1/email/send', { to, template, data }, { headers }).catch(err => {
    console.error('[notification] failed to send email', err?.response?.data || err.message);
  });
}

// Usage in a route
router.post('/register', async (req, res) => {
  const user = await createUser(req.body);
  dispatchEmail({
    to: user.email,
    template: 'USER_WELCOME',
    data: { username: user.name, email: user.email, verifyLink: user.verifyUrl },
    tenantId: req.headers['x-tenant-id'],
    idempotencyKey: `welcome-${user.id}`,
    appName: 'MyApp',
    appUrl: process.env.APP_URL,
    ctaPath: '/dashboard',
  });
  res.status(201).json({ user });
});
```

### Python (httpx)

```python
import httpx
import os
from typing import Optional

NOTIFICATION_URL = os.environ["NOTIFICATION_SERVICE_URL"]
NOTIFICATION_API_KEY = os.environ["NOTIFICATION_API_KEY"]

def send_email(
    to: str,
    template: str,
    data: dict,
    tenant_id: str,
    idempotency_key: str,
    app_name: Optional[str] = None,
    app_url: Optional[str] = None,
    cta_path: Optional[str] = None,
) -> None:
    headers = {
        "Authorization": f"Bearer {NOTIFICATION_API_KEY}",
        "x-tenant-id": tenant_id,
        "x-idempotency-key": idempotency_key,
    }
    if app_name:
        headers["x-app-name"] = app_name
    if app_url:
        headers["x-app-url"] = app_url
    if cta_path:
        headers["x-path"] = cta_path

    with httpx.Client() as client:
        resp = client.post(
            f"{NOTIFICATION_URL}/v1/email/send",
            json={"to": to, "template": template, "data": data},
            headers=headers,
        )
        resp.raise_for_status()
```

### Go

```go
package notification

import (
    "bytes"
    "encoding/json"
    "fmt"
    "net/http"
    "os"
)

type EmailPayload struct {
    To       string         `json:"to"`
    Template string         `json:"template"`
    Data     map[string]any `json:"data"`
}

func SendEmail(to, template string, data map[string]any, tenantID, idempotencyKey string) error {
    body, _ := json.Marshal(EmailPayload{To: to, Template: template, Data: data})
    req, err := http.NewRequest(http.MethodPost,
        os.Getenv("NOTIFICATION_SERVICE_URL")+"/v1/email/send",
        bytes.NewBuffer(body),
    )
    if err != nil {
        return fmt.Errorf("building request: %w", err)
    }
    req.Header.Set("Content-Type", "application/json")
    req.Header.Set("Authorization", "Bearer "+os.Getenv("NOTIFICATION_API_KEY"))
    req.Header.Set("x-tenant-id", tenantID)
    req.Header.Set("x-idempotency-key", idempotencyKey)

    resp, err := http.DefaultClient.Do(req)
    if err != nil {
        return fmt.Errorf("sending request: %w", err)
    }
    defer resp.Body.Close()
    if resp.StatusCode >= 300 {
        return fmt.Errorf("notification service returned %d", resp.StatusCode)
    }
    return nil
}
```

### Vue 3 (Composition API)

```typescript
// composables/useNotification.ts
import { ref } from 'vue';

export function useEmailSignup() {
  const loading = ref(false);
  const error = ref<string | null>(null);

  async function sendWelcome(payload: {
    to: string;
    username: string;
    verifyLink: string;
  }) {
    loading.value = true;
    error.value = null;
    try {
      // All notification calls go through your BFF/gateway, never directly to the service
      const res = await fetch('/api/notifications/welcome', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (!res.ok) throw new Error((await res.json()).message);
    } catch (e: any) {
      error.value = e.message;
    } finally {
      loading.value = false;
    }
  }

  return { loading, error, sendWelcome };
}
```

> Never call the Notification Service directly from a browser client. Route all calls through your backend gateway and keep `NOTIFICATION_API_KEY` server-side only.

### Angular

```typescript
// notification.service.ts
import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable, catchError, of } from 'rxjs';
import { environment } from '../environments/environment';

interface NotificationResult {
  success: boolean;
  messageId?: string;
}

@Injectable({ providedIn: 'root' })
export class NotificationGatewayService {
  private readonly apiUrl = environment.apiUrl;

  constructor(private http: HttpClient) {}

  sendWelcomeEmail(to: string, username: string, verifyLink: string): Observable<NotificationResult> {
    // Route through your BFF — do not expose the notification API key on the client
    return this.http.post<NotificationResult>(
      `${this.apiUrl}/notifications/welcome`,
      { to, username, verifyLink },
    ).pipe(
      catchError(() => of({ success: false })),
    );
  }
}
```

---

## Sending an OTP (SMS)

```bash
# Step 1: send OTP
curl -X POST http://localhost:4000/v1/sms/otp/send \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -H "x-tenant-id: tenant_abc" \
  -d '{ "to": "+919876543210", "otpLength": 6, "expiresInMinutes": 10 }'

# Step 2: verify OTP
curl -X POST http://localhost:4000/v1/sms/otp/verify \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -H "x-tenant-id: tenant_abc" \
  -d '{ "to": "+919876543210", "otp": "847291" }'
```

---

## Async vs Sync Delivery

| Endpoint | Mode | Response | Use when |
|---|---|---|---|
| `POST /v1/email/send` | Async (queued) | `202 Accepted` | Default — non-blocking |
| `POST /v1/email/send-sync` | Synchronous | `200 OK` | Must confirm delivery before proceeding |

Prefer async in web request handlers. Use sync only when the result is needed immediately (e.g., OTP validation flows).

---

## Idempotency

Pass a unique `x-idempotency-key` header on every email send. The service deduplicates on this key via Redis for 24 hours. Repeating the same key within the window returns the original result without re-sending.

**Recommended key format:** `{operation}-{userId or orderId}-{date}`

```
welcome-usr_7f3k2-20260602
order-confirm-ORD-2026-001
payment-TXN-ABC-123456
```

---

## Kafka Integration

Enable with `ENABLE_KAFKA=true`. Topics:

| Direction | Topic | Purpose |
|---|---|---|
| Consumer | `email.notification.send` | Receive email requests from other services |
| Consumer | `sms.notification.send` | Receive SMS requests from other services |
| Producer | `email.notification.delivered` | Emit on delivery |
| Producer | `email.notification.failed` | Emit on failure |
| Producer | `sms.notification.delivered` | Emit on delivery |
| Producer | `sms.notification.failed` | Emit on failure |

Full schema: [event-contracts.md](./event-contracts.md)

---

## Error Handling

| HTTP Status | Meaning | Action |
|---|---|---|
| `400 Bad Request` | Missing required data fields or headers | Check template schema in [template-catalog.md](./template-catalog.md) |
| `401 Unauthorized` | Invalid or missing API key | Verify `NOTIFICATION_API_KEY` |
| `409 Conflict` | Duplicate idempotency key | Already processed — safe to ignore |
| `429 Too Many Requests` | Rate limit exceeded (100/min) | Implement exponential backoff |
| `503 Service Unavailable` | Circuit breaker OPEN | Wait 30 seconds and retry |

---

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `PORT` | No | `4000` | HTTP server port |
| `API_KEY` | Yes (prod) | — | Shared secret for all callers |
| `MONGODB_URI` | Yes | — | MongoDB connection string |
| `REDIS_URL` | Yes | `redis://localhost:6379` | Redis for idempotency + rate limiting |
| `ENABLE_BULL` | No | `false` | Enable BullMQ async queues |
| `ENABLE_KAFKA` | No | `false` | Enable Kafka consumer/producer |
| `KAFKA_BROKERS` | If Kafka | — | Comma-separated broker list |
| `SMTP_HOST` | Email | — | SMTP server hostname |
| `SMTP_PORT` | Email | `587` | SMTP port |
| `SMTP_USER` | Email | — | SMTP username |
| `SMTP_PASS` | Email | — | SMTP password |
| `EMAIL_FROM` | Email | — | Default sender address |
| `SMS_DEFAULT_PROVIDER` | SMS | `twilio` | Active SMS provider |
| `TWILIO_ACCOUNT_SID` | SMS/Twilio | — | Twilio Account SID |
| `TWILIO_AUTH_TOKEN` | SMS/Twilio | — | Twilio Auth Token |
| `TWILIO_PHONE_NUMBER` | SMS/Twilio | — | Twilio sender number |

---

## Further Reading

- [Template Catalog](./template-catalog.md) — all 378 email templates with required fields
- [Email Templates](./email-templates.md) — HTML layout standards and dark mode
- [SMS Templates](./sms-templates.md) — SMS template creation and DLT compliance
- [Event Contracts](./event-contracts.md) — Kafka topic JSON schemas
- [Webhook Guide](./webhook-guide.md) — SMS delivery report webhooks
- [Push Notifications](./push-templates.md) — proposed future push channel
- [In-App Notifications](./inapp-templates.md) — proposed future in-app channel
- [Integration Audit](./integration-audit.md) — coverage gaps and recommendations
- [Postman Collection](./postman_collection.json) — import into Postman
- [Bruno Collection](./bruno/) — import into Bruno API client
