# Templates

## Email Templates

The service ships with **378 named email templates** covering the full customer lifecycle. Each template is validated at send time — if required `data` fields are missing, the request is rejected with `400 Bad Request`.

### How to Use a Template

```json
{
  "to": "user@example.com",
  "template": "ORDER_CONFIRMED",
  "data": {
    "username": "John Doe",
    "orderId": "ORD-2026-001",
    "totalAmount": "1499.00"
  }
}
```

Templates marked with `requireCtaPath: true` also require the `x-path` header (or `ctaPath` in the request body).

---

### OTP / Email Verification

| Template | Required `data` fields | CTA Path |
|---|---|---|
| `otpEmailTemplate` | `otp` | No |
| `otpForLoginTemplate` | `username`, `otp` | No |
| `EMAIL_VERIFICATION_SEND` | `username`, `token` | No |
| `USER_EMAIL_VERIFIED` | `username` | No |

---

### User Lifecycle

| Template | Required `data` fields | CTA Path |
|---|---|---|
| `USER_CREATED` | `userId`, `username`, `email`, `timestamp` | No |
| `USER_WELCOME` | `username`, `email` | No |
| `ADMIN_USER_REGISTERED` | `userId`, `username`, `email`, `registeredAt` | No |
| `USER_UPDATED` | `userId`, `username`, `email`, `timestamp` | No |
| `USER_DELETED` | `userId`, `username`, `email`, `timestamp` | No |
| `USER_SUSPENDED` | `userId`, `username`, `email`, `timestamp` | No |
| `USER_BANNED` | `userId`, `username`, `email`, `timestamp` | No |
| `USER_REINSTATED` | `userId`, `username`, `email`, `timestamp` | No |
| `accountDeletedTemplate` | `username` | No |

---

### Roles & Permissions

| Template | Required `data` fields |
|---|---|
| `ROLE_ASSIGNED` | `username`, `roleName` |
| `ROLE_REVOKED` | `username`, `roleName` |
| `PERMISSION_CHANGED` | `username` |

---

### Password

| Template | Required `data` fields | CTA Path |
|---|---|---|
| `PASSWORD_CHANGED` | `username` | No |
| `PASSWORD_RESET_REQUESTED` | `resetLink` | No |
| `PASSWORD_RESET_COMPLETED` | `username` | No |
| `PASSWORD_EXPIRED` | `username` | No |
| `passwordExpiryReminderTemplate` | `username`, `resetLink` | No |

---

### Profile / Phone

| Template | Required `data` fields |
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

### Login / Security

| Template | Required `data` fields | CTA Path |
|---|---|---|
| `LOGIN_SUCCESS` | `username`, `ipAddress`, `timestamp` | No |
| `LOGIN_FAILED` | `username` | No |
| `NEW_DEVICE_LOGIN` | `username`, `device`, `timestamp` | No |
| `ACCOUNT_LOCKED` | `username` | No |
| `ACCOUNT_UNLOCKED` | `username` | No |
| `ACCOUNT_RECOVERY_REQUESTED` | `username` | No |
| `ACCOUNT_RECOVERY_COMPLETED` | `username` | No |
| `MFA_ENABLED` | `username`, `device`, `timestamp` | No |
| `MFA_DISABLED` | `username`, `device`, `timestamp` | Yes |
| `SESSION_EXPIRED` | `username`, `device`, `timestamp` | Yes |
| `loginAlertTemplate` | `username`, `device`, `location`, `time` | No |
| `logoutAllDevicesTemplate` | `username`, `timestamp` | Yes |
| `failedLoginAttemptsTemplate` | `username`, `attempts` | No |
| `failedLoginAttemptWarningTemplate` | `username`, `attempts` | No |
| `loginAttemptLimitExceededTemplate` | `username` | No |
| `trustedDeviceAddedTemplate` | `username`, `device`, `location` | No |
| `backupCodesTemplate` | `username`, `codes` | No |
| `accountVerificationReminderTemplate` | `username` | No |
| `trustedDeviceManagementUpdateTemplate` | `username` | No |
| `multiFactorAuthenticationSetupReminderTemplate` | `username` | No |
| `twoFactorEnabledDisabledNotificationTemplate` | `username`, `status` | No |
| `twoFactorCompletedTemplate` | `username` | No |
| `accountSecurityCheckReminderTemplate` | `username` | No |
| `sessionTimeoutNotificationTemplate` | `username` | No |
| `fraudulentTransactionAlertTemplate` | `username`, `transactionId`, `amount` | No |

