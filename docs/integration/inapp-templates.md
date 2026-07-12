# In-App Notification Templates (Planned)

> **Status: NOT IMPLEMENTED**  
> This document defines the proposed standard for a future In-App Notification channel (web/SPA notification feed). No in-app endpoints exist yet.

---

## Concept

In-app notifications are persistent records stored in the database and surfaced through a REST API or WebSocket feed. Unlike push or email, they appear inside the authenticated product UI and persist until the user dismisses them.

---

## Proposed HTTP Endpoints

```
POST   /v1/inapp/send             — Create a notification for a user
POST   /v1/inapp/send-bulk        — Create for multiple users / a segment
GET    /v1/inapp/:userId          — List notifications (paginated, filter by read/unread)
PATCH  /v1/inapp/:id/read         — Mark single notification as read
PATCH  /v1/inapp/:userId/read-all — Mark all as read
DELETE /v1/inapp/:id              — Dismiss / delete
GET    /v1/inapp/:userId/count    — Unread count (for badge)
```

### WebSocket / SSE (proposed)

```
GET /v1/inapp/stream/:userId — Server-Sent Events stream for real-time delivery
```

---

## Proposed Notification Schema

```typescript
interface InAppNotification {
  id: string;                  // UUID
  tenantId: string;            // Multi-tenant isolation
  userId: string;              // Recipient
  type: InAppNotificationType; // Enum
  title: string;
  body: string;
  icon?: string;               // URL or icon identifier
  actionUrl?: string;          // Deep-link inside the app
  data?: Record<string, unknown>; // Arbitrary extra payload
  read: boolean;
  readAt?: string;             // ISO 8601
  createdAt: string;           // ISO 8601
  expiresAt?: string;          // ISO 8601 — auto-expire support
}

enum InAppNotificationType {
  INFO     = 'INFO',
  SUCCESS  = 'SUCCESS',
  WARNING  = 'WARNING',
  ERROR    = 'ERROR',
  PROMO    = 'PROMO',
}
```

---

## Proposed Request Shape

```json
{
  "userId": "usr_abc123",
  "type": "SUCCESS",
  "title": "Order Confirmed",
  "body": "Your order #ORD-2026-001 has been confirmed.",
  "actionUrl": "/orders/ORD-2026-001",
  "data": { "orderId": "ORD-2026-001" },
  "templateId": "INAPP_ORDER_CONFIRMED",
  "expiresAt": "2026-06-09T00:00:00.000Z"
}
```

---

## Proposed Template Catalog

### Auth & Account

| Template ID | type | Title | Body |
|---|---|---|---|
| `INAPP_WELCOME` | `SUCCESS` | Welcome! | Welcome to `{{appName}}`! Let's get started. |
| `INAPP_EMAIL_VERIFIED` | `SUCCESS` | Email Verified | Your email address has been verified. |
| `INAPP_PASSWORD_CHANGED` | `WARNING` | Password Changed | Your account password was changed just now. |
| `INAPP_MFA_ENABLED` | `SUCCESS` | Two-Factor Auth On | Your account is now protected with 2FA. |
| `INAPP_MFA_DISABLED` | `WARNING` | Two-Factor Auth Off | 2FA has been disabled on your account. |
| `INAPP_NEW_DEVICE_LOGIN` | `WARNING` | New Login | Sign-in from `{{device}}` detected. |
| `INAPP_ACCOUNT_LOCKED` | `ERROR` | Account Locked | Your account was locked due to failed attempts. |
| `INAPP_ACCOUNT_SUSPENDED` | `ERROR` | Account Suspended | Your account has been suspended. |

### Orders

| Template ID | type | Title | Body |
|---|---|---|---|
| `INAPP_ORDER_CONFIRMED` | `SUCCESS` | Order Confirmed | Order #`{{orderId}}` has been confirmed. |
| `INAPP_ORDER_SHIPPED` | `INFO` | Order Shipped | Your order is on the way. Tracking: `{{trackingNumber}}`. |
| `INAPP_ORDER_DELIVERED` | `SUCCESS` | Order Delivered | Your order arrived on `{{deliveryDate}}`. |
| `INAPP_ORDER_DELAYED` | `WARNING` | Order Delayed | Your order has been delayed. New ETA: `{{newETA}}`. |
| `INAPP_ORDER_CANCELLED` | `WARNING` | Order Cancelled | Order #`{{orderId}}` has been cancelled. |
| `INAPP_ORDER_REFUNDED` | `SUCCESS` | Refund Issued | ₹`{{refundAmount}}` has been refunded. |

