# Template Catalog

Complete reference for all 378 named email templates. Each entry shows the template ID, required `data` fields, and which optional headers are enforced.

**Header flags:**
- `requireAppUrl: true` → `x-app-url` header required  
- `requireApplicationName: true` → `x-app-name` header required  
- `requireCtaPath: true` → `x-path` header required  

---

## OTP / Email Verification

| Template ID | Required `data` fields | Header flags |
|---|---|---|
| `otpEmailTemplate` | `otp` | — |
| `otpForLoginTemplate` | `username`, `otp` | — |
| `EMAIL_VERIFICATION_SEND` | `username`, `token` | — |
| `USER_EMAIL_VERIFIED` | `username` | — |

---

## User Lifecycle

| Template ID | Required `data` fields | Header flags |
|---|---|---|
| `USER_CREATED` | `userId`, `username`, `email`, `timestamp` | — |
| `USER_WELCOME` | `username`, `email`, `verifyLink` | `requireAppUrl`, `requireApplicationName` |
| `ADMIN_USER_REGISTERED` | `userId`, `username`, `email`, `registeredAt` | — |
| `USER_UPDATED` | `userId`, `username`, `email`, `timestamp` | — |
| `USER_DELETED` | `userId`, `username`, `email`, `timestamp` | — |
| `USER_SUSPENDED` | `userId`, `username`, `email`, `timestamp` | — |
| `USER_BANNED` | `userId`, `username`, `email`, `timestamp` | — |
| `USER_REINSTATED` | `userId`, `username`, `email`, `timestamp` | — |
| `accountDeletedTemplate` | `username` | — |

### USER_WELCOME — full example

```json
{
  "to": "john@example.com",
  "template": "USER_WELCOME",
  "data": {
    "username": "John Doe",
    "email": "john@example.com",
    "verifyLink": "https://myapp.com/verify?token=abc123"
  }
}
```

Headers required: `x-app-url`, `x-app-name`, `x-tenant-id`, `x-idempotency-key`

---

## Product Access

| Template ID | Required `data` fields | Header flags |
|---|---|---|
| `PRODUCT_ACCESS_GRANTED` | `username`, `productName`, `productUrl`, `planType` | `requireAppUrl`, `requireApplicationName` |

### PRODUCT_ACCESS_GRANTED — full example

```json
{
  "to": "john@example.com",
  "template": "PRODUCT_ACCESS_GRANTED",
  "data": {
    "username": "John Doe",
    "productName": "AI Communication",
    "productUrl": "https://ai.myapp.com",
    "planType": "STARTER"
  }
}
```

---

## Roles & Permissions

| Template ID | Required `data` fields | Header flags |
|---|---|---|
| `ROLE_ASSIGNED` | `username`, `roleName` | — |
| `ROLE_REVOKED` | `username`, `roleName` | — |
| `PERMISSION_CHANGED` | `username` | — |

---

## Password

| Template ID | Required `data` fields | Header flags |
|---|---|---|
| `PASSWORD_CHANGED` | `username` | — |
| `PASSWORD_RESET_REQUESTED` | `resetLink` | — |
| `PASSWORD_RESET_COMPLETED` | `username` | — |
| `PASSWORD_EXPIRED` | `username` | — |
| `passwordExpiryReminderTemplate` | `username`, `resetLink` | — |

---

## Profile / Phone

| Template ID | Required `data` fields |
|---|---|
| `PHONE_VERIFIED` | `username` |
| `PROFILE_COMPLETED` | `username` |
| `PROFILE_PICTURE_UPDATED` | `username` |
| `phoneVerificationTemplate` | `username`, `phone`, `verificationCode` |
| `secondaryPhoneVerificationTemplate` | `username`, `verificationCode` |
| `phoneNumberChangeRequestTemplate` | `username`, `newPhone`, `confirmationCode` |
| `phoneNumberChangeConfirmationTemplate` | `username`, `updatedPhone` |
| `emailPhoneVerificationReminderTemplate` | `username` |

---

## Login / Security