---

### Account State

| Template | Required `data` fields | CTA Path |
|---|---|---|
| `CONSENT_REQUIRED` | `username`, `consentType` | Yes |
| `CONSENT_REVOKED` | `username`, `consentType` | No |
| `ACCOUNT_MERGED` | `username`, `accountId`, `reason` | No |
| `ACCOUNT_TERMINATED` | `username`, `accountId`, `reason` | No |
| `SOCIAL_LOGIN_CONNECTED` | `username`, `provider`, `timestamp` | Yes |
| `SOCIAL_LOGIN_DISCONNECTED` | `username`, `provider`, `timestamp` | Yes |
| `PRIVACY_POLICY_UPDATED` | `effectiveDate` | Yes |
| `TERMS_OF_SERVICE_UPDATED` | `effectiveDate` | Yes |
| `accountReactivationTemplate` | `username`, `reactivateLink` | No |
| `accountSuspendedTemplate` | `username`, `reason` | No |
| `consentRequiredTemplate` | `username`, `consentLink` | No |
| `securitySettingsUpdatedTemplate` | `username`, `setting` | No |
| `accountAccessRevokedTemplate` | `username` | No |
| `passwordStrengthWarningTemplate` | `username` | No |
| `accountMergeConfirmationTemplate` | `username` | Yes |
| `socialLoginConnectionTemplate` | `username`, `action` | No |
| `identityVerificationRequestTemplate` | `username` | No |
| `identityVerificationResultTemplate` | `username`, `result` | No |
| `backupEmailAddedRemovedTemplate` | `username`, `action` | No |
| `emailChangedTemplate` | `username`, `oldEmail`, `newEmail` | No |

---

### Organisation

| Template | Required `data` fields | CTA Path |
|---|---|---|
| `CONTACT_NOTIFICATION` | `name`, `email`, `subject`, `message` | No |
| `ORG_CREATED` | `orgName`, `adminName` | No |
| `ORG_UPDATED` | `orgName`, `updatedBy` | No |
| `ORG_DELETED` | `orgName`, `deletedBy` | No |
| `ORG_PLAN_CHANGED` | `orgName`, `oldPlan`, `newPlan` | No |
| `ORG_MEMBER_INVITED` | `orgName`, `inviteeEmail`, `invitedBy`, `inviteUrl` | No |
| `ORG_MEMBER_REMOVED` | `orgName`, `memberName` | Yes |
| `ORG_ROLE_ASSIGNED` | `orgName`, `memberName`, `roleName` | No |
| `ORG_ROLE_CHANGED` | `orgName`, `memberName`, `oldRole`, `newRole` | No |
| `ORG_ROLE_REVOKED` | `orgName`, `memberName`, `roleName` | No |
| `ORG_SECURITY_POLICY_UPDATED` | `orgName`, `updatedBy` | No |
| `ORG_API_KEY_CREATED` | `orgName`, `keyName`, `createdBy` | No |
| `ORG_API_KEY_REVOKED` | `orgName`, `keyName`, `revokedBy` | No |
| `ORG_DOMAIN_VERIFIED` | `orgName`, `domain` | No |
| `ORG_DOMAIN_UNVERIFIED` | `orgName`, `domain` | Yes |
| `ORG_BILLING_UPDATED` | `orgName`, `updatedBy` | No |
| `ORG_COMPLIANCE_AUDIT_COMPLETED` | `orgName`, `auditType`, `status` | No |
| `TEAM_INVITE` | `inviteeEmail`, `invitedBy`, `teamName` | No |

---

### Newsletter / Welcome

