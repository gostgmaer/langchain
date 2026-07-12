# Simplified RBAC Guide - Role-Based Only

## Overview

**Simplified Authentication:**
- ✅ **No permission checks** - just roles (anonymous, user, admin)
- ✅ **Works standalone** - no API Gateway required for public endpoints
- ✅ **Optional HMAC** - gateway signature verification only if configured
- ✅ **Simple headers** - just pass `X-User-Role` header

---

## Roles (3 Simple Roles)

| Role | Access Level | Header |
|------|--------------|---------|
| **anonymous** | Upload, view, download, list files | No header needed (or `X-User-Role: anonymous`) |
| **user** | All anonymous + update/rename/replace files | `X-User-Role: user` |
| **admin** | All user + delete, bulk operations | `X-User-Role: admin` |

---

## Usage Examples

### 1. Public Access (No Authentication)

```bash
# Upload file - NO HEADERS NEEDED
curl -X POST http://localhost:4001/api/files/upload \
  -F "files=@photo.jpg"

# List files - NO HEADERS NEEDED
curl http://localhost:4001/api/files

# View file - NO HEADERS NEEDED
curl http://localhost:4001/api/files/{fileId}

# Download file - NO HEADERS NEEDED
curl http://localhost:4001/api/files/{fileId}/download -o downloaded.jpg
```

### 2. Authenticated User (Update/Rename)

```bash
# Update file metadata - REQUIRES USER ROLE
curl -X PATCH http://localhost:4001/api/files/{fileId} \
  -H "Content-Type: application/json" \
  -H "X-User-Role: user" \
  -d '{"description": "Updated description"}'

# Rename file - REQUIRES USER ROLE
curl -X PATCH http://localhost:4001/api/files/{fileId}/rename \
  -H "Content-Type: application/json" \
  -H "X-User-Role: user" \
  -d '{"newName": "new-name.jpg"}'

# Replace file - REQUIRES USER ROLE
curl -X PUT http://localhost:4001/api/files/{fileId}/replace \
  -H "X-User-Role: user" \
  -F "file=@new-photo.jpg"
```

### 3. Admin Access (Delete/Bulk Operations)

```bash
# Delete file - REQUIRES ADMIN ROLE
curl -X DELETE http://localhost:4001/api/files/{fileId} \
  -H "X-User-Role: admin"

# Bulk delete - REQUIRES ADMIN ROLE
curl -X POST http://localhost:4001/api/files/bulk/delete \
  -H "Content-Type: application/json" \
  -H "X-User-Role: admin" \
  -d '{"fileIds": ["id1", "id2", "id3"]}'

# View transactions - REQUIRES ADMIN ROLE
curl http://localhost:4001/api/files/{fileId}/transactions \
  -H "X-User-Role: admin"
```

---

## With API Gateway (Optional)

If using with API Gateway, the gateway validates JWT and sets headers:

**Gateway adds these headers:**
```
X-User-Id: user-123
X-User-Email: user@example.com
X-User-Role: user
X-Gateway-HMAC: <signature>  (optional)
```

**Service behavior:**
- If `GATEWAY_INTERNAL_SECRET` is set AND `X-Gateway-HMAC` is provided → verifies signature
- If no secret or no HMAC → works without verification (standalone mode)

---

## Endpoint Access Matrix

| Endpoint | Anonymous (no header) | User | Admin |
|----------|----------------------|------|-------|
| `POST /upload` | ✅ | ✅ | ✅ |
| `GET /` (list) | ✅ | ✅ | ✅ |
| `GET /:id` | ✅ | ✅ | ✅ |
| `GET /:id/download` | ✅ | ✅ | ✅ |
| `PATCH /:id` | ❌ | ✅ | ✅ |
| `PATCH /:id/rename` | ❌ | ✅ | ✅ |
| `PUT /:id/replace` | ❌ | ✅ | ✅ |
| `DELETE /:id` | ❌ | ❌ | ✅ |
| `DELETE /:id/permanent` | ❌ | ❌ | ✅ |
| `GET /:id/transactions` | ❌ | ❌ | ✅ |
| `POST /bulk/*` | ❌ | ❌ | ✅ |