| Template ID | Required `data` fields | CTA Path |
|---|---|---|
| `LOGIN_SUCCESS` | `username`, `ipAddress`, `timestamp` | — |
| `LOGIN_FAILED` | `username` | — |
| `NEW_DEVICE_LOGIN` | `username`, `device`, `timestamp` | — |
| `ACCOUNT_LOCKED` | `username` | — |
| `ACCOUNT_UNLOCKED` | `username` | — |
| `ACCOUNT_RECOVERY_REQUESTED` | `username` | — |
| `ACCOUNT_RECOVERY_COMPLETED` | `username` | — |
| `MFA_ENABLED` | `username`, `device`, `timestamp` | — |
| `MFA_DISABLED` | `username`, `device`, `timestamp` | `requireCtaPath` |
| `SESSION_EXPIRED` | `username`, `device`, `timestamp` | `requireCtaPath` |
| `loginAlertTemplate` | `username`, `device`, `location`, `time` | — |
| `logoutAllDevicesTemplate` | `username`, `timestamp` | `requireCtaPath` |
| `failedLoginAttemptsTemplate` | `username`, `attempts` | — |
| `failedLoginAttemptWarningTemplate` | `username`, `attempts` | — |
| `loginAttemptLimitExceededTemplate` | `username` | — |
| `trustedDeviceAddedTemplate` | `username`, `device`, `location` | — |
| `backupCodesTemplate` | `username`, `codes` | — |
| `accountVerificationReminderTemplate` | `username` | — |
| `trustedDeviceManagementUpdateTemplate` | `username` | — |
| `multiFactorAuthenticationSetupReminderTemplate` | `username` | — |
| `twoFactorEnabledDisabledNotificationTemplate` | `username`, `status` | — |
| `twoFactorCompletedTemplate` | `username` | — |
| `accountSecurityCheckReminderTemplate` | `username` | — |
| `sessionTimeoutNotificationTemplate` | `username` | — |
| `fraudulentTransactionAlertTemplate` | `username`, `transactionId`, `amount` | — |

---

## Account State

| Template ID | Required `data` fields | CTA Path |
|---|---|---|
| `CONSENT_REQUIRED` | `username`, `consentType` | `requireCtaPath` |
| `CONSENT_REVOKED` | `username`, `consentType` | — |
| `ACCOUNT_MERGED` | `username`, `accountId`, `reason` | — |
| `ACCOUNT_TERMINATED` | `username`, `accountId`, `reason` | — |
| `SOCIAL_LOGIN_CONNECTED` | `username`, `provider`, `timestamp` | `requireCtaPath` |
| `SOCIAL_LOGIN_DISCONNECTED` | `username`, `provider`, `timestamp` | `requireCtaPath` |
| `PRIVACY_POLICY_UPDATED` | `effectiveDate` | `requireCtaPath` |
| `TERMS_OF_SERVICE_UPDATED` | `effectiveDate` | `requireCtaPath` |
| `accountReactivationTemplate` | `username`, `reactivateLink` | — |
| `accountSuspendedTemplate` | `username`, `reason` | — |
| `consentRequiredTemplate` | `username`, `consentLink` | — |
| `securitySettingsUpdatedTemplate` | `username`, `setting` | — |
| `accountAccessRevokedTemplate` | `username` | — |
| `passwordStrengthWarningTemplate` | `username` | — |
| `accountMergeConfirmationTemplate` | `username` | `requireCtaPath` |
| `socialLoginConnectionTemplate` | `username`, `action` | — |
| `identityVerificationRequestTemplate` | `username` | — |
| `identityVerificationResultTemplate` | `username`, `result` | — |
| `backupEmailAddedRemovedTemplate` | `username`, `action` | — |
| `emailChangedTemplate` | `username`, `oldEmail`, `newEmail` | — |

---

## Organisation

| Template ID | Required `data` fields | CTA Path |
|---|---|---|
| `CONTACT_NOTIFICATION` | `name`, `email`, `subject`, `message` | — |
| `ORG_CREATED` | `orgName`, `adminName` | — |
| `ORG_UPDATED` | `orgName`, `updatedBy` | — |
| `ORG_DELETED` | `orgName`, `deletedBy` | — |
| `ORG_PLAN_CHANGED` | `orgName`, `oldPlan`, `newPlan` | — |
| `ORG_MEMBER_INVITED` | `orgName`, `inviteeEmail`, `invitedBy`, `inviteUrl` | — |
| `ORG_MEMBER_REMOVED` | `orgName`, `memberName` | `requireCtaPath` |
| `ORG_ROLE_ASSIGNED` | `orgName`, `memberName`, `roleName` | — |
| `ORG_ROLE_CHANGED` | `orgName`, `memberName`, `oldRole`, `newRole` | — |
| `ORG_ROLE_REVOKED` | `orgName`, `memberName`, `roleName` | — |
| `ORG_SECURITY_POLICY_UPDATED` | `orgName`, `updatedBy` | — |
| `ORG_API_KEY_CREATED` | `orgName`, `keyName`, `createdBy` | — |
| `ORG_API_KEY_REVOKED` | `orgName`, `keyName`, `revokedBy` | — |
| `ORG_DOMAIN_VERIFIED` | `orgName`, `domain` | — |
| `ORG_DOMAIN_UNVERIFIED` | `orgName`, `domain` | `requireCtaPath` |
| `ORG_BILLING_UPDATED` | `orgName`, `updatedBy` | — |
| `ORG_COMPLIANCE_AUDIT_COMPLETED` | `orgName`, `auditType`, `status` | — |
| `TEAM_INVITE` | `inviteeEmail`, `invitedBy`, `teamName` | — |

