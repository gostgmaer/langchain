# RBAC (Role-Based Access Control) Guide

## Overview

This service implements Role-Based Access Control (RBAC) integrated with your API Gateway. The gateway validates JWT tokens and forwards user context via signed headers.

## Architecture

```
Client → API Gateway (JWT validation) → File Service (RBAC enforcement)
```

**Flow:**
1. Client sends request with JWT in `Authorization` header
2. API Gateway validates JWT signature
3. Gateway extracts user info from JWT payload
4. Gateway signs user context with HMAC
5. Gateway forwards request to file service with headers:
   - `X-User-Id`: User identifier (or "anonymous")
   - `X-User-Email`: User email
   - `X-User-Role`: Role from JWT (anonymous|user|editor|admin)
   - `X-Gateway-HMAC`: HMAC signature for tamper prevention
6. File service verifies HMAC signature
7. File service enforces role-based permissions

## Roles & Permissions

### Role Hierarchy
```
anonymous < user < admin
```

### 1. Anonymous (Public Users)
**Role:** `anonymous`  
**Authentication:** None required (no JWT)  
**Permissions:**
- ✅ Upload files
- ✅ List files
- ✅ View file metadata
- ✅ Download files
- ❌ Update/rename files
- ❌ Delete files
- ❌ Bulk operations

**Use Cases:**
- Public file sharing
- Anonymous uploads
- Public galleries

### 2. User (Authenticated Users)
**Role:** `user`  
**Authentication:** JWT (with or without explicit role)  
**Permissions:**
- ✅ All anonymous permissions
- ✅ Update file metadata
- ✅ Rename files
- ✅ Replace file content
- ❌ Delete files
- ❌ Bulk operations

**Use Cases:**
- Authenticated users managing their files
- Content creators and editors
- Collaborative file management

### 3. Admin
**Role:** `admin`  
**Authentication:** JWT with `role: "admin"`  
**Permissions:**
- ✅ All user permissions
- ✅ Soft delete files
- ✅ Permanent delete files
- ✅ View transaction history
- ✅ Bulk operations (delete, update, signed URLs)

**Use Cases:**
- System administrators
- Tenant administrators
- Data cleanup operations

## Endpoint Access Matrix

| Endpoint | Anonymous | User | Admin |
|----------|-----------|------|-------|
| `POST /upload` | ✅ | ✅ | ✅ |
| `GET /` | ✅ | ✅ | ✅ |
| `GET /:id` | ✅ | ✅ | ✅ |
| `GET /:id/download` | ✅ | ✅ | ✅ |
| `PATCH /:id` | ❌ | ✅ | ✅ |
| `PATCH /:id/rename` | ❌ | ✅ | ✅ |
| `PUT /:id/replace` | ❌ | ✅ | ✅ |
| `DELETE /:id` | ❌ | ❌ | ✅ |
| `DELETE /:id/permanent` | ❌ | ❌ | ✅ |
| `GET /:id/transactions` | ❌ | ❌ | ✅ |
| `POST /bulk/*` | ❌ | ❌ | ✅ |

## API Gateway Configuration

### Environment Variables

Both API Gateway and File Service must share the same secret:

**API Gateway (.env):**
```env
GATEWAY_INTERNAL_SECRET=your-strong-random-secret-min-32-chars
```

**File Service (.env):**
```env
GATEWAY_INTERNAL_SECRET=your-strong-random-secret-min-32-chars
```

⚠️ **Security:** Use a cryptographically strong random string (32+ characters). Never commit this to version control.

### JWT Payload Format

The API Gateway expects JWTs with the following payload:

```json
{
  "userId": "user-123",
  "sub": "user-123",
  "email": "user@example.com",
  "name": "John Doe",
  "role": "user",
  "iat": 1234567890,
  "exp": 1234571490
}
```

**Fields:**
- `userId` / `sub` / `id`: User identifier (any of these)
- `email`: User email address
- `role`: One of: `user`, `admin` (optional, defaults to `user`)
- `name`: Display name (optional)

### Anonymous User Handling

When no JWT is present, the gateway sets:
```
X-User-Id: anonymous
X-User-Email: anonymous@example.com
X-User-Role: anonymous
```

## Security

### HMAC Signature Verification

All user context headers are signed with HMAC-SHA256 to prevent tampering:

**Gateway signs:**
```javascript
const hmacPayload = `${userId}:${email}:${role}`;
const signature = crypto.createHmac('sha256', GATEWAY_INTERNAL_SECRET)
  .update(hmacPayload)
  .digest('hex');
// X-Gateway-HMAC: <signature>
```

**File service verifies:**
```javascript
const expectedHmac = crypto.createHmac('sha256', GATEWAY_INTERNAL_SECRET)
  .update(`${userId}:${email}:${role}`)
  .digest('hex');

if (providedHmac !== expectedHmac) {
  throw Error('Invalid signature - headers tampered');
}
```

### Best Practices

