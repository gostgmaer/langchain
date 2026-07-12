# Kafka Event Contracts

Kafka integration is optional. Enable with `ENABLE_KAFKA=true`.

The service acts as a **hybrid NestJS microservice** — it simultaneously serves HTTP and consumes Kafka messages.

---

## Configuration

```env
ENABLE_KAFKA=true
KAFKA_BROKERS=localhost:9092
KAFKA_CLIENT_ID=notification-service
KAFKA_GROUP_ID=notification-service-group

# Optional SASL/SSL
# KAFKA_SASL_MECHANISM=plain
# KAFKA_SASL_USERNAME=
# KAFKA_SASL_PASSWORD=
```

Multiple brokers: `KAFKA_BROKERS=broker1:9092,broker2:9092`

---

## Consumer Topics

The notification service **subscribes** to these topics.

---

### `email.notification.send`

Trigger an email send via a Kafka event.

**JSON Schema:**

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "EmailNotificationSendEvent",
  "type": "object",
  "required": ["to"],
  "properties": {
    "tenantId": {
      "type": "string",
      "description": "Tenant identifier (maps to x-tenant-id header)",
      "example": "tenant_abc"
    },
    "appName": {
      "type": "string",
      "description": "Application name shown in email (maps to x-app-name header)",
      "example": "MyApp"
    },
    "appUrl": {
      "type": "string",
      "format": "uri",
      "description": "Base URL for CTA buttons (maps to x-app-url header)",
      "example": "https://myapp.com"
    },
    "ctaPath": {
      "type": "string",
      "description": "CTA path appended to appUrl (maps to x-path header)",
      "example": "/dashboard"
    },
    "idempotencyKey": {
      "type": "string",
      "description": "Prevents duplicate sends (maps to x-idempotency-key header)",
      "example": "welcome-usr_123"
    },
    "to": {
      "type": "string",
      "format": "email",
      "description": "Recipient email address",
      "example": "user@example.com"
    },
    "from": {
      "type": "string",
      "format": "email",
      "description": "Optional sender override"
    },
    "fromName": {
      "type": "string",
      "description": "Optional sender display name"
    },
    "subject": {
      "type": "string",
      "description": "Optional subject override (templates auto-generate subjects)"
    },
    "template": {
      "type": "string",
      "description": "Named template identifier (one of 378 registered templates)",
      "example": "USER_WELCOME"
    },
    "templateId": {
      "type": "string",
      "description": "MongoDB ObjectId of a stored custom template"
    },
    "data": {
      "type": "object",
      "description": "Template variables. Required fields depend on the chosen template.",
      "additionalProperties": true,
      "example": { "username": "John Doe", "email": "user@example.com" }
    },
    "cc": {
      "type": "array",
      "items": { "type": "string", "format": "email" }
    },
    "bcc": {
      "type": "array",
      "items": { "type": "string", "format": "email" }
    },
    "metadata": {
      "type": "object",
      "description": "Arbitrary key-value pairs stored with the log (not sent in email)",
      "additionalProperties": true
    }
  }
}
```

**Minimal example:**

```json
{
  "tenantId": "tenant_abc",
  "appName": "MyApp",
  "appUrl": "https://myapp.com",
  "ctaPath": "/dashboard",
  "idempotencyKey": "welcome-usr_123",
  "to": "user@example.com",
  "template": "USER_WELCOME",
  "data": {
    "username": "John Doe",
    "email": "user@example.com",
    "verifyLink": "https://myapp.com/verify?token=abc123"
  }
}
```

**Order confirmation example:**

```json
{
  "tenantId": "tenant_abc",
  "appName": "MyShop",
  "appUrl": "https://myshop.com",
  "ctaPath": "/orders/ORD-2026-001",
  "idempotencyKey": "order-confirm-ORD-2026-001",
  "to": "customer@example.com",
  "template": "ORDER_CONFIRMED",
  "data": {
    "username": "Jane Doe",
    "orderId": "ORD-2026-001",
    "totalAmount": "1499.00",
    "estimatedDelivery": "2026-04-25T00:00:00.000Z"
  }
}
```

---

### `sms.notification.send`

Trigger an SMS send via a Kafka event.

**JSON Schema:**

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "SmsNotificationSendEvent",
  "type": "object",
  "required": ["to"],
  "properties": {
    "tenantId": {
      "type": "string",
      "description": "Tenant identifier",
      "example": "tenant_abc"
    },
    "to": {
      "type": "string",
      "description": "Recipient phone number in E.164 format",
      "pattern": "^\\+[1-9]\\d{1,14}$",
      "example": "+919876543210"
    },
    "from": {
      "type": "string",
      "description": "Sender ID or number"
    },
    "message": {
      "type": "string",
      "maxLength": 1600,
      "description": "Raw message body (required if no templateCode/templateId)"
    },
    "templateId": {
      "type": "string",
      "description": "MongoDB ObjectId of the SMS template"
    },
    "templateCode": {
      "type": "string",
      "description": "Template code for variable substitution",
      "example": "OTP_VERIFICATION"
    },
    "templateName": {
      "type": "string",
      "description": "Human-readable template name"
    },
    "variables": {
      "type": "object",
      "description": "Variable substitutions for the template",
      "additionalProperties": { "type": "string" },
      "example": { "otp": "847291", "name": "John" }
    },
    "messageType": {
      "type": "string",
      "enum": ["TRANSACTIONAL", "PROMOTIONAL", "OTP", "FLASH"],
      "default": "TRANSACTIONAL"
    },
    "unicode": {
      "type": "boolean",
      "default": false
    },
    "referenceId": {
      "type": "string",
      "description": "Caller reference for idempotency and DLR matching"
    },
    "dltTemplateId": {
      "type": "string",
      "description": "DLT Template ID (India TRAI compliance)"
    },
    "dltEntityId": {
      "type": "string",
      "description": "DLT Entity ID (India TRAI compliance)"
    },
    "metadata": {
      "type": "object",
      "additionalProperties": true
    }
  }
}
```