---

## Newsletter / Admin

| Template ID | Required `data` fields |
|---|---|
| `NEWSLETTER_SUBSCRIBE_CONFIRMATION` | `name`, `email`, `confirmationUrl`, `companyName` |
| `NEWSLETTER_WELCOME` | `email`, `companyName` |
| `NEWSLETTER_RESUBSCRIBE` | `name`, `email`, `companyName` |
| `NEWSLETTER_FAREWELL` | `name`, `email`, `companyName` |
| `newsletterTemplate` | `title`, `content` |
| `ADMIN_CREATED_USER` | `username`, `email`, `temporaryPassword`, `loginUrl` |

---

## System

| Template ID | Required `data` fields |
|---|---|
| `SYSTEM_ALERT` | `alertType`, `severity`, `message`, `detectedAt` |
| `MAINTENANCE_SCHEDULED` | `scheduledAt`, `duration`, `affectedServices` |
| `DEPLOYMENT_COMPLETED` | `version`, `deployedBy`, `deployedAt` |
| `WEEKLY_REPORT_READY` | `username`, `weekStart`, `weekEnd`, `reportUrl` |
| `systemAlertTemplate` | `alertType`, `message`, `severity`, `detectedAt` |

### SYSTEM_ALERT — full example

```json
{
  "to": "ops@example.com",
  "template": "SYSTEM_ALERT",
  "data": {
    "alertType": "WEBHOOK_FAILURE",
    "severity": "HIGH",
    "message": "Webhook delivery to https://api.example.com/hook failed after 3 retries",
    "detectedAt": "2026-06-02T10:00:00.000Z"
  }
}
```

---

## Payments (UPPERCASE)

| Template ID | Required `data` fields |
|---|---|
| `PAYMENT_SUCCESS` | `username`, `amount`, `transactionId` |
| `PAYMENT_FAILED` | `username`, `amount`, `transactionId`, `failureReason` |
| `PAYMENT_PENDING` | `username`, `amount`, `paymentMethod` |
| `PAYMENT_REFUNDED` | `username`, `amount`, `transactionId`, `refundId` |
| `INVOICE_GENERATED` | `username`, `invoiceNumber`, `dueDate`, `amount` |
| `INVOICE_PAID` | `username`, `invoiceNumber`, `amount` |
| `INVOICE_OVERDUE` | `username`, `invoiceNumber`, `dueDate`, `amount` |
| `INVOICE_CANCELLED` | `username`, `invoiceNumber` |
| `BILLING_INFO_UPDATED` | `username`, `updatedFields`, `updatedAt` |
| `AUTO_RENEWAL_REMINDER` | `username`, `subscriptionName`, `renewalDate`, `amount` |
| `SUBSCRIPTION_STARTED` | `username`, `subscriptionName`, `startDate` |
| `SUBSCRIPTION_CANCELLED` | `username`, `subscriptionName`, `cancelledAt` |
| `SUBSCRIPTION_RENEWED` | `username`, `subscriptionName`, `renewalDate`, `amount` |
| `CHARGEBACK_INITIATED` | `username`, `transactionId`, `amount`, `reason` |
| `CHARGEBACK_RESOLVED` | `username`, `transactionId`, `amount`, `outcome` |

---

## Subscription (camelCase)

| Template ID | Required `data` fields | CTA Path |
|---|---|---|
| `subscriptionUpdatedTemplate` | `username`, `plan` | — |
| `subscriptionStartedTemplate` | `username`, `subscriptionName`, `startDate` | — |
| `subscriptionRenewedSuccessfullyTemplate` | `username`, `subscriptionName` | — |
| `subscriptionFailedRetryNeededTemplate` | `username`, `subscriptionName` | — |
| `subscriptionCanceledTemplate` | `username`, `subscriptionName` | — |
| `subscriptionPauseConfirmationTemplate` | `username`, `subscriptionName` | `requireCtaPath` |

