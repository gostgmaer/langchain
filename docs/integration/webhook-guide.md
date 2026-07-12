# Webhook Guide

The Notification Service accepts incoming delivery report (DLR) callbacks from 19 SMS providers. This document explains how to configure each provider and how signature validation works.

---

## Overview

All webhook endpoints are public (`@Public()` — no API key required) because they are called by external provider servers, not by your application.

Base path:

```
POST /v1/webhooks/{provider}
```

---

## Supported Providers and Signature Headers

| Provider | Endpoint | Signature Header |
|---|---|---|
| Twilio | `/v1/webhooks/twilio` | `x-twilio-signature` |
| Vonage / Nexmo | `/v1/webhooks/vonage` | `x-nexmo-signature` |
| MSG91 | `/v1/webhooks/msg91` | `x-msg91-signature` |
| Fast2SMS | `/v1/webhooks/fast2sms` | `x-fast2sms-signature` |
| TextLocal | `/v1/webhooks/textlocal` | `x-textlocal-hash` |
| Gupshup | `/v1/webhooks/gupshup` | `x-hub-signature-256` |
| Infobip | `/v1/webhooks/infobip` | `x-infobip-signature` |
| Telnyx | `/v1/webhooks/telnyx` | `telnyx-signature-ed25519-signature` |
| D7 Networks | `/v1/webhooks/d7networks` | `x-d7-signature` |
| Sinch | `/v1/webhooks/sinch` | `x-sinch-signature` |
| Plivo | `/v1/webhooks/plivo` | `x-plivo-signature-v2` |
| AWS SNS | `/v1/webhooks/awssns` | `x-amz-sns-message-type` |
| Kaleyra | `/v1/webhooks/kaleyra` | `x-kaleyra-signature` |
| ClickSend | `/v1/webhooks/clicksend` | `x-clicksend-signature` |
| Brevo | `/v1/webhooks/brevo` | `x-brevo-signature` |
| Unifonic | `/v1/webhooks/unifonic` | `x-unifonic-signature` |
| Pinnacle | `/v1/webhooks/pinnacle` | `x-pinnacle-signature` |
| Sarv | `/v1/webhooks/sarv` | `x-sarv-signature` |
| MessageBird | `/v1/webhooks/messagebird` | `messagebird-signature-jwt` |

---

## Provider Setup Instructions

### Twilio

1. In the Twilio Console, go to **Phone Numbers → Manage → Active Numbers**
2. Select your number and set the **Messaging Webhook URL** to:  
   ```
   https://your-domain.com/v1/webhooks/twilio
   ```
3. Set method to **HTTP POST**
4. Copy your **Auth Token** from the Twilio Console
5. Set `TWILIO_AUTH_TOKEN` in the service `.env`

Twilio webhook payload:

```json
{
  "MessageSid": "SMxxxxxxxxxxxxxxxx",
  "MessageStatus": "delivered",
  "To": "+919876543210",
  "From": "+12025550123"
}
```

---

### Vonage (Nexmo)

1. In the Vonage Dashboard, go to **API Settings**
2. Enable **Signed webhooks** and copy the **Signature Secret**
3. Set the **Inbound SMS Webhook URL** to:
   ```
   https://your-domain.com/v1/webhooks/vonage
   ```
4. Set `VONAGE_SIGNATURE_SECRET` in the service `.env`

---

### MSG91

1. In MSG91 Dashboard, go to **API → Webhook**
2. Set webhook URL to:
   ```
   https://your-domain.com/v1/webhooks/msg91
   ```
3. Copy the **Webhook Secret** and set `MSG91_WEBHOOK_SECRET` in `.env`

---

### Infobip

1. In Infobip Portal, go to **Channels → SMS → Advanced Settings**
2. Set **Delivery Report URL** to:
   ```
   https://your-domain.com/v1/webhooks/infobip
   ```
3. Set `INFOBIP_API_KEY` in `.env` for signature validation

---

### AWS SNS

AWS SNS uses a different pattern — it sends a subscription confirmation message first.

1. Create an SNS topic for SMS delivery events
2. Create a subscription with protocol `HTTPS` and endpoint:
   ```
   https://your-domain.com/v1/webhooks/awssns
   ```
3. The service will automatically confirm the subscription by fetching the `SubscribeURL`
4. Subsequent delivery records will arrive as `Notification` messages

AWS SNS payload types: `SubscriptionConfirmation`, `Notification`

---

## Generic DLR Payload Pattern

Most providers send a delivery report with these common fields (names vary by provider):

```json
{
  "messageId": "provider-msg-id",
  "to": "+919876543210",
  "status": "DELIVERED",
  "deliveredAt": "2026-06-02T10:15:00Z",
  "errorCode": null
}
```

The `SmsWebhookService` normalises these into a common schema before updating the SMS log.

---

## Signature Validation Details

Each handler reads its provider-specific header and validates the signature. If validation fails, the handler returns `400 Bad Request` and logs the failure. The DLR is silently dropped — providers will retry based on their own retry policies.

Validation is performed in `SmsWebhookService` using HMAC-SHA256 or provider-specific algorithms. Each provider's webhook secret must be configured in `.env`. Without a matching secret, any incoming DLR body is accepted (permissive fallback for development).

### Enable strict mode in production

Set all provider secret env vars. Example for Twilio + Vonage:

```env
TWILIO_AUTH_TOKEN=your_twilio_auth_token
VONAGE_SIGNATURE_SECRET=your_vonage_signature_secret
```

---

## Health and Testing

### Test a webhook locally

Use `ngrok` or similar to expose your local port:

```bash
ngrok http 4000
```

Then set your ngrok URL as the webhook in the provider dashboard:

```
https://abc123.ngrok.io/v1/webhooks/twilio
```

### Simulate a DLR delivery report (curl)

```bash
# Simulate a Twilio DLR
curl -X POST http://localhost:4000/v1/webhooks/twilio \
  -H "Content-Type: application/json" \
  -H "x-twilio-signature: test-signature" \
  -d '{
    "MessageSid": "SMxxxxxxxxxxxxxxxx",
    "MessageStatus": "delivered",
    "To": "+919876543210",
    "From": "+12025550123"
  }'

# Simulate a generic DLR (mock provider)
curl -X POST http://localhost:4000/v1/webhooks/mock \
  -H "Content-Type: application/json" \
  -d '{
    "referenceId": "my-reference-id",
    "status": "DELIVERED"
  }'
```

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `400 Bad Request` on DLR | Signature validation failure | Check the provider's secret is in `.env` |
| DLR arrives but SMS log not updated | `referenceId` mismatch | Ensure you set `referenceId` when calling `/v1/sms/send` |
| Webhook URL not reachable | No public URL | Use ngrok for local dev |
| AWS SNS subscription stuck at `PendingConfirmation` | Service not accessible to SNS | Ensure `https://` URL is publicly reachable |
| MSG91 DLRs failing in production | IP whitelist required | Add your server IP to MSG91 webhook IP allowlist |
