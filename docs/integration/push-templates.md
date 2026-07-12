# Push Notification Templates (Planned)

> **Status: NOT IMPLEMENTED**  
> This document defines the proposed standard for a future Push Notification channel. No push endpoints exist yet.

---

## Proposed HTTP Endpoints

```
POST /v1/push/send          — Send a push notification
POST /v1/push/send-bulk     — Send to a segment or list of tokens
GET  /v1/push/logs          — Delivery history
GET  /v1/push/metrics       — Delivery rate stats
```

---

## Proposed Request Shape

```json
{
  "to": "ExponentPushToken[xxxxxxxxxxxxxx]",
  "title": "Your order has shipped!",
  "body": "Order #ORD-2026-001 is on its way. Expected: Apr 25.",
  "data": {
    "screen": "OrderDetail",
    "orderId": "ORD-2026-001"
  },
  "badge": 1,
  "sound": "default",
  "channelId": "order-updates",
  "templateId": "ORDER_SHIPPED",
  "idempotencyKey": "push-order-ORD-2026-001"
}
```

### Required Headers (same as email)

| Header | Description |
|---|---|
| `x-api-key` / `Authorization` | Authentication |
| `x-tenant-id` | Tenant identifier |
| `x-idempotency-key` | Deduplication key |

---

## Proposed Template Catalog

Templates define the `title`, `body`, and optional `data` payload injected into the push notification.

### Auth & Account

| Template ID | Title | Body | `data` fields |
|---|---|---|---|
| `PUSH_OTP_SENT` | Security Code | Your OTP is `{{otp}}`. Expires in `{{expiryMinutes}}` min. | `{ screen: "OTP" }` |
| `PUSH_PASSWORD_CHANGED` | Password Changed | Your account password was just changed. | `{ screen: "Security" }` |
| `PUSH_NEW_DEVICE_LOGIN` | New Login Detected | Sign-in from `{{device}}` at `{{timestamp}}`. | `{ screen: "Security", device }` |
| `PUSH_ACCOUNT_LOCKED` | Account Locked | Too many failed attempts. Contact support. | `{ screen: "Support" }` |
| `PUSH_MFA_ENABLED` | Two-Factor On | Two-factor authentication enabled on your account. | `{ screen: "Security" }` |

### Orders

| Template ID | Title | Body | `data` fields |
|---|---|---|---|
| `PUSH_ORDER_CONFIRMED` | Order Confirmed | Order #`{{orderId}}` confirmed! Total: `{{totalAmount}}`. | `{ screen: "OrderDetail", orderId }` |
| `PUSH_ORDER_SHIPPED` | Order Shipped | Your order is on the way! Tracking: `{{trackingNumber}}`. | `{ screen: "OrderTracking", orderId }` |
| `PUSH_ORDER_DELIVERED` | Order Delivered | Your order arrived on `{{deliveryDate}}`. | `{ screen: "OrderDetail", orderId }` |
| `PUSH_ORDER_CANCELLED` | Order Cancelled | Order #`{{orderId}}` has been cancelled. | `{ screen: "OrderDetail", orderId }` |
| `PUSH_ORDER_REFUNDED` | Refund Issued | ₹`{{refundAmount}}` refund for order #`{{orderId}}`. | `{ screen: "OrderDetail", orderId }` |

### Payments

| Template ID | Title | Body | `data` fields |
|---|---|---|---|
| `PUSH_PAYMENT_SUCCESS` | Payment Received | ₹`{{amount}}` payment successful. TxnID: `{{transactionId}}`. | `{ screen: "Billing" }` |
| `PUSH_PAYMENT_FAILED` | Payment Failed | Your payment of ₹`{{amount}}` failed. Please retry. | `{ screen: "Billing" }` |
| `PUSH_INVOICE_OVERDUE` | Invoice Overdue | Invoice `{{invoiceNumber}}` for ₹`{{amount}}` is overdue. | `{ screen: "Invoices" }` |
| `PUSH_AUTO_RENEWAL` | Subscription Renewing | `{{subscriptionName}}` renews on `{{renewalDate}}` for ₹`{{amount}}`. | `{ screen: "Billing" }` |

### Cart & Commerce

| Template ID | Title | Body | `data` fields |
|---|---|---|---|
| `PUSH_CART_ABANDONED` | Items in Cart | You left `{{itemCount}}` item(s) worth ₹`{{totalAmount}}` in your cart! | `{ screen: "Cart", cartId }` |
| `PUSH_WISHLIST_PRICE_DROP` | Price Drop! | `{{productName}}` dropped from ₹`{{oldPrice}}` to ₹`{{newPrice}}`. | `{ screen: "Wishlist" }` |
| `PUSH_WISHLIST_BACK_IN_STOCK` | Back in Stock | `{{productName}}` is available again! | `{ screen: "Product", productId }` |
| `PUSH_FLASH_SALE` | Flash Sale | `{{discountPercent}}`% off ends in `{{hoursRemaining}}` hours! | `{ screen: "Sale" }` |

### System

| Template ID | Title | Body | `data` fields |
|---|---|---|---|
| `PUSH_SYSTEM_ALERT` | System Alert | `{{message}}` | `{ screen: "Alerts" }` |
| `PUSH_MAINTENANCE` | Maintenance | Service maintenance on `{{scheduledAt}}`. Duration: `{{duration}}`. | `{ screen: "Status" }` |

---

## Proposed Platform Standards

### iOS (APNs)

```json
{
  "aps": {
    "alert": { "title": "Order Confirmed", "body": "Order #ORD-2026-001 confirmed!" },
    "badge": 1,
    "sound": "default",
    "content-available": 1,
    "category": "ORDER_UPDATE"
  },
  "data": { "screen": "OrderDetail", "orderId": "ORD-2026-001" }
}
```

### Android (FCM)

```json
{
  "notification": {
    "title": "Order Confirmed",
    "body": "Order #ORD-2026-001 confirmed!",
    "icon": "ic_notification",
    "channel_id": "order-updates",
    "click_action": "OPEN_ORDER_DETAIL"
  },
  "data": {
    "screen": "OrderDetail",
    "orderId": "ORD-2026-001"
  }
}
```

### Expo (React Native)

```json
{
  "to": "ExponentPushToken[xxxxxx]",
  "title": "Order Confirmed",
  "body": "Order #ORD-2026-001 confirmed!",
  "data": { "screen": "OrderDetail", "orderId": "ORD-2026-001" },
  "sound": "default",
  "badge": 1,
  "channelId": "order-updates"
}
```

---

## Implementation Roadmap

1. Register `push.module.ts` with `FCM`, `APNs`, and `Expo` adapters
2. Implement `PushService` with token registration (`PATCH /v1/push/device`)  
3. Implement `PushController` with `POST /v1/push/send`  
4. Add `PUSH_*` templates to `template-schemas.ts`  
5. Add BullMQ `push` queue with same retry policy as email  
6. Add Kafka consumer topic `push.notification.send`  
7. Extend health endpoint to report push provider connectivity