---

## Payment (camelCase)

| Template ID | Required `data` fields |
|---|---|
| `paymentSuccessfulTemplate` | `username`, `orderId`, `amount` |
| `paymentMethodExpiringSoonTemplate` | `username`, `expiryDate` |
| `paymentMethodUpdatedTemplate` | `username` |
| `paymentDisputeNotificationTemplate` | `username`, `orderId` |
| `paymentDisputeResolvedTemplate` | `username`, `orderId` |
| `creditNoteIssuedTemplate` | `username`, `creditNoteNumber`, `amount`, `issueDate` |
| `giftCardPurchasedTemplate` | `username`, `giftCardCode`, `amount` |
| `giftCardRedeemedTemplate` | `username`, `giftCardCode`, `amount` |
| `giftCardReceivedTemplate` | `username`, `sender`, `amount`, `redeemCode` |
| `storeCreditAddedTemplate` | `username`, `amount` |
| `storeCreditUsedTemplate` | `username`, `amount` |
| `emiPaymentReminderTemplate` | `username`, `dueDate` |

---

## Cart / Wishlist (UPPERCASE)

| Template ID | Required `data` fields |
|---|---|
| `CART_CREATED` | `username`, `cartId`, `itemCount` |
| `CART_UPDATED` | `username`, `cartId`, `itemCount`, `totalAmount` |
| `CART_ABANDONED` | `username`, `cartId`, `itemCount`, `totalAmount`, `items`, `abandonedAt` |
| `WISHLIST_CREATED` | `username`, `wishlistId`, `itemCount` |
| `WISHLIST_REMINDER` | `username`, `wishlistId`, `itemCount`, `items` |
| `WISHLIST_PRICE_DROP` | `username`, `productName`, `oldPrice`, `newPrice` |
| `WISHLIST_BACK_IN_STOCK` | `username`, `productName`, `productId` |
| `CART_ITEM_PRICE_CHANGED` | `username`, `cartId`, `productName`, `oldPrice`, `newPrice` |
| `CART_EXPIRY_NOTIFICATION` | `username`, `cartId`, `itemCount`, `expiryDate` |

---

## Cart / Wishlist (camelCase)

| Template ID | Required `data` fields |
|---|---|
| `wishlistReminderTemplate` | `username`, `wishlistItems` |
| `wishlistBackInStockTemplate` | `username`, `itemName` |
| `wishlistPriceDropAlertTemplate` | `username`, `itemName`, `newPrice` |
| `wishlistItemDiscontinuedTemplate` | `username`, `itemName` |
| `savedForLaterReminderTemplate` | `username`, `savedItems` |
| `cartItemPriceChangedTemplate` | `username`, `itemName`, `oldPrice`, `newPrice` |
| `cartExpiryNotificationTemplate` | `username` |

---

## Orders (UPPERCASE)

| Template ID | Required `data` fields |
|---|---|
| `ORDER_CREATED` | `username`, `orderId`, `totalAmount` |
| `ORDER_CONFIRMED` | `username`, `orderId`, `totalAmount` |
| `ORDER_SHIPPED` | `username`, `orderId`, `trackingNumber`, `carrier` |
| `ORDER_DELIVERED` | `username`, `orderId`, `deliveryDate` |
| `ORDER_DELAYED` | `username`, `orderId`, `reason`, `newEstimatedDelivery` |
| `ORDER_CANCELLED` | `username`, `orderId` |
| `ORDER_RETURNED` | `username`, `orderId`, `returnReason` |
| `ORDER_REFUNDED` | `username`, `orderId`, `refundAmount`, `refundMethod` |
| `ORDER_PAYMENT_PENDING` | `username`, `orderId`, `amount`, `paymentMethod` |
| `ORDER_PAYMENT_FAILED` | `username`, `orderId`, `amount`, `paymentMethod`, `failureReason` |
| `ORDER_PARTIALLY_SHIPPED` | `username`, `orderId`, `trackingNumber` |
| `CUSTOM_ORDER_CONFIRMED` | `username`, `orderId`, `customDetails`, `totalAmount` |
| `ORDER_REVIEWED` | `username`, `orderId`, `rating` |

---

## Orders (camelCase)

