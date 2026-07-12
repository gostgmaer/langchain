# Sales And Provisioning Integration Guide

This guide explains how to provision EasyDev Communication AI accounts safely.

## Choose The Right Integration Path

### Recommended path: integrate through the gateway

Use this when your sales or checkout flow is part of the EasyDev stack.

Why it is preferred:

- payment verification and provisioning stay in one place
- IAM user creation and grant assignment are completed automatically
- AI Communication business records are linked to IAM in the same orchestration flow
- browser clients never need the product `X-Api-Key`

### Advanced path: call the product backend directly

Use this only when you are integrating from a trusted backend service and you also own the IAM linkage step.

Why it is advanced:

- `POST /api/v1/onboarding/create-account` creates only local product records
- it does not create the shared IAM user by itself
- you must separately create or resolve the IAM user and then call `POST /api/v1/onboarding/link-iam-user`

## Recommended Local Ports

| Service | Port |
|---|---|
| gateway | `3500` |
| AI Communication backend | `3001` |
| AI Communication frontend | `3002` |
| IAM | `3100` |
| payment service | `3200` |

## Path 1: Gateway-First Integration

### Public checkout sequence

```http
GET  /api/payments/methods
POST /api/payments/initiate
POST /api/payments/verify
```

The verify request is the provisioning trigger.

### Verify request example

```http
POST /api/payments/verify
Content-Type: application/json
x-tenant-id: easydev

{
  "provider": "RAZORPAY",
  "productId": "easydev-ai-communication",
  "token": "provider-order-or-reference",
  "paymentId": "pay_123",
  "signature": "provider_signature",
  "planKey": "growth",
  "name": "Jane Buyer",
  "email": "buyer@example.com",
  "businessName": "Buyer Co",
  "externalId": "crm_123"
}
```

Accepted `planKey` values at the gateway level:

- `starter`
- `growth`
- `payg`
- aliases such as `free`, `pro`, `enterprise`, `pay-as-you-go`

### What happens after verify succeeds

1. payment is verified with `payment-microservice`
2. AI Communication local account is created
3. shared IAM user is created or reused
4. IAM user is linked back to the AI Communication business
5. the response can include a product login or launch path from the gateway context

## Path 2: Direct Product Backend Integration

Use the AI Communication backend only from a trusted server with the shared API key.

### Authentication header

```http
X-Api-Key: <SALES_API_KEY>
```

This value must match:

- AI Communication backend `SALES_API_KEY`
- gateway `COMMUNICATION_API_KEY`

### Create local product account

```http
POST /api/v1/onboarding/create-account
X-Api-Key: <SALES_API_KEY>
Content-Type: application/json

{
  "name": "Jane Buyer",
  "email": "buyer@example.com",
  "businessName": "Buyer Co",
  "plan": "growth",
  "paymentId": "pay_123",
  "externalId": "crm_123"
}
```

Accepted `plan` values:

- canonical: `starter`, `growth`, `payg`
- accepted aliases: `free`, `pro`, `enterprise`, `business`, `pay-as-you-go`

Successful response from the product backend is a raw object, not the gateway envelope:

```json
{
  "userId": "...",
  "businessId": "...",
  "email": "buyer@example.com",
  "iamUserId": null,
  "loginUrl": "http://localhost:3000/login",
  "magicToken": null
}
```

Important consequences:

- `iamUserId` is `null` until you link the shared IAM user
- `loginUrl` points to the EasyDev portal login
- there is no product-side magic link in the current implementation

### Link the IAM user afterwards

After you create or resolve the IAM user, call:

```http
POST /api/v1/onboarding/link-iam-user
X-Api-Key: <SALES_API_KEY>
Content-Type: application/json

{
  "businessId": "<business-id>",
  "iamUserId": "<iam-user-id>"
}
```

Successful response:

```json
{
  "businessId": "<business-id>",
  "iamUserId": "<iam-user-id>"
}
```

If you skip this step, the user will not be able to authenticate into the product through IAM-backed flows.

## Onboarding Status Endpoint

Once the user is authenticated with IAM or has a valid product session cookie, you can inspect onboarding progress:

```http
GET /api/v1/onboarding/status
Authorization: Bearer <iam-access-token>
```

This endpoint is not protected by `X-Api-Key`; it is a normal authenticated product route.

## SSO Launch After Provisioning

Product entry is usually initiated from the gateway, not directly from the product backend:

1. user signs in to EasyDev through IAM
2. EasyDev calls `GET /api/communication/launch`
3. gateway calls `POST /api/v1/iam/sso/generate`
4. browser opens product `/sso?token=...&appId=...`
5. product frontend calls `POST /api/v1/auth/sso/exchange`
6. product backend sets the `ea_comm_session` cookie

## What To Store In Your Sales System

At minimum keep:

- original customer email
- external CRM or billing id
- payment reference id
- returned `businessId`
- linked `iamUserId`

That makes support, re-provisioning, and entitlement recovery much easier.

## Common Integration Mistakes

- Sending `planKey` to the direct product endpoint instead of `plan`.
- Calling direct onboarding from browser code and exposing `X-Api-Key`.
- Assuming direct onboarding creates the IAM user automatically.
- Forgetting to link `iamUserId` after direct onboarding.
- Using the raw product response shape when calling the gateway wrapper, or vice versa.

## Minimum Security Checklist

- keep `X-Api-Key` in server-side code only
- use idempotency on your sales side to avoid duplicate provisioning attempts
- record `businessId` and linked IAM identity for recovery workflows
- verify shared secrets match before debugging application code