| Template | Required `data` fields |
|---|---|
| `NEWSLETTER_SUBSCRIBE_CONFIRMATION` | `name`, `email`, `confirmationUrl`, `companyName` |
| `NEWSLETTER_WELCOME` | `email`, `companyName` |
| `NEWSLETTER_RESUBSCRIBE` | `name`, `email`, `companyName` |
| `NEWSLETTER_FAREWELL` | `name`, `email`, `companyName` |
| `newsletterTemplate` | `title`, `content` |
| `ADMIN_CREATED_USER` | `username`, `email`, `temporaryPassword`, `loginUrl` |

---

### Payments (UPPERCASE)

| Template | Required `data` fields |
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

### Subscription (camelCase)

| Template | Required `data` fields | CTA Path |
|---|---|---|
| `subscriptionUpdatedTemplate` | `username`, `plan` | No |
| `subscriptionStartedTemplate` | `username`, `subscriptionName`, `startDate` | No |
| `subscriptionRenewedSuccessfullyTemplate` | `username`, `subscriptionName` | No |
| `subscriptionFailedRetryNeededTemplate` | `username`, `subscriptionName` | No |
| `subscriptionCanceledTemplate` | `username`, `subscriptionName` | No |
| `subscriptionPauseConfirmationTemplate` | `username`, `subscriptionName` | Yes |

---

### Payment (camelCase)

| Template | Required `data` fields |
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

### Cart / Wishlist (UPPERCASE)

| Template | Required `data` fields |
|---|---|
| `CART_CREATED` | `username`, `cartId`, `itemCount` |
| `CART_UPDATED` | `username`, `cartId`, `itemCount`, `totalAmount` |
| `CART_ABANDONED` | `username`, `cartId`, `itemCount`, `totalAmount` |
| `WISHLIST_CREATED` | `username`, `wishlistId`, `itemCount` |
| `WISHLIST_REMINDER` | `username`, `wishlistId`, `itemCount`, `items` |
| `WISHLIST_PRICE_DROP` | `username`, `productName`, `oldPrice`, `newPrice` |
| `WISHLIST_BACK_IN_STOCK` | `username`, `productName`, `productId` |
| `CART_ITEM_PRICE_CHANGED` | `username`, `cartId`, `productName`, `oldPrice`, `newPrice` |
| `CART_EXPIRY_NOTIFICATION` | `username`, `cartId`, `itemCount`, `expiryDate` |

---

### Wishlist / Cart (camelCase)

| Template | Required `data` fields |
|---|---|
| `wishlistReminderTemplate` | `username`, `wishlistItems` |
| `wishlistBackInStockTemplate` | `username`, `itemName` |
| `wishlistPriceDropAlertTemplate` | `username`, `itemName`, `newPrice` |
| `wishlistItemDiscontinuedTemplate` | `username`, `itemName` |
| `savedForLaterReminderTemplate` | `username`, `savedItems` |
| `cartItemPriceChangedTemplate` | `username`, `itemName`, `oldPrice`, `newPrice` |
| `cartExpiryNotificationTemplate` | `username` |

---

### Orders (UPPERCASE)

| Template | Required `data` fields |
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

### Orders (camelCase)

| Template | Required `data` fields |
|---|---|
| `orderProcessingTemplate` | `username`, `orderId` |
| `orderPackedTemplate` | `username`, `orderId` |
| `orderOutForDeliveryTemplate` | `username`, `orderId` |
| `partialOrderShippedTemplate` | `username`, `orderId` |
| `orderSplitShipmentTemplate` | `username`, `orderId` |
| `deliveryDelayedNotificationTemplate` | `username`, `orderId` |
| `orderCanceledByCustomerTemplate` | `username`, `orderId` |
| `orderCanceledByStoreTemplate` | `username`, `orderId`, `reason` |
| `preOrderConfirmationTemplate` | `username`, `productName`, `releaseDate` |
| `preOrderShippedTemplate` | `username`, `productName` |
| `digitalDownloadReadyTemplate` | `username`, `downloadLink` |
| `customOrderConfirmedTemplate` | `username` |
| `orderModificationRequestReceivedTemplate` | `username`, `orderId` |
| `orderModificationResultTemplate` | `username`, `orderId`, `status` |
| `returnRequestReceivedTemplate` | `username`, `orderId` |
| `returnApprovedTemplate` | `username`, `orderId`, `instructions` |
| `returnRejectedTemplate` | `username`, `orderId`, `reason` |
| `refundProcessedTemplate` | `username`, `orderId` |
| `exchangeApprovedTemplate` | `username`, `orderId`, `nextSteps` |
| `exchangeRejectedTemplate` | `username`, `orderId`, `reason` |
| `returnShipmentReceivedTemplate` | `username`, `orderId` |
| `partialRefundProcessedTemplate` | `username`, `orderId`, `details` |

