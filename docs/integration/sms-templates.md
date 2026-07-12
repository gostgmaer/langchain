# SMS Templates

SMS templates are stored in MongoDB and resolved by `templateCode`. Variable substitution uses `{{variable}}` syntax. Each message must stay under **160 characters** for single-part delivery (GSM-7 charset). Unicode messages have a 70-character limit per segment.

---

## How to Use SMS Templates

### Method 1 — Inline message

```json
{
  "to": "+919876543210",
  "message": "Your OTP is 847291. Valid for 10 minutes.",
  "messageType": "OTP"
}
```

### Method 2 — Template code with variables

```json
{
  "to": "+919876543210",
  "templateCode": "OTP_VERIFICATION",
  "variables": {
    "otp": "847291",
    "expiryMinutes": "10"
  },
  "messageType": "OTP"
}
```

### Method 3 — MongoDB ObjectId

```json
{
  "to": "+919876543210",
  "templateId": "6650a1f2e4b0c23d4f8a91bc",
  "variables": { "otp": "847291" },
  "messageType": "OTP"
}
```

---

## Message Types

| Type | Use case | DND bypass |
|---|---|---|
| `TRANSACTIONAL` | Order updates, account alerts | Generally allowed |
| `OTP` | One-time passwords | Always allowed |
| `PROMOTIONAL` | Marketing, offers | Blocked during DND hours |
| `FLASH` | Urgent alerts | Provider-specific |

---

## India TRAI Compliance (DLT)

For India, every promotional and transactional message must be pre-approved on the DLT (Distributed Ledger Technology) platform. Pass the approved identifiers in your request:

```json
{
  "to": "+919876543210",
  "templateCode": "ORDER_SHIPPED",
  "variables": { "orderId": "ORD-001" },
  "messageType": "TRANSACTIONAL",
  "dltTemplateId": "1234567890123456789",
  "dltEntityId": "9876543210987654321"
}
```

---

## Recommended Built-in Template Catalog

These templates should be created in your tenant via `POST /v1/sms/templates`.

### OTP / Auth

| Code | Body (under 160 chars) | Variables |
|---|---|---|
| `OTP_VERIFICATION` | `Your verification code is {{otp}}. Valid for {{expiryMinutes}} min. Do not share with anyone.` | `otp`, `expiryMinutes` |
| `OTP_LOGIN` | `{{otp}} is your {{appName}} login OTP. Expires in {{expiryMinutes}} minutes.` | `otp`, `appName`, `expiryMinutes` |
| `OTP_TRANSACTION` | `{{otp}} is your OTP for transaction of Rs {{amount}}. Valid for {{expiryMinutes}} min.` | `otp`, `amount`, `expiryMinutes` |
| `MAGIC_LINK_SMS` | `Click to sign in to {{appName}}: {{magicLink}} . Expires in 15 min.` | `appName`, `magicLink` |

### Orders

| Code | Body | Variables |
|---|---|---|
| `ORDER_CONFIRMED_SMS` | `Hi {{name}}, your order #{{orderId}} is confirmed! Total: Rs {{amount}}. Track at {{trackUrl}}` | `name`, `orderId`, `amount`, `trackUrl` |
| `ORDER_SHIPPED_SMS` | `Hi {{name}}, order #{{orderId}} shipped via {{carrier}}. Track: {{trackingUrl}}` | `name`, `orderId`, `carrier`, `trackingUrl` |
| `ORDER_DELIVERED_SMS` | `Hi {{name}}, your order #{{orderId}} has been delivered. Enjoy! Reply HELP for support.` | `name`, `orderId` |
| `ORDER_CANCELLED_SMS` | `Hi {{name}}, order #{{orderId}} has been cancelled. Refund (if any) in 3-5 days.` | `name`, `orderId` |

### Payments