1. **Never expose file service directly** - Always route through API Gateway
2. **Use strong secrets** - Generate with `openssl rand -hex 32`
3. **Rotate secrets regularly** - Implement secret rotation strategy
4. **Log access attempts** - Monitor for unauthorized access patterns
5. **Use HTTPS only** - Never transmit headers over HTTP
6. **Validate tenant isolation** - Ensure users can only access their tenant's files

## Error Responses

### 401 Unauthorized
**When:** No authentication or invalid credentials
```json
{
  "success": false,
  "statusCode": 401,
  "message": "Authentication required",
  "error": {
    "code": "UNAUTHORIZED"
  }
}
```

### 403 Forbidden
**When:** Authenticated but insufficient permissions
```json
{
  "success": false,
  "statusCode": 403,
  "message": "Insufficient permissions. Required: file:delete, Your role: user",
  "error": {
    "code": "FORBIDDEN"
  }
}
```

### 400 Bad Request (Invalid Role)
**When:** Invalid role in X-User-Role header
```json
{
  "success": false,
  "statusCode": 400,
  "message": "Invalid role: superuser. Valid roles: anonymous, user, admin",
  "error": {
    "code": "BAD_REQUEST"
  }
}
```

## Testing RBAC

### 1. Test Anonymous Access (Public)

```bash
# Upload file (anonymous)
curl -X POST http://localhost:4001/api/files/upload \
  -H "X-User-Id: anonymous" \
  -H "X-User-Role: anonymous" \
  -H "X-User-Email: anonymous@example.com" \
  -H "X-Gateway-HMAC: <valid-signature>" \
  -F "files=@test.jpg"

# List files (anonymous)
curl http://localhost:4001/api/files \
  -H "X-User-Id: anonymous" \
  -H "X-User-Role: anonymous" \
  -H "X-User-Email: anonymous@example.com" \
  -H "X-Gateway-HMAC: <valid-signature>"
```

### 2. Test Authenticated User Access

```bash
# Update file metadata (requires user)
curl -X PATCH http://localhost:4001/api/files/{fileId} \
  -H "Content-Type: application/json" \
  -H "X-User-Id: user-123" \
  -H "X-User-Role: user" \
  -H "X-User-Email: user@example.com" \
  -H "X-Gateway-HMAC: <valid-signature>" \
  -d '{"description": "Updated by user"}'
```

### 3. Test Admin Access

```bash
# Delete file (requires admin)
curl -X DELETE http://localhost:4001/api/files/{fileId} \
  -H "X-User-Id: admin-456" \
  -H "X-User-Role: admin" \
  -H "X-User-Email: admin@example.com" \
  -H "X-Gateway-HMAC: <valid-signature>"
```

### 4. Test Permission Denial

```bash
# Try to delete as regular user (should fail with 403)
curl -X DELETE http://localhost:4001/api/files/{fileId} \
  -H "X-User-Id: user-123" \
  -H "X-User-Role: user" \
  -H "X-User-Email: user@example.com" \
  -H "X-Gateway-HMAC: <valid-signature>"
```

## Extending Permissions

To add new permissions or modify role capabilities:

1. **Update [src/config/permissions.js](../src/config/permissions.js)**:
```javascript
const PERMISSIONS = {
  // ... existing permissions
  FILE_ARCHIVE: 'file:archive',  // New permission
};

const ROLE_PERMISSIONS = {
  [ROLES.USER]: [
    // ... existing permissions
    PERMISSIONS.FILE_ARCHIVE,  // Grant to authenticated users
  ],
};
```

2. **Apply in route**:
```javascript
router.post('/:id/archive',
  requirePermission(PERMISSIONS.FILE_ARCHIVE),
  archiveFile
);
```

## Multi-Tenancy & RBAC

RBAC works seamlessly with multi-tenancy:

- **Anonymous users** can access files across tenants (if `TENANCY_ENABLED=true`, tenant is required in `X-Tenant-Id`)
- **Authenticated users** can only modify files within their tenant
- **Admins** have full access within their tenant only
- Cross-tenant access is **never** allowed (enforced at query level)

**Example:** An admin of `tenant-a` cannot delete files from `tenant-b`, even though they have the `admin` role.

## Troubleshooting

### "Missing gateway signature"
**Cause:** `X-Gateway-HMAC` header not provided  
**Fix:** Ensure API Gateway is setting the header

### "Invalid gateway signature"
**Cause:** HMAC verification failed  
**Fix:** 
- Verify `GATEWAY_INTERNAL_SECRET` matches between gateway and service
- Check header order in HMAC payload: `userId:email:role`
- Ensure no extra whitespace in header values

### "Invalid role: <role>"
**Cause:** Role not in allowed list  
**Fix:** Use only: `anonymous`, `user`, `admin`

### HMAC verification disabled warning
**Cause:** `GATEWAY_INTERNAL_SECRET` not set  
**Fix:** Set the environment variable (required for production)

---

**Related Documentation:**
- [Integration Guide](INTEGRATION_GUIDE.md) - General API usage
- [API Gateway README](../../Local-Service-Marketplace/api-gateway/README.md) - Gateway configuration