---

### Returns / Exchanges (UPPERCASE)

| Template | Required `data` fields |
|---|---|
| `RETURN_REQUEST_RECEIVED` | `username`, `orderId`, `returnId`, `returnReason` |
| `RETURN_APPROVED` | `username`, `orderId`, `returnId` |
| `RETURN_REJECTED` | `username`, `orderId`, `returnId`, `rejectionReason` |
| `RETURN_COMPLETED` | `username`, `orderId`, `returnId`, `refundAmount`, `refundMethod` |
| `EXCHANGE_REQUESTED` | `username`, `orderId`, `exchangeId`, `originalItem`, `requestedItem` |
| `EXCHANGE_APPROVED` | `username`, `orderId`, `exchangeId`, `originalItem`, `newItem` |
| `EXCHANGE_REJECTED` | `username`, `orderId`, `exchangeId`, `rejectionReason` |

---

### Shipping / Packages (UPPERCASE)

| Template | Required `data` fields |
|---|---|
| `PACKAGE_DISPATCHED` | `username`, `orderId`, `trackingNumber` |
| `PACKAGE_IN_TRANSIT` | `username`, `orderId`, `trackingNumber`, `estimatedDelivery`, `carrier` |
| `PACKAGE_OUT_FOR_DELIVERY` | `username`, `orderId`, `trackingNumber`, `estimatedDelivery` |
| `PACKAGE_DELIVERED` | `username`, `orderId`, `deliveredAt` |
| `PACKAGE_DELAYED` | `username`, `orderId`, `trackingNumber`, `newDelivery`, `reason` |
| `PACKAGE_LOST` | `username`, `orderId`, `trackingNumber` |
| `DELIVERY_EXCEPTION` | `username`, `orderId`, `trackingNumber`, `exceptionType`, `details` |
| `CUSTOMS_HOLD` | `username`, `orderId`, `trackingNumber`, `holdReason` |

---

### Loyalty / Marketing (UPPERCASE)

| Template | Required `data` fields |
|---|---|
| `PROMOTION_LAUNCHED` | `username`, `promotionName`, `discountPercentage`, `validFrom`, `validTo` |
| `DISCOUNT_APPLIED` | `username`, `discountAmount`, `discountType` |
| `FLASH_SALE_ANNOUNCEMENT` | `saleName`, `startsAt`, `endsAt`, `discount` |
| `LOYALTY_POINTS_EARNED` | `username`, `pointsEarned`, `totalPoints`, `reason` |
| `LOYALTY_POINTS_REDEEMED` | `username`, `pointsRedeemed`, `remainingPoints`, `redemptionValue` |
| `NEW_PRODUCT_LAUNCH` | `username`, `productName`, `launchDate` |
| `CUSTOMER_MILESTONE` | `username`, `milestoneType`, `milestoneValue` |
| `REVIEW_REMINDER` | `username`, `productName`, `orderId` |
| `EVENT_INVITATION` | `username`, `eventName`, `eventDate`, `eventTime`, `location` |
| `HOLIDAY_GREETINGS` | `username`, `holidayName`, `greeting` |

---

### Loyalty / Marketing (camelCase)