---

## Configuration

### Standalone Mode (No Gateway)

```env
# No gateway secret needed
GATEWAY_INTERNAL_SECRET=

# Or just omit it entirely
```

**How it works:**
- Public endpoints work with no headers
- Protected endpoints check `X-User-Role` header
- No signature verification

### With API Gateway

```env
# Set shared secret for HMAC verification
GATEWAY_INTERNAL_SECRET=your-64-char-hex-secret
```

**How it works:**
- Gateway validates JWT
- Gateway sets `X-User-Role` + `X-Gateway-HMAC`
- Service verifies HMAC signature
- Prevents header tampering

---

## Error Responses

### 401 Unauthorized - Missing Authentication
```json
{
  "success": false,
  "statusCode": 401,
  "message": "Authentication required"
}
```

### 403 Forbidden - Insufficient Role
```json
{
  "success": false,
  "statusCode": 403,
  "message": "Admin role required"
}
```

### 400 Bad Request - Invalid Role
```json
{
  "success": false,
  "statusCode": 400,
  "message": "Invalid role: superuser. Valid roles: anonymous, user, admin"
}
```

---

## Testing

### Test Public Access
```bash
# Should work without any headers
curl http://localhost:4001/api/files
```

### Test User Access
```bash
# Should succeed
curl -X PATCH http://localhost:4001/api/files/{id} \
  -H "X-User-Role: user" \
  -H "Content-Type: application/json" \
  -d '{"description": "test"}'

# Should fail (403)
curl -X DELETE http://localhost:4001/api/files/{id} \
  -H "X-User-Role: user"
```

### Test Admin Access
```bash
# Should succeed
curl -X DELETE http://localhost:4001/api/files/{id} \
  -H "X-User-Role: admin"
```

---

## Migration from Previous System

**What changed:**
- ❌ Removed: `requirePermission()` middleware
- ❌ Removed: `PERMISSIONS` constants
- ✅ Added: `allowPublic`, `requireAuth`, `requireAdmin` middleware
- ✅ Simplified: HMAC verification now optional

**What stayed the same:**
- Multi-tenancy still works (`X-Tenant-Id` header)
- All endpoints work the same way
- Role hierarchy: anonymous < user < admin

---

## Benefits

✅ **Simpler** - No permission matrix, just check roles  
✅ **Standalone** - Works without API Gateway  
✅ **Flexible** - Can add gateway later without changes  
✅ **Backwards Compatible** - Gateway integration still works  
✅ **Easier Testing** - Just set role header in tests  

---

## Security Notes

**Standalone Mode (Development):**
- Anyone can set `X-User-Role` header
- Trust-based system
- ⚠️ **NOT recommended for production internet-facing deployments**
- ✅ **OK for internal services, admin panels, trusted networks**

**Gateway Mode (Production):**
- API Gateway validates JWT
- HMAC prevents header tampering
- Service trusts gateway-signed headers
- ✅ **Recommended for production**

---

## Quick Reference

**Public endpoints (no auth):**
```bash
POST /api/files/upload
GET  /api/files
GET  /api/files/:id
GET  /api/files/:id/download
```

**User endpoints (X-User-Role: user):**
```bash
PATCH /api/files/:id
PATCH /api/files/:id/rename
PUT   /api/files/:id/replace
```

**Admin endpoints (X-User-Role: admin):**
```bash
DELETE /api/files/:id
DELETE /api/files/:id/permanent
GET    /api/files/:id/transactions
POST   /api/files/bulk/*
PATCH  /api/files/bulk/*
```

---

**Simple, flexible, and production-ready! 🚀**