| Code | Body | Variables |
|---|---|---|
| `PAYMENT_SUCCESS_SMS` | `Rs {{amount}} payment received. TxnID: {{txnId}}. Thank you for using {{appName}}!` | `amount`, `txnId`, `appName` |
| `PAYMENT_FAILED_SMS` | `Hi {{name}}, payment of Rs {{amount}} failed. Please retry or contact support.` | `name`, `amount` |
| `PAYMENT_REMINDER_SMS` | `Hi {{name}}, your invoice {{invoiceNo}} of Rs {{amount}} is due on {{dueDate}}.` | `name`, `invoiceNo`, `amount`, `dueDate` |

### Subscriptions

| Code | Body | Variables |
|---|---|---|
| `SUBSCRIPTION_STARTED_SMS` | `Hi {{name}}, your {{planName}} subscription starts today. Welcome aboard!` | `name`, `planName` |
| `SUBSCRIPTION_EXPIRY_REMINDER` | `Hi {{name}}, your {{planName}} plan expires on {{expiryDate}}. Renew at {{renewUrl}}` | `name`, `planName`, `expiryDate`, `renewUrl` |
| `SUBSCRIPTION_CANCELLED_SMS` | `Hi {{name}}, your {{planName}} subscription has been cancelled. Access ends {{endDate}}.` | `name`, `planName`, `endDate` |

### Account

| Code | Body | Variables |
|---|---|---|
| `WELCOME_SMS` | `Welcome to {{appName}}, {{name}}! Your account is ready. Login: {{loginUrl}}` | `appName`, `name`, `loginUrl` |
| `PASSWORD_RESET_SMS` | `Reset your {{appName}} password: {{resetLink}} . Link expires in 30 min.` | `appName`, `resetLink` |
| `ACCOUNT_LOCKED_SMS` | `Your {{appName}} account has been temporarily locked. Contact support to unlock.` | `appName` |

### Promotions (PROMOTIONAL type)

| Code | Body | Variables |
|---|---|---|
| `FLASH_SALE` | `FLASH SALE! {{discountPercent}}% off on {{appName}} for next {{hours}} hrs. Shop: {{shopUrl}}` | `discountPercent`, `appName`, `hours`, `shopUrl` |
| `BIRTHDAY_OFFER` | `Happy Birthday {{name}}! Enjoy {{discount}}% off your next order. Use code: {{couponCode}}` | `name`, `discount`, `couponCode` |

---

## Creating Templates via API

```bash
curl -X POST http://localhost:4000/v1/sms/templates \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -H "x-tenant-id: tenant_abc" \
  -d '{
    "code": "OTP_VERIFICATION",
    "name": "OTP Verification",
    "body": "Your verification code is {{otp}}. Valid for {{expiryMinutes}} min. Do not share with anyone.",
    "type": "OTP",
    "variables": ["otp", "expiryMinutes"]
  }'
```

---

## Importing Templates in Bulk

```bash
curl -X POST http://localhost:4000/v1/sms/templates/import \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -H "x-tenant-id: tenant_abc" \
  -d '[
    {
      "code": "ORDER_SHIPPED_SMS",
      "name": "Order Shipped",
      "body": "Hi {{name}}, order #{{orderId}} shipped via {{carrier}}. Track: {{trackingUrl}}",
      "type": "TRANSACTIONAL",
      "variables": ["name", "orderId", "carrier", "trackingUrl"]
    },
    {
      "code": "OTP_VERIFICATION",
      "name": "OTP Verification",
      "body": "Your code is {{otp}}. Valid {{expiryMinutes}} min. Do not share.",
      "type": "OTP",
      "variables": ["otp", "expiryMinutes"]
    }
  ]'
```

---

## Character Count Reference

| Encoding | Single SMS | Multi-part |
|---|---|---|
| GSM-7 (ASCII + basic) | 160 chars | 153 chars per segment |
| Unicode (emojis, regional scripts) | 70 chars | 67 chars per segment |

Use `unicode: true` in the request body for non-Latin scripts (Hindi, Arabic, Chinese, etc.).

---

## Provider Character Limits

Most providers support up to 1600 characters (10 segments), but billing is per segment. Keep transactional messages under 160 characters to minimise cost.