| Template | Required `data` fields | CTA Path |
|---|---|---|
| `loyaltyPointsEarnedTemplate` | `username`, `points` | No |
| `loyaltyPointsRedeemedTemplate` | `username`, `points` | No |
| `loyaltyPointsExpiryReminderTemplate` | `username` | No |
| `loyaltyTierChangeTemplate` | `username`, `change` | No |
| `referralInvitationTemplate` | `username` | No |
| `referralBonusEarnedTemplate` | `username`, `bonus` | No |
| `referralBonusUsedTemplate` | `username`, `bonus` | No |
| `dataExportRequestTemplate` | `username`, `requestDate` | No |
| `trialExpiredTemplate` | `username`, `upgradeLink` | No |
| `newFeatureAnnouncementTemplate` | `username`, `featureName` | No |
| `onboardingSeriesTemplate` | `username` | No |
| `customerMilestoneTemplate` | `username`, `period` | No |
| `seasonalSaleAnnouncementTemplate` | `username` | No |
| `flashSaleTemplate` | `username` | No |
| `earlyAccessToSaleTemplate` | `username` | No |
| `sneakPeekTemplate` | `username` | No |
| `exclusiveEventTemplate` | `username` | No |
| `surveyRequestTemplate` | `username` | No |
| `holidayGreetingsTemplate` | `username` | No |
| `csrStoriesTemplate` | `username` | No |
| `appDownloadInvitationTemplate` | `username` | Yes |
| `abandonedBrowseReminderTemplate` | `username`, `items` | No |

---

### Products (UPPERCASE)

| Template | Required `data` fields |
|---|---|
| `PRODUCT_CREATED` | `productName`, `productId`, `category` |
| `PRODUCT_UPDATED` | `productName`, `productId`, `updatedFields`, `updatedBy` |
| `PRODUCT_DELETED` | `productName`, `productId`, `deletedBy` |
| `PRODUCT_FEATURED` | `productName`, `productId`, `featureType`, `startDate`, `endDate` |
| `PRODUCT_BACK_IN_STOCK` | `username`, `productName`, `productId` |
| `PRODUCT_REVIEWED` | `productName`, `productId`, `reviewerName`, `rating` |
| `PRODUCT_OUT_OF_STOCK` | `productName`, `productId` |
| `PRODUCT_ARCHIVED` | `productName`, `productId`, `archivedBy`, `reason` |

---

### Inventory (UPPERCASE)

| Template | Required `data` fields |
|---|---|
| `STOCK_LOW` | `productName`, `currentStock`, `minimumThreshold`, `productId` |
| `STOCK_CRITICAL` | `productName`, `currentStock`, `criticalThreshold`, `productId` |
| `STOCK_REPLENISHED` | `productName`, `quantityAdded`, `newStock` |
| `INVENTORY_AUDIT_COMPLETED` | `auditType`, `completedAt` |
| `SUPPLIER_DELAY` | `supplierName`, `orderId`, `originalDelivery`, `newDelivery` |
| `BATCH_EXPIRING_SOON` | `productName`, `batchNumber`, `expiryDate`, `daysRemaining` |
| `WAREHOUSE_TRANSFER_INITIATED` | `transferId`, `fromWarehouse`, `toWarehouse`, `initiatedBy` |

---

### Messaging / Communication (UPPERCASE)

| Template | Required `data` fields |
|---|---|
| `MESSAGE_SENT` | `senderName`, `recipientName`, `messagePreview`, `sentAt` |
| `MESSAGE_RECEIVED` | `recipientName`, `senderName`, `messagePreview`, `receivedAt` |
| `MESSAGE_READ` | `senderName`, `recipientName`, `readAt` |
| `MENTION_RECEIVED` | `username`, `mentionedBy`, `context`, `contentPreview` |
| `COMMENT_POSTED` | `username`, `commenterName`, `contentType`, `commentPreview` |
| `COMMENT_REPLIED` | `username`, `replyName`, `originalComment`, `replyContent` |
| `EMAIL_DELIVERED` | `emailAddress`, `messageSubject`, `deliveredAt`, `deliveryStatus` |
| `EMAIL_FAILED` | `emailAddress`, `messageSubject`, `failureReason`, `failedAt` |
| `PUSH_NOTIFICATION_SENT` | `deviceType`, `notificationTitle`, `notificationBody`, `sentAt` |
| `CHAT_STARTED` | `username`, `chatInitiator`, `topic`, `chatId` |
| `CHAT_ENDED` | `username`, `chatWith`, `topic`, `chatId` |

---

### System / Infrastructure (UPPERCASE)

