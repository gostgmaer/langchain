# Email Template Standards

This document defines the design and coding standards for HTML email templates in the Notification Service.

---

## Template Architecture

All 378 email templates are defined as JavaScript functions in `src/channels/email/templates/emailTemplate.js`. Each function receives a context object and returns:

```typescript
{
  subject: string;
  html: string;
  text?: string;  // optional plain-text fallback
}
```

Template functions receive these standard arguments:

```javascript
function MY_TEMPLATE({ username, email, appUrl, applicationName, ctaPath, ...data }) {
  const _appUrl = appUrl || 'https://easydev.in';
  const _appName = applicationName || 'EasyDev';
  const ctaUrl = ctaPath ? _appUrl + ctaPath : _appUrl;
  // ...
}
```

---

## Layout Structure

All templates use a consistent layout:

```
┌───────────────────────────────────────┐
│  Logo + App Name (header)             │
├───────────────────────────────────────┤
│                                       │
│  Hero title (h1)                      │
│  Body paragraph(s)                    │
│                                       │
│  [Primary CTA Button]                 │
│                                       │
│  Optional data section / table        │
│                                       │
│  Security note (if sensitive)         │
│                                       │
├───────────────────────────────────────┤
│  Footer: company name, address        │
│  Unsubscribe / manage preferences     │
└───────────────────────────────────────┘
```

---

## Responsive Email Standards

### Max width

Container max-width: **600px**, centered.

### Inline styles only

Email clients strip `<style>` blocks. All styles must be inline.

### Font stack

```css
font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
```

### Colour palette

| Token | Value | Use |
|---|---|---|
| `--primary` | `#3B82F6` | CTA buttons, links |
| `--primary-dark` | `#2563EB` | Button hover |
| `--text-primary` | `#1F2937` | Body text |
| `--text-muted` | `#6B7280` | Subtext, metadata |
| `--background` | `#F9FAFB` | Page background |
| `--surface` | `#FFFFFF` | Card/container background |
| `--border` | `#E5E7EB` | Dividers, borders |
| `--success` | `#10B981` | Success badges |
| `--warning` | `#F59E0B` | Warning notices |
| `--danger` | `#EF4444` | Error notices |

---

## Dark Mode Support

Use `prefers-color-scheme` media query in the `<style>` block within `<head>`:

```html
<style>
  @media (prefers-color-scheme: dark) {
    .email-body { background-color: #111827 !important; }
    .email-container { background-color: #1F2937 !important; }
    .email-text { color: #F9FAFB !important; }
    .email-muted { color: #9CA3AF !important; }
  }
</style>
```

Apply both the light-mode inline style and a class name so dark-mode clients can override:

```html
<td class="email-text" style="color: #1F2937;">Your order has been confirmed.</td>
```

---

## CTA Button Standard

```html
<table role="presentation" cellpadding="0" cellspacing="0" style="margin: 24px auto;">
  <tr>
    <td style="
      background-color: #3B82F6;
      border-radius: 6px;
      text-align: center;
    ">
      <a href="{{ctaUrl}}"
         target="_blank"
         style="
           display: inline-block;
           padding: 12px 24px;
           color: #ffffff;
           font-size: 16px;
           font-weight: 600;
           text-decoration: none;
           letter-spacing: 0.02em;
         ">
        View Order
      </a>
    </td>
  </tr>
</table>
```

Always use `<table>` for buttons — `<a>` elements with `display: block` are unreliable in Outlook.

---

## Data Table Standard (for order summaries, invoices, etc.)

```html
<table role="presentation" width="100%" cellpadding="0" cellspacing="0"
       style="border-collapse: collapse; margin: 16px 0;">
  <thead>
    <tr style="background-color: #F3F4F6;">
      <th style="padding: 10px 12px; text-align: left; font-size: 12px;
                 text-transform: uppercase; color: #6B7280; border-bottom: 1px solid #E5E7EB;">
        Item
      </th>
      <th style="padding: 10px 12px; text-align: right; font-size: 12px;
                 text-transform: uppercase; color: #6B7280; border-bottom: 1px solid #E5E7EB;">
        Amount
      </th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td style="padding: 10px 12px; border-bottom: 1px solid #E5E7EB; color: #1F2937;">
        Pro Plan — Annual
      </td>
      <td style="padding: 10px 12px; text-align: right; border-bottom: 1px solid #E5E7EB; color: #1F2937;">
        ₹4,999.00
      </td>
    </tr>
  </tbody>
  <tfoot>
    <tr style="background-color: #F9FAFB;">
      <td style="padding: 10px 12px; font-weight: 600; color: #1F2937;">Total</td>
      <td style="padding: 10px 12px; text-align: right; font-weight: 600; color: #1F2937;">₹4,999.00</td>
    </tr>
  </tfoot>
</table>
```

---

## Security / Sensitive Content Banner

For templates involving passwords, MFA, or account changes:

```html
<div style="
  background-color: #FEF3C7;
  border-left: 4px solid #F59E0B;
  padding: 12px 16px;
  margin: 16px 0;
  border-radius: 0 4px 4px 0;
">
  <p style="margin: 0; font-size: 13px; color: #92400E;">
    If you did not request this, please secure your account immediately.
  </p>
</div>
```

---

## Fallback Plain Text

Every template should return a `text` property with a condensed plain-text version:

```javascript
return {
  subject: `Welcome to ${_appName}!`,
  html: `...full HTML...`,
  text: [
    `Welcome to ${_appName}, ${username}!`,
    '',
    `Please verify your email: ${verifyLink}`,
    '',
    `If you did not sign up, ignore this email.`,
    '',
    `— The ${_appName} Team`,
  ].join('\n'),
};
```

---

## Template Preheader (Preview Text)

Add a hidden preheader span immediately after `<body>` to control what appears in inbox previews:

```html
<span style="
  display: none;
  max-height: 0;
  overflow: hidden;
  mso-hide: all;
">
  Welcome to MyApp! Verify your email to get started.
  &nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌&nbsp;‌
</span>
```

---

## Creating a New Template

1. Add the template function to `emailTemplate.js`
2. Register the schema in `template-schemas.ts`:

```typescript
MY_NEW_TEMPLATE: {
  data: ['username', 'requiredField1', 'requiredField2'],
  requireAppUrl: true,        // if CTA buttons are used
  requireApplicationName: true, // if app branding is used
  requireCtaPath: false,
},
```

3. Test with:

```bash
curl -X POST http://localhost:4000/v1/email/send-sync \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -H "x-tenant-id: test" \
  -H "x-app-name: TestApp" \
  -H "x-app-url: https://test.com" \
  -H "x-idempotency-key: test-$(date +%s)" \
  -d '{
    "to": "your.email@example.com",
    "template": "MY_NEW_TEMPLATE",
    "data": { "username": "Tester", "requiredField1": "val1", "requiredField2": "val2" }
  }'
```

---

## Supported Email Clients

Templates are tested against:

| Client | Version | Notes |
|---|---|---|
| Gmail | Web + Android + iOS | Full support |
| Outlook | 2016–2021 | Limited CSS; avoid flex/grid |
| Apple Mail | macOS + iOS | Full support including dark mode |
| Yahoo Mail | Web | Limited media query support |
| Samsung Email | Android | Full support |

Avoid: CSS Grid, Flexbox, `position: absolute/fixed`, CSS variables (`var(--)`), `:hover` (use `title` links for links).
