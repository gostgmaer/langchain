# EasyDev Communication AI Workflow

This document describes the current end-to-end workflow from purchase to active automated messaging.

## 1. Services Involved

| Service | Responsibility |
|---|---|
| `easydev` | marketing site and customer portal |
| `web-agency-backend-api` | gateway, checkout adapter, product provisioning trigger, launch URL generation |
| `payment-microservice` | transactions, subscriptions, invoices, payment methods |
| `multi-tannet-auth-services` | shared identities, grants, SSO |
| `ai automation communication` backend | business, conversations, messages, channels, AI config |
| `ai automation communication` frontend | product dashboard and onboarding UI |

## 2. Recommended Local Port Map

| Service | Port |
|---|---|
| EasyDev portal | `3000` |
| AI Communication backend | `3001` |
| AI Communication frontend | `3002` |
| IAM | `3100` |
| gateway | `3500` |
| payment service | `3200` |

## 3. Purchase And Provisioning Flow

### Step 1: Customer starts checkout

The EasyDev frontend calls the gateway:

```http
GET  /api/payments/methods
POST /api/payments/initiate
```

The payment microservice owns provider-specific checkout details.

### Step 2: Customer completes payment

The EasyDev frontend calls:

```http
POST /api/payments/verify
```

This is the important step. The gateway does three things here:

1. verifies the provider payment through `payment-microservice`
2. provisions the AI Communication business locally through `POST /api/v1/onboarding/create-account`
3. provisions or resolves the shared IAM user and then links that IAM user back with `POST /api/v1/onboarding/link-iam-user`

### Step 3: Product-side local records are created

The AI Communication backend creates, in one transaction:

- `Business`
- `User` local join record
- `ReplyUsage`
- `AiConfig`
- `Onboarding`

At this point the product has local tenant data, but IAM is still the source of truth for user authentication.

## 4. Identity And Access Linking

After local product creation, the gateway continues with shared IAM orchestration:

1. create or reuse the IAM user
2. assign or confirm product access grants
3. link the IAM user to the AI Communication business
4. optionally send gateway-driven product access emails

The important consequence is:

- AI Communication `create-account` alone does not finish the full cross-product onboarding story.
- The gateway is the preferred orchestration layer because it completes both product provisioning and IAM linkage.

## 5. User Sign-In And Product Launch

### Step 1: User signs in to EasyDev

The user authenticates against IAM through the gateway using the EasyDev portal.

### Step 2: User clicks Open App

EasyDev calls:

```http
GET /api/communication/launch
Authorization: Bearer <iam-access-token>
```

The gateway then calls IAM:

```http
POST /api/v1/iam/sso/generate
```

### Step 3: Browser opens product launch URL

The gateway returns a URL like:

```text
http://localhost:3002/sso?token=<sso-token>&appId=<application-id>
```

### Step 4: Product exchanges SSO token for session cookie

The product frontend `/sso` page calls:

```http
POST /api/v1/auth/sso/exchange
```

The backend validates the IAM SSO token and sets the `ea_comm_session` cookie.

### Step 5: Product hydrates current user

The frontend then calls:

```http
GET /api/v1/auth/me
```

and routes the user to the correct in-product page.

## 6. Onboarding Inside The Product

The onboarding progress endpoint is:

```http
GET /api/v1/onboarding/status
```

The status reflects these milestones:

1. at least one channel connected
2. FAQs added
3. auto-reply enabled
4. first message processed

Relevant APIs that move those steps forward:

- `POST /channels`
- `POST /email-accounts`
- `PUT /ai-config`
- `PATCH /business/auto-reply`
- inbound webhooks and worker processing for the first live message

## 7. Channel And Messaging Flow

### Channel setup

The product supports:

- generic channels through `/channels`
- WhatsApp state helpers through `/channels/state`, `/channels/:channel/enable`, `/channels/whatsapp/connect`
- email account management through `/email-accounts/*`
- provider OAuth starts and callbacks for Google, Microsoft, Zoho, and Yahoo email accounts

### Inbound message processing

Inbound messages enter through:

- `POST /webhooks/whatsapp`
- `POST /webhooks/email`

High-level pipeline:

1. verify and normalize inbound payload
2. resolve business and conversation
3. store inbound message
4. enqueue processing job
5. evaluate channel state, plan usage, and feature flags
6. run FAQ rules and AI configuration
7. store outbound message
8. deliver reply through the configured channel provider

## 8. Product APIs Used By The EasyDev Portal

The gateway proxies a subset of product APIs to `/api/customer/*`. The most important ones are:

- `/customer/business`
- `/customer/business/stats`
- `/customer/business/usage`
- `/customer/conversations`
- `/customer/conversations/stats`
- `/customer/messages/stats`
- `/customer/ai-config`
- `/customer/channels`
- `/customer/email-accounts`

This lets the member portal show product summaries without exposing internal service URLs to the browser.

## 9. Failure Points To Expect

### Payment verifies, but provisioning fails

User impact:

- payment succeeded
- product access is not fully ready

What to inspect:

- gateway logs around `POST /api/payments/verify`
- AI Communication onboarding endpoint health
- `COMMUNICATION_API_KEY` and `SALES_API_KEY` match

### Product exists, but launch fails

What to inspect:

- IAM application record and grants
- gateway `GET /api/communication/launch` response
- `IAM_SSO_SECRET` in product backend
- product frontend origin and `FRONTEND_URL`

### User has session in EasyDev, but product says unauthorized

What to inspect:

- `IAM_JWT_SECRET` in product backend
- `ea_comm_session` cookie presence
- whether the linked `iamUserId` exists on the business record

## 10. Local Smoke Test Checklist

1. Start IAM on `3100`.
2. Start payment service on `3200`.
3. Start gateway on `3500`.
4. Start AI Communication backend on `3001`.
5. Start AI Communication frontend on `3002`.
6. Start EasyDev on `3000`.
7. Confirm checkout methods load from the gateway.
8. Confirm payment verify provisions the product.
9. Confirm `GET /api/communication/launch` returns a launch URL.
10. Confirm `/sso` exchange sets `ea_comm_session` and `GET /api/v1/auth/me` succeeds.