| Template | Required `data` fields |
|---|---|
| `SYSTEM_ALERT` | `alertType`, `severity`, `message`, `detectedAt` |
| `MAINTENANCE_SCHEDULED` | `maintenanceType`, `scheduledStart`, `scheduledEnd` |
| `MAINTENANCE_STARTED` | `maintenanceType`, `startedAt`, `estimatedEnd` |
| `MAINTENANCE_COMPLETED` | `maintenanceType`, `completedAt`, `duration` |
| `DATA_BACKUP_COMPLETED` | `backupType`, `completedAt`, `status` |
| `SERVER_RESTARTED` | `serverName`, `restartReason`, `restartedAt` |
| `SERVER_OVERLOADED` | `serverName`, `cpuUsage`, `memoryUsage`, `detectedAt` |
| `DEPLOYMENT_STARTED` | `version`, `environment`, `deployedBy`, `startedAt` |
| `DEPLOYMENT_COMPLETED` | `version`, `environment`, `deployedBy`, `completedAt` |
| `DEPLOYMENT_FAILED` | `version`, `environment`, `deployedBy`, `failedAt`, `errorMessage` |
| `CONFIGURATION_CHANGED` | `configType`, `changedBy`, `changedAt`, `environment` |
| `SERVICE_OUTAGE_DETECTED` | `serviceName`, `detectedAt`, `errorDetails` |
| `SERVICE_RECOVERED` | `serviceName`, `recoveredAt`, `rootCause` |
| `NEW_FEATURE_RELEASED` | `featureName`, `releaseDate`, `description` |
| `systemMaintenanceNotificationTemplate` | `username`, `startTime`, `endTime` |
| `scheduledDowntimeNotificationTemplate` | `username`, `downtimeStart`, `downtimeEnd` |

---

### Reports / Analytics (UPPERCASE)

| Template | Required `data` fields |
|---|---|
| `DAILY_REPORT_READY` | `username`, `reportDate`, `reportUrl` |
| `WEEKLY_REPORT_READY` | `username`, `weekStart`, `weekEnd`, `reportUrl` |
| `MONTHLY_REPORT_READY` | `username`, `month`, `year`, `reportUrl` |
| `DATA_TREND_ALERT` | `username`, `trendType`, `metric`, `change` |
| `TRAFFIC_SPIKE` | `username`, `spikePercentage`, `currentTraffic`, `normalTraffic` |
| `CONVERSION_RATE_DROP` | `username`, `currentRate`, `previousRate`, `percentageDrop` |
| `ENGAGEMENT_INCREASED` | `username`, `engagementMetric`, `increasePercentage`, `currentValue` |
| `KPI_THRESHOLD_BREACHED` | `username`, `kpiName`, `currentValue`, `threshold` |

---

### Contact / Inquiry (UPPERCASE)

| Template | Required `data` fields |
|---|---|
| `CONTACT_REPLY` | `name`, `email`, `subject` |
| `INQUIRY_NOTIFICATION` | `name`, `email`, `projectType` |
| `CONTACT_CONFIRMATION` | `name`, `subject` |
| `INQUIRY_CONFIRMATION` | `name`, `projectType`, `budget`, `timeline` |

---

### Special / Utility (UPPERCASE)

| Template | Required `data` fields |
|---|---|
| `MAGIC_LINK` | `username`, `magicUrl` |
| `TRIAL_EXPIRING` | `username`, `upgradeUrl` |
| `DATA_EXPORT_READY` | `username`, `downloadUrl` |
| `BIRTHDAY_GREETING` | `username` |
| `IAM_BOOTSTRAP_CREDENTIALS` | `message` |

---

### Lead Management (UPPERCASE)