| Template ID | Required `data` fields |
|---|---|
| `orderProcessingTemplate` | `username`, `orderId` |
| `orderPackedTemplate` | `username`, `orderId` |
| `orderOutForDeliveryTemplate` | `username`, `orderId` |
| `partialOrderShippedTemplate` | `username`, `orderId` |
| `orderSplitShipmentTemplate` | `username`, `orderId` |
| `deliveryDelayedNotificationTemplate` | `username`, `orderId` |
| `orderCanceledByCustomerTemplate` | `username`, `orderId` |

---

## Returns / Refunds (camelCase)

| Template ID | Required `data` fields |
|---|---|
| `returnInitiatedTemplate` | `username`, `returnId`, `orderId` |
| `refundProcessedTemplate` | `username`, `refundId`, `amount` |
| `returnStatusUpdateTemplate` | `username`, `returnId`, `status` |
| `exchangeInitiatedTemplate` | `username`, `orderId`, `newOrderId` |
| `exchangeCompletedTemplate` | `username`, `orderId` |
| `returnRejectedTemplate` | `username`, `returnId`, `reason` |

---

## Rewards / Loyalty

| Template ID | Required `data` fields |
|---|---|
| `LOYALTY_POINTS_EARNED` | `username`, `points`, `totalPoints` |
| `LOYALTY_POINTS_REDEEMED` | `username`, `points`, `orderId` |
| `LOYALTY_TIER_UPGRADE` | `username`, `oldTier`, `newTier` |
| `loyaltyPointsExpiringSoonTemplate` | `username`, `points`, `expiryDate` |
| `loyaltyMilestoneAchievedTemplate` | `username`, `milestone` |
| `referralBonusEarnedTemplate` | `username`, `bonusAmount` |
| `BIRTHDAY_GREETING` | `username` |
| `ANNIVERSARY_CELEBRATION` | `username`, `years` |

---

## Marketing / Promotions

| Template ID | Required `data` fields |
|---|---|
| `FLASH_SALE_ANNOUNCEMENT` | `saleTitle`, `discountPercent`, `endsAt` |
| `NEW_PRODUCT_LAUNCH` | `productName`, `productUrl` |
| `PROMOTION_LAUNCHED` | `promoTitle`, `description`, `validUntil` |
| `NEWSLETTER_PROMOTION` | `subject`, `content` |
| `personalizedRecommendationTemplate` | `username`, `items` |
| `newFeatureAnnouncementTemplate` | `featureName`, `description` |
| `productReviewRequestTemplate` | `username`, `orderId`, `productName` |
| `surveyInvitationTemplate` | `username`, `surveyUrl` |
| `MAGIC_LINK` | `username`, `magicLink` |

---

## Marketplace

| Template ID | Required `data` fields |
|---|---|
| `MARKETPLACE_WELCOME` | `username`, `marketplaceName` |
| `MARKETPLACE_NEW_REQUEST` | `sellerName`, `buyerName`, `requestTitle` |
| `MARKETPLACE_REQUEST_ACCEPTED` | `buyerName`, `requestTitle` |
| `MARKETPLACE_REQUEST_REJECTED` | `buyerName`, `requestTitle`, `reason` |
| `MARKETPLACE_PAYMENT_RECEIVED` | `sellerName`, `amount`, `orderId` |
| `MARKETPLACE_JOB_ASSIGNED` | `workerName`, `jobTitle`, `startDate` |
| `MARKETPLACE_JOB_COMPLETED` | `clientName`, `jobTitle` |

---

## Support / Notifications

| Template ID | Required `data` fields |
|---|---|
| `SUPPORT_TICKET_OPENED` | `username`, `ticketId`, `subject` |
| `SUPPORT_TICKET_UPDATED` | `username`, `ticketId`, `status` |
| `SUPPORT_TICKET_RESOLVED` | `username`, `ticketId` |
| `SUPPORT_TICKET_CLOSED` | `username`, `ticketId` |
| `notificationPreferencesUpdatedTemplate` | `username` |
| `weeklyActivitySummaryTemplate` | `username`, `weekStart`, `weekEnd` |
| `monthlyStatementTemplate` | `username`, `month`, `year` |

---

## Compliance / Data

| Template ID | Required `data` fields |
|---|---|
| `GDPR_DATA_EXPORT_READY` | `username`, `downloadUrl`, `expiresAt` |
| `GDPR_DATA_DELETION_CONFIRMED` | `username` |
| `GDPR_CONSENT_RECEIPT` | `username`, `consentType`, `timestamp` |
| `dataBreachNotificationTemplate` | `username`, `detectedAt`, `affectedData` |