**OTP example:**

```json
{
  "tenantId": "tenant_abc",
  "to": "+919876543210",
  "templateCode": "OTP_VERIFICATION",
  "variables": { "otp": "847291", "name": "John" },
  "messageType": "OTP",
  "referenceId": "otp-usr_123-20260602"
}
```

---

## Producer Topics

The notification service **publishes** to these topics after processing.

---

### `email.notification.delivered`

Emitted when an email is successfully sent (accepted by SMTP).

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "EmailNotificationDeliveredEvent",
  "type": "object",
  "required": ["requestId", "to", "template", "deliveredAt"],
  "properties": {
    "requestId": { "type": "string", "description": "Internal log entry ID" },
    "idempotencyKey": { "type": "string" },
    "tenantId": { "type": "string" },
    "to": { "type": "string", "format": "email" },
    "template": { "type": "string" },
    "messageId": { "type": "string", "description": "SMTP message ID" },
    "deliveredAt": { "type": "string", "format": "date-time" }
  }
}
```

**Example event:**

```json
{
  "requestId": "6650a1f2e4b0c23d4f8a91bc",
  "idempotencyKey": "welcome-usr_123",
  "tenantId": "tenant_abc",
  "to": "user@example.com",
  "template": "USER_WELCOME",
  "messageId": "<abc123@smtp.example.com>",
  "deliveredAt": "2026-06-02T10:15:00.000Z"
}
```

---

### `email.notification.failed`

Emitted when all retry attempts are exhausted.

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "EmailNotificationFailedEvent",
  "type": "object",
  "required": ["requestId", "to", "template", "error", "failedAt"],
  "properties": {
    "requestId": { "type": "string" },
    "idempotencyKey": { "type": "string" },
    "tenantId": { "type": "string" },
    "to": { "type": "string", "format": "email" },
    "template": { "type": "string" },
    "error": { "type": "string", "description": "Error message from last attempt" },
    "attempts": { "type": "integer", "minimum": 1, "maximum": 3 },
    "failedAt": { "type": "string", "format": "date-time" }
  }
}
```

**Example event:**

```json
{
  "requestId": "6650a1f2e4b0c23d4f8a91bd",
  "idempotencyKey": "welcome-usr_456",
  "tenantId": "tenant_abc",
  "to": "broken@example.com",
  "template": "USER_WELCOME",
  "error": "ECONNREFUSED 587",
  "attempts": 3,
  "failedAt": "2026-06-02T10:17:05.000Z"
}
```

---

### `sms.notification.delivered`

Emitted when an SMS is accepted by the provider.

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "SmsNotificationDeliveredEvent",
  "type": "object",
  "required": ["requestId", "to", "deliveredAt"],
  "properties": {
    "requestId": { "type": "string" },
    "referenceId": { "type": "string" },
    "tenantId": { "type": "string" },
    "to": { "type": "string" },
    "provider": { "type": "string", "example": "twilio" },
    "providerMessageId": { "type": "string" },
    "deliveredAt": { "type": "string", "format": "date-time" }
  }
}
```

---

### `sms.notification.failed`

Emitted when all SMS retry attempts are exhausted.

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "SmsNotificationFailedEvent",
  "type": "object",
  "required": ["requestId", "to", "error", "failedAt"],
  "properties": {
    "requestId": { "type": "string" },
    "referenceId": { "type": "string" },
    "tenantId": { "type": "string" },
    "to": { "type": "string" },
    "provider": { "type": "string" },
    "error": { "type": "string" },
    "attempts": { "type": "integer" },
    "failedAt": { "type": "string", "format": "date-time" }
  }
}
```

---

## Kafka Producer Integration Example

```typescript
// In your producer service (another microservice)
import { ClientKafka } from '@nestjs/microservices';

@Injectable()
export class NotificationProducerService {
  constructor(
    @Inject('NOTIFICATION_SERVICE') private readonly kafka: ClientKafka,
  ) {}

  async sendWelcomeEmail(userId: string, email: string, username: string, verifyLink: string) {
    await this.kafka.emit('email.notification.send', {
      tenantId: 'tenant_abc',
      appName: 'MyApp',
      appUrl: 'https://myapp.com',
      ctaPath: '/dashboard',
      idempotencyKey: `welcome-${userId}`,
      to: email,
      template: 'USER_WELCOME',
      data: { username, email, verifyLink },
    });
  }

  async sendOtpSms(tenantId: string, phone: string, otp: string, referenceId: string) {
    await this.kafka.emit('sms.notification.send', {
      tenantId,
      to: phone,
      templateCode: 'OTP_VERIFICATION',
      variables: { otp },
      messageType: 'OTP',
      referenceId,
    });
  }
}
```

---

## Consuming Delivery Events

```typescript
// In any downstream microservice
@Controller()
export class NotificationEventsController {
  @EventPattern('email.notification.delivered')
  onEmailDelivered(@Payload() event: EmailNotificationDeliveredEvent) {
    this.logger.log(`Email delivered: ${event.to} [${event.template}]`);
    // update order status, audit log, etc.
  }

  @EventPattern('email.notification.failed')
  onEmailFailed(@Payload() event: EmailNotificationFailedEvent) {
    this.logger.error(`Email delivery failed: ${event.to} — ${event.error}`);
    // alert, retry fallback, etc.
  }

  @EventPattern('sms.notification.delivered')
  onSmsDelivered(@Payload() event: SmsNotificationDeliveredEvent) {
    // mark OTP as sent, update delivery record, etc.
  }
}
```