| Template | Required `data` fields |
|---|---|
| `LEAD_RECEIVED` | `firstName`, `lastName`, `leadNumber`, `subject`, `projectType` |
| `LEAD_ADMIN_NOTIFICATION` | `leadNumber`, `firstName`, `lastName`, `email` |
| `LEAD_CONTACT_REPLY` | `firstName`, `lastName`, `leadNumber`, `subject`, `message` |
| `LEAD_STATUS_CHANGED` | `firstName`, `lastName`, `leadNumber`, `oldStatus`, `newStatus` |
| `LEAD_FOLLOW_UP_REMINDER` | `agentName`, `leadNumber`, `leadFirstName`, `leadLastName`, `leadEmail` |
| `PROJECT_PROPOSAL_EMAIL` | `clientName`, `projectName`, `proposalUrl`, `proposalNumber` |
| `LEAD_PROPOSAL_ACCEPTED` | `firstName`, `leadNumber`, `projectName`, `quotedAmount`, `agentName` |
| `LEAD_ADMIN_PROPOSAL_ACCEPTED` | `leadNumber`, `firstName`, `lastName`, `email`, `projectName` |
| `LEAD_PROPOSAL_DECLINED_ACK` | `firstName`, `leadNumber`, `projectName`, `agentName` |
| `LEAD_ADMIN_PROPOSAL_DECLINED` | `leadNumber`, `firstName`, `lastName`, `email`, `declinedReason` |
| `LEAD_PROPOSAL_EXPIRING` | `leadNumber`, `firstName`, `lastName`, `email`, `proposalNumber`, `validUntil` |
| `LEAD_PROPOSAL_EXPIRED` | `leadNumber`, `firstName`, `lastName`, `email`, `proposalNumber`, `expiredAt` |
| `LEAD_CONTRACT_SENT` | `firstName`, `leadNumber`, `projectName`, `contractUrl`, `agentName` |
| `LEAD_CONTRACT_SIGNED` | `firstName`, `leadNumber`, `projectName`, `contractSignedAt`, `agentName` |
| `LEAD_WON_NOTIFICATION` | `leadNumber`, `firstName`, `lastName`, `email`, `projectName` |
| `LEAD_LOST_NOTIFICATION` | `leadNumber`, `firstName`, `lastName`, `email`, `lostReason` |

---

### Admin Templates (camelCase)

| Template | Required `data` fields | CTA Path |
|---|---|---|
| `newOrderPlacedAdminTemplate` | `adminName`, `orderId`, `customerName`, `total` | No |
| `highValueOrderAlertAdminTemplate` | `adminName`, `orderId`, `amount` | No |
| `lowStockAlertAdminTemplate` | `adminName`, `productId`, `productName`, `currentStock` | No |
| `outOfStockNotificationAdminTemplate` | `adminName`, `productId`, `productName` | No |
| `productDisabledAdminTemplate` | `adminName`, `productId`, `productName` | No |
| `newReviewSubmittedAdminTemplate` | `adminName`, `productName`, `reviewId` | Yes |
| `paymentDisputeAlertAdminTemplate` | `adminName`, `orderId` | No |
| `returnRequestNotificationAdminTemplate` | `adminName`, `orderId` | No |
| `refundProcessedNotificationAdminTemplate` | `adminName`, `orderId` | No |
| `dailySalesReportAdminTemplate` | `adminName`, `reportDate`, `totalSales` | No |
| `weeklyMonthlySalesReportAdminTemplate` | `adminName`, `period`, `totalSales` | No |
| `systemErrorFailedJobAlertAdminTemplate` | `adminName`, `errorDetails` | No |
| `customerSupportTicketCreatedAdminTemplate` | `adminName`, `ticketId`, `customerName` | No |
| `inventoryRestockNotificationAdminTemplate` | `adminName`, `productName`, `productId` | No |
| `bulkOrderRequestAdminTemplate` | `adminName`, `requestId`, `requesterName` | No |
| `customerDataDeletionRequestAdminTemplate` | `adminName`, `userName`, `userId` | No |
| `suspiciousAccountActivityAlertAdminTemplate` | `adminName`, `userName`, `userId`, `details` | No |
| `multipleFailedLoginAttemptsAdminTemplate` | `adminName`, `userName`, `userId`, `attempts` | No |
| `accountSuspensionReinstatementNotificationAdminTemplate` | `adminName`, `userName`, `userId`, `action` | No |
| `userProfileUpdateAlertAdminTemplate` | `adminName`, `userName`, `userId`, `changes` | No |
| `twoFactorStatusChangeAlertAdminTemplate` | `adminName`, `userName`, `userId`, `status` | No |
| `accountDeletionRequestDeniedAdminTemplate` | `adminName`, `userName`, `userId`, `reason` | No |
| `unusualAccountLoginPatternAdminTemplate` | `adminName`, `userName`, `userId`, `details` | No |
| `phoneVerificationStatusUpdateAdminTemplate` | `adminName`, `userName`, `userId`, `status` | No |
| `emailVerificationFailureAlertAdminTemplate` | `adminName`, `userName`, `userId`, `attempts` | No |
| `secondaryPhoneVerificationStatusUpdateAdminTemplate` | `adminName`, `userName`, `userId`, `status` | No |
| `identityVerificationRequestReceivedAdminTemplate` | `adminName`, `userName`, `userId` | No |
| `identityVerificationOutcomeNotificationAdminTemplate` | `adminName`, `userName`, `userId`, `result` | No |
| `accountAccessRevocationAdminTemplate` | `adminName`, `userName`, `userId` | No |
| `socialLoginConnectionAlertAdminTemplate` | `adminName`, `userName`, `userId`, `action` | No |
| `accountMergeRequestReceivedAdminTemplate` | `adminName`, `userName`, `userId` | No |
| `highRiskAccountActivityAlertAdminTemplate` | `adminName`, `userName`, `userId`, `details` | No |
| `accountRecoveryRequestReceivedAdminTemplate` | `adminName`, `userName`, `userId` | No |
| `fraudulentActivityDetectedAdminTemplate` | `adminName`, `userName`, `userId`, `activityDetails` | No |