### Payments

| Template ID | type | Title | Body |
|---|---|---|---|
| `INAPP_PAYMENT_SUCCESS` | `SUCCESS` | Payment Received | ₹`{{amount}}` payment successful (TxnID: `{{transactionId}}`). |
| `INAPP_PAYMENT_FAILED` | `ERROR` | Payment Failed | Your payment of ₹`{{amount}}` failed. Please retry. |
| `INAPP_INVOICE_GENERATED` | `INFO` | Invoice Ready | Invoice `{{invoiceNumber}}` for ₹`{{amount}}` is ready. |
| `INAPP_INVOICE_OVERDUE` | `WARNING` | Invoice Overdue | Invoice `{{invoiceNumber}}` is overdue. |
| `INAPP_SUBSCRIPTION_CANCELLED` | `WARNING` | Subscription Cancelled | `{{subscriptionName}}` has been cancelled. |
| `INAPP_AUTO_RENEWAL` | `INFO` | Subscription Renewing | `{{subscriptionName}}` renews on `{{renewalDate}}`. |

### Commerce

| Template ID | type | Title | Body |
|---|---|---|---|
| `INAPP_CART_ABANDONED` | `PROMO` | Finish Your Purchase | You left items in your cart worth ₹`{{totalAmount}}`. |
| `INAPP_WISHLIST_PRICE_DROP` | `PROMO` | Price Drop! | `{{productName}}` is now ₹`{{newPrice}}`. |
| `INAPP_WISHLIST_BACK_IN_STOCK` | `PROMO` | Back in Stock | `{{productName}}` is available again. |
| `INAPP_FLASH_SALE` | `PROMO` | Flash Sale | `{{discountPercent}}`% off — ends in `{{hoursRemaining}}` hours! |

### Organisation

| Template ID | type | Title | Body |
|---|---|---|---|
| `INAPP_ORG_INVITED` | `INFO` | Team Invitation | `{{invitedBy}}` invited you to join `{{orgName}}`. |
| `INAPP_ROLE_ASSIGNED` | `INFO` | Role Assigned | You've been assigned the `{{roleName}}` role in `{{orgName}}`. |
| `INAPP_API_KEY_CREATED` | `SUCCESS` | API Key Created | New API key `{{keyName}}` created. |
| `INAPP_API_KEY_REVOKED` | `WARNING` | API Key Revoked | API key `{{keyName}}` has been revoked. |

### System

| Template ID | type | Title | Body |
|---|---|---|---|
| `INAPP_SYSTEM_ALERT` | `ERROR` | System Alert | `{{message}}` |
| `INAPP_MAINTENANCE` | `WARNING` | Scheduled Maintenance | Maintenance on `{{scheduledAt}}` for `{{duration}}`. |
| `INAPP_DEPLOYMENT_DONE` | `SUCCESS` | Deployment Complete | Version `{{version}}` deployed successfully. |

---

## Implementation Roadmap

1. Create `InAppNotification` MongoDB schema with TTL index on `expiresAt`
2. Register `inapp.module.ts` with `InAppService` and `InAppController`
3. Implement `GET /v1/inapp/:userId` with cursor-based pagination (sorted by `createdAt DESC`)
4. Add `PATCH /v1/inapp/:userId/read-all` for bulk read
5. Implement SSE endpoint `GET /v1/inapp/stream/:userId` using `@nestjs/event-emitter` or Redis Pub/Sub
6. Add `INAPP_*` entries to `template-schemas.ts`
7. Add BullMQ `inapp` queue with same retry policy
8. Extend Kafka consumer to handle `inapp.notification.send` topic
9. Emit `inapp.notification.delivered` / `inapp.notification.failed` Kafka events