---

### Marketplace (UPPERCASE)

| Template | Required `data` fields |
|---|---|
| `MARKETPLACE_WELCOME` | `name` |
| `MARKETPLACE_EMAIL_VERIFICATION` | `name`, `verificationLink` |
| `MARKETPLACE_PASSWORD_RESET` | `name`, `resetLink` |
| `MARKETPLACE_NEW_REQUEST` | `providerName`, `requestTitle`, `category`, `budget`, `customerName` |
| `MARKETPLACE_PROPOSAL_RECEIVED` | `customerName`, `providerName`, `requestTitle`, `price` |
| `MARKETPLACE_JOB_ASSIGNED` | `providerName`, `requestTitle`, `customerName`, `price`, `startDate` |
| `MARKETPLACE_PAYMENT_RECEIVED` | `providerName`, `amount`, `jobTitle`, `customerName` |
| `MARKETPLACE_PROVIDER_APPROVED` | `businessName`, `email` |
| `MARKETPLACE_PROVIDER_REJECTED` | `businessName`, `email`, `reason` |

---

## SMS Template Engine

SMS templates are stored per-tenant in MongoDB (`sms_templates` collection). Unlike email templates, SMS templates are user-created — not built-in.

### Variable Syntax

Template body uses `{{variableName}}` mustache-style substitution:

```
Your order {{orderId}} has shipped! Track it at {{trackingUrl}}.
```

Variables are resolved from the `variables` object in the send request.

### Template Object

```json
{
  "_id": "6650a1f2e4b0c23d4f8a91bc",
  "name": "Order Shipped",
  "code": "ORDER_SHIPPED",
  "body": "Hi {{name}}, your order {{orderId}} has shipped. Track: {{trackingUrl}}",
  "variables": ["name", "orderId", "trackingUrl"],
  "category": "TRANSACTIONAL",
  "dltTemplateId": "1234567890",
  "dltEntityId": "9876543210",
  "senderId": "MYAPP",
  "isActive": true,
  "isDeleted": false,
  "tenantId": "tenant_abc",
  "createdAt": "2026-06-01T00:00:00.000Z",
  "updatedAt": "2026-06-01T00:00:00.000Z"
}
```

### Template Code Auto-Generation

If you do not provide `code` when creating a template, it is auto-generated from the `name`:
- Uppercased
- Spaces replaced with `_`
- Special characters stripped

Example: `"Order Shipped"` → `"ORDER_SHIPPED"`

### Template Caching

Templates are cached in Redis after the first lookup. The cache is invalidated when a template is updated or deleted.

### Template Resolution Priority

When a send request includes multiple template identifiers, they are resolved in this order:

1. `templateId` (MongoDB ObjectId — most specific)
2. `templateCode` (unique per tenant)
3. `templateName` (resolved by name string match)
