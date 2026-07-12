# File Upload Microservice — Integration Guide

## Table of Contents

1. [Overview](#1-overview)
2. [Quick Start](#2-quick-start)
3. [Base URL & Environments](#3-base-url--environments)
4. [Header Contract](#4-header-contract)
5. [Response Format](#5-response-format)
6. [Error Reference](#6-error-reference)
7. [API Endpoints](#7-api-endpoints)
8. [Code Examples](#8-code-examples)
   - [Node.js / axios](#nodejs--axios)
   - [Python / requests](#python--requests)
   - [cURL](#curl)
9. [Integration Patterns](#9-integration-patterns)
   - [Proxy from a Node.js monolith](#proxy-from-a-nodejs-monolith)
   - [Direct frontend integration](#direct-frontend-integration)
   - [Server-to-server integration](#server-to-server-integration)
10. [Multi-Tenancy](#10-multi-tenancy)
11. [Rate Limiting](#11-rate-limiting)
12. [Storage Backends](#12-storage-backends)
13. [Docker Deployment](#13-docker-deployment)
14. [Troubleshooting](#14-troubleshooting)

---

## 1. Overview

The **File Upload Microservice** is a standalone Node.js/Express service that handles all file operations:

| Capability | Details |
|---|---|
| **Upload** | Up to 10 files per request, multipart/form-data |
| **Download** | Stream as attachment or inline; pre-signed URLs for cloud storage |
| **List / Search** | Filter by MIME, category, tags, language, visibility, linked entity, date range; sortable; paginated |
| **Rename** | Update display name without moving the storage object |
| **Update Metadata** | Category, description, title, alt text, author, source, language, expiry, visibility, tags, custom KV, entity link |
| **Replace** | Swap binary content; previous versions are archived |
| **Delete** | Soft delete (recoverable) or permanent delete |
| **Audit Trail** | Every operation is logged as an immutable transaction |
| **Multi-tenancy** | Full tenant isolation via `X-Tenant-Id` header; defaults to `DEFAULT_TENANT_ID` if omitted |
| **Storage backends** | Local disk · AWS S3 · GCS · Azure Blob · Cloudflare R2 |

**Authentication is NOT handled by this service.** Auth is delegated to your API gateway (Kong, AWS API Gateway, nginx, or your main backend). The service trusts all incoming requests and reads identity from two injected headers: `X-Tenant-Id` and `X-User-Id`.

---

## 2. Quick Start

### Start with Docker (recommended)

```bash
# Clone / navigate to the service directory
cd file-upload-service

# Copy and configure environment
cp .env.example .env
# Edit .env — at minimum set MONGO_URI and STORAGE_TYPE

# Start everything
docker compose up -d

# Verify
curl http://localhost:4001/health
# → {"status":"ok","db":"connected","timestamp":"..."}
```

### Start without Docker

```bash
cd file-upload-service
npm install
cp .env.example .env
# Edit .env

node server.js
# or for development:
npm run dev
```

### First request — upload a file

```bash
curl -X POST http://localhost:4001/api/files/upload \
  -H "X-Tenant-Id: my-tenant" \
  -H "X-User-Id: user-123" \
  -F "files=@/path/to/photo.jpg" \
  -F "description=My first upload"
```

---

## 3. Base URL & Environments

| Environment | Default URL |
|---|---|
| Local dev | `http://localhost:4001` |
| Docker Compose | `http://file-upload-service:4001` (internal) |
| Production | Your deployed URL, e.g. `https://files.yourdomain.com` |

Set `FILE_SERVICE_URL` in your main service's `.env` when using the proxy pattern.

---

## 4. Header Contract

Every request to `/api/files/*` should include these headers:

| Header | Required | Type | Description |
|---|---|---|---|
| `X-Tenant-Id` | Optional | `string` | Tenant identifier. If omitted, falls back to the `DEFAULT_TENANT_ID` env var (default: `"default"`). Set this on every request in a multi-tenant setup. |
| `X-User-Id` | Optional | `string` | Authenticated user ID. Used to populate `uploader` on new files and `performedBy` on transactions. If omitted, defaults to `'anonymous'`. |
| `X-User-Role` | Optional | `string` | User role (e.g. `admin`, `editor`). Stored for future access-control policies. |

> **Who sets these headers?**
> Your upstream API gateway or main backend service is responsible for verifying the auth token and then injecting these headers before forwarding requests to the file service. The file service reads them as trusted facts.

---

## 5. Response Format

All responses follow the same envelope structure.

### Success Response

```json
{
  "success": true,
  "statusCode": 200,
  "message": "Files retrieved successfully",
  "data": { ... }
}
```

### Error Response

```json
{
  "success": false,
  "statusCode": 400,
  "message": "Human-readable error description",
  "error": {
    "code": "VALIDATION_ERROR",
    "errors": [
      { "field": "tenantId", "message": "Path `tenantId` is required." }
    ]
  }
}
```

> In `NODE_ENV=development`, the `error.details` field additionally includes the full stack trace.

### Upload Success Data Shape

```json
{
  "data": [
    {
      "id": "6650a1234b5678c9d0e1f234",
      "originalName": "photo.jpg",
      "size": 204800,
      "mimeType": "image/jpeg",
      "category": "avatar",
      "url": "/uploads/files/my-tenant/user-123/1741234567890-uuid-photo.jpg",
      "metadata": {
        "description": "My first upload",
        "title": "Profile photo",
        "altText": "A photo of a mountain",
        "author": "",
        "source": "",
        "language": "en",
        "expiresAt": null,
        "isPublic": false,
        "tags": ["photo"],
        "custom": {},
        "linkedTo": {}
      }
    }
  ]
}
```

### File Object Shape (GET by ID, update, rename)

```json
{
  "data": {
    "_id": "6650a1234b5678c9d0e1f234",
    "tenantId": "my-tenant",
    "originalName": "photo.jpg",
    "storageKey": "files/my-tenant/user-123/1741234567890-uuid-photo.jpg",
    "size": 204800,
    "mimeType": "image/jpeg",
    "extension": ".jpg",
    "uploader": "user-123",
    "publicUrl": "/uploads/files/my-tenant/user-123/...",
    "category": "avatar",
    "metadata": {
      "description": "My first upload",
      "title": "Profile photo",
      "altText": "A photo of a mountain",
      "author": "Jane Smith",
      "source": "https://example.com/original",
      "language": "en",
      "expiresAt": null,
      "isPublic": false,
      "tags": ["photo"],
      "custom": { "project": "Q1" },
      "linkedTo": {
        "entityType": "product",
        "entityId": "prod_abc123"
      }
    },
    "versions": [],
    "status": "active",
    "createdAt": "2026-03-06T10:00:00.000Z",
    "updatedAt": "2026-03-06T10:05:00.000Z"
  }
}
```

### List Response Data Shape

```json
{
  "data": {
    "files": [ ...File objects... ],
    "pagination": {
      "page": 1,
      "limit": 20,
      "total": 87,
      "pages": 5
    }
  }
}
```

### Transaction Object Shape

```json
{
  "_id": "...",
  "tenantId": "my-tenant",
  "fileId": "6650a1234b5678c9d0e1f234",
  "operation": "upload",
  "status": "success",
  "performedBy": "user-123",
  "requestId": "uuid-v4",
  "payload": { "originalName": "photo.jpg", "size": 204800 },
  "providerResponse": { "location": "..." },
  "createdAt": "2026-03-06T10:00:00.000Z",
  "updatedAt": "2026-03-06T10:00:00.001Z"
}
```

---

## 6. Error Reference

| HTTP Status | `error.code` | When |
|---|---|---|
| `400 Bad Request` | `BAD_REQUEST` | Missing required field, wrong field name, file not provided |
| `400 Bad Request` | `VALIDATION_ERROR` | Joi schema failure, Mongoose validation failure, malformed JSON |
| `404 Not Found` | `NOT_FOUND` | File ID not found in this tenant, or route doesn't exist |
| `409 Conflict` | `DUPLICATE_ENTRY` | Duplicate MongoDB document (rare — unique index collision) |
| `413 Payload Too Large` | `VALIDATION_ERROR` | File exceeds `MAX_FILE_SIZE` |
| `415 Unsupported Media Type` | `VALIDATION_ERROR` | MIME type not in `ALLOWED_MIME_TYPES` |
| `429 Too Many Requests` | `RATE_LIMIT_EXCEEDED` | Upload rate limit exceeded |
| `500 Internal Server Error` | `INTERNAL_ERROR` | Unexpected server error |
| `503 Service Unavailable` | `INTERNAL_ERROR` | MongoDB connection error |

---

## 7. API Endpoints

Base path: `/api/files`

---

### `POST /api/files/upload`

Upload one or more files.

**Headers:** `X-Tenant-Id` (required for write), `X-User-Id` (optional)

**Body:** `multipart/form-data`

| Field | Type | Required | Description |
|---|---|---|---|
| `files` | file | Yes | Up to 10 files. Field name must be `files` (plural). |
| `category` | string | No | Top-level category label, e.g. `invoice`, `avatar`. Max 100 chars. |
| `description` | string | No | Description text. Max 1000 chars. |
| `tags` | string | No | Repeat the field for multiple tags, e.g. `tags=invoice&tags=2025`. |
| `custom` | string | No | JSON-serialized object for arbitrary key-value metadata. |
| `title` | string | No | Display title separate from the filename. Max 255 chars. |
| `altText` | string | No | Accessibility alt text (especially useful for images). Max 500 chars. |
| `author` | string | No | Document/content author name. Max 255 chars. |
| `source` | string | No | Origin URL or reference string. Max 500 chars. |
| `language` | string | No | ISO 639-1 language code, e.g. `en`, `fr`, `de`. Max 10 chars. |
| `expiresAt` | ISO 8601 date | No | Optional expiry datetime. Must be in the future. |
| `isPublic` | boolean | No | Public visibility flag. Defaults to `false`. Send `"true"` or `"false"` as a string in form-data. |
| `linkedEntityType` | string | No | Type of the linked entity, e.g. `product`, `user`, `invoice`. Max 100 chars. |
| `linkedEntityId` | string | No | ID of the linked entity. Max 255 chars. |

**Returns:** `201 Created` + array of uploaded file summaries.

---

### `GET /api/files`

List files for the tenant with optional filtering, sorting, and pagination.

**Headers:** `X-Tenant-Id`

**Query Parameters:**

| Param | Type | Default | Description |
|---|---|---|---|
| `page` | number | 1 | Page number (1-based) |
| `limit` | number | 20 | Items per page (max 100) |
| `sort` | string | `createdAt` | Sort field. Prefix `-` for descending. Allowed: `originalName`, `size`, `createdAt`, `updatedAt` |
| `search` | string | — | Search `originalName` and `metadata.description` (case-insensitive) |
| `mimeType` | string | — | Exact MIME type, e.g. `image/jpeg` |
| `category` | string | — | Exact category label |
| `tags` | string | — | Repeat for multiple. OR logic. |
| `uploader` | string | — | Filter by uploader user ID |
| `language` | string | — | Filter by ISO 639-1 language code, e.g. `en` |
| `isPublic` | boolean | — | Filter by visibility flag. Send `true` or `false`. |
| `linkedEntityType` | string | — | Filter by linked entity type, e.g. `product` |
| `linkedEntityId` | string | — | Filter by linked entity ID |
| `dateFrom` | ISO 8601 date | — | Inclusive start date |
| `dateTo` | ISO 8601 date | — | Inclusive end date |

**Returns:** `200 OK` + `{ files: [...], pagination: {...} }`

---

### `GET /api/files/:id`

Get full metadata for a single file.

**Headers:** `X-Tenant-Id`

**Returns:** `200 OK` + File object. `404` if not found or belongs to a different tenant.

---

### `GET /api/files/:id/download`

Download or preview a file.

**Headers:** `X-Tenant-Id`

**Query Parameters:**

| Param | Value | Description |
|---|---|---|
| `inline` | `1` | Set `Content-Disposition: inline` so browsers preview the file |
| `signed` | `1` | Redirect to a pre-signed URL (cloud storage only; local falls back to stream) |

**Returns:** File binary stream (200) or redirect to signed URL (302).

---

### `PATCH /api/files/:id/rename`

Rename a file's display name. The storage key (path on disk/cloud) is NOT changed.

**Headers:** `X-Tenant-Id`, `Content-Type: application/json`

**Body:**

```json
{ "name": "new-filename.pdf" }
```

| Field | Type | Required | Constraints |
|---|---|---|---|
| `name` | string | Yes | 1–255 characters, trimmed |

**Returns:** `200 OK` + `{ file: {...}, requestId: "..." }`

---

### `PATCH /api/files/:id`

Update file metadata. At least one field must be provided.

**Headers:** `X-Tenant-Id`, `Content-Type: application/json`

**Body:**

```json
{
  "originalName": "new-display-name.jpg",
  "category": "invoice",
  "metadata": {
    "description": "Updated description",
    "title": "Q1 Invoice",
    "altText": "Invoice document thumbnail",
    "author": "Jane Smith",
    "source": "https://erp.example.com/invoices/123",
    "language": "en",
    "expiresAt": "2027-01-01T00:00:00.000Z",
    "isPublic": false,
    "tags": ["tag1", "tag2"],
    "custom": { "project": "Q1", "reviewed": true },
    "linkedTo": {
      "entityType": "product",
      "entityId": "prod_abc123"
    }
  }
}
```

| Field | Description |
|---|---|
| `originalName` | New display filename. Max 255 chars. |
| `category` | Top-level category label. Pass `""` to clear. |
| `metadata.description` | Description text. Max 1000 chars. |
| `metadata.title` | Display title. Max 255 chars. |
| `metadata.altText` | Accessibility alt text. Max 500 chars. |
| `metadata.author` | Author name. Max 255 chars. |
| `metadata.source` | Origin URL or reference. Max 500 chars. |
| `metadata.language` | ISO 639-1 language code. Max 10 chars. |
| `metadata.expiresAt` | Expiry datetime (ISO 8601). |
| `metadata.isPublic` | Visibility boolean. |
| `metadata.tags` | Full replacement of the tags array. |
| `metadata.custom` | Full replacement of the custom object. |
| `metadata.linkedTo` | Entity reference: `{ entityType, entityId }`. |

**Returns:** `200 OK` + `{ file: {...}, requestId: "..." }`

---

### `PUT /api/files/:id/replace`

Replace the binary content of an existing file. The old version is archived in `file.versions[]`.

**Headers:** `X-Tenant-Id`, `X-User-Id`

**Body:** `multipart/form-data`

| Field | Type | Required | Description |
|---|---|---|---|
| `file` | file | Yes | New file content. Field name must be `file` (singular). |

**Returns:** `200 OK` + `{ file: {...}, requestId: "..." }`

---

### `DELETE /api/files/:id`

Soft delete — marks `status: 'deleted'`. The MongoDB record and storage object are preserved.

**Headers:** `X-Tenant-Id`

**Returns:** `200 OK` + `{ file: { status: "deleted", ... }, requestId: "..." }`

---

### `DELETE /api/files/:id/permanent`

Permanently removes the MongoDB record AND the storage object (including all archived versions).

**Headers:** `X-Tenant-Id`

**Returns:** `200 OK` + `{ requestId: "..." }`

> ⚠️ This operation is irreversible.

---

### `GET /api/files/:id/transactions`

Get the full audit trail for a file (newest first).

**Headers:** `X-Tenant-Id`

**Returns:** `200 OK` + array of Transaction objects.

Transaction `operation` values: `upload` · `rename` · `update_metadata` · `replace` · `delete` · `permanent_delete`

---

### `GET /health`

Health check. No headers required.

**Returns:**

```json
{
  "status": "ok",
  "service": "file-upload-service",
  "version": "1.0.0",
  "timestamp": "2026-03-07T10:00:00.000Z",
  "uptime": 3725,
  "db": "connected",
  "memory": {
    "heapUsedMB": 42,
    "heapTotalMB": 67,
    "rssMB": 89
  }
}
```

Returns `200` when DB is connected, `503` when disconnected.

---

## 8. Code Examples

### Node.js / axios

**Install:**

```bash
npm install axios form-data
```

#### Upload a file

```js
const axios = require('axios');
const FormData = require('form-data');
const fs = require('fs');

const FILE_SERVICE = process.env.FILE_SERVICE_URL || 'http://localhost:4001';

async function uploadFile(filePath, tenantId, userId, metadata = {}) {
  const form = new FormData();
  form.append('files', fs.createReadStream(filePath));
  if (metadata.description) form.append('description', metadata.description);
  if (metadata.tags) metadata.tags.forEach(tag => form.append('tags', tag));

  const response = await axios.post(`${FILE_SERVICE}/api/files/upload`, form, {
    headers: {
      ...form.getHeaders(),
      'X-Tenant-Id': tenantId,
      'X-User-Id': userId,
    },
    maxBodyLength: Infinity,  // Required for large files
  });

  return response.data.data;  // Array of uploaded file summaries
}

// Usage
uploadFile('./invoice.pdf', 'tenant-a', 'user-123', {
  description: 'Q1 invoice',
  tags: ['invoice', '2026'],
}).then(files => console.log('Uploaded:', files[0].id));
```

#### List files

```js
async function listFiles(tenantId, options = {}) {
  const params = new URLSearchParams();
  if (options.page)     params.set('page', options.page);
  if (options.limit)    params.set('limit', options.limit);
  if (options.search)   params.set('search', options.search);
  if (options.mimeType) params.set('mimeType', options.mimeType);
  if (options.sort)     params.set('sort', options.sort);
  if (options.tags)     options.tags.forEach(t => params.append('tags', t));

  const response = await axios.get(`${FILE_SERVICE}/api/files?${params}`, {
    headers: { 'X-Tenant-Id': tenantId },
  });

  return response.data.data;  // { files: [...], pagination: {...} }
}

// Usage
const result = await listFiles('tenant-a', {
  search: 'invoice',
  sort: '-createdAt',
  page: 1,
  limit: 10,
});
console.log(`Found ${result.pagination.total} files`);
```

#### Download and save to disk

```js
const path = require('path');

async function downloadFile(fileId, tenantId, savePath) {
  const response = await axios.get(
    `${FILE_SERVICE}/api/files/${fileId}/download`,
    {
      headers: { 'X-Tenant-Id': tenantId },
      responseType: 'stream',
    }
  );

  const writer = fs.createWriteStream(savePath);
  response.data.pipe(writer);

  return new Promise((resolve, reject) => {
    writer.on('finish', resolve);
    writer.on('error', reject);
  });
}

// Usage
await downloadFile('6650a123...', 'tenant-a', './downloads/invoice.pdf');
```

#### Rename a file

```js
async function renameFile(fileId, newName, tenantId, userId) {
  const response = await axios.patch(
    `${FILE_SERVICE}/api/files/${fileId}/rename`,
    { name: newName },
    { headers: { 'X-Tenant-Id': tenantId, 'X-User-Id': userId } }
  );
  return response.data.data.file;
}
```

#### Delete (soft)

```js
async function deleteFile(fileId, tenantId, userId, permanent = false) {
  const url = permanent
    ? `${FILE_SERVICE}/api/files/${fileId}/permanent`
    : `${FILE_SERVICE}/api/files/${fileId}`;

  const response = await axios.delete(url, {
    headers: { 'X-Tenant-Id': tenantId, 'X-User-Id': userId },
  });
  return response.data;
}
```

#### Error handling wrapper

```js
async function fileServiceCall(fn) {
  try {
    return await fn();
  } catch (err) {
    if (err.response) {
      // File service returned an error response
      const { statusCode, message, error } = err.response.data;
      console.error(`File service error ${statusCode}: ${message} (${error?.code})`);
      throw new Error(message);
    }
    if (err.code === 'ECONNREFUSED') {
      throw new Error('File service is unavailable');
    }
    throw err;
  }
}

// Usage
const files = await fileServiceCall(() => listFiles('tenant-a'));
```

---

### Python / requests

```python
import requests
import os

FILE_SERVICE = os.getenv("FILE_SERVICE_URL", "http://localhost:4001")


def upload_file(file_path: str, tenant_id: str, user_id: str, description: str = "", tags: list = None):
    with open(file_path, "rb") as f:
        files = [("files", (os.path.basename(file_path), f))]
        data = {"description": description}
        if tags:
            data["tags"] = tags  # requests sends repeated keys as list

        response = requests.post(
            f"{FILE_SERVICE}/api/files/upload",
            headers={"X-Tenant-Id": tenant_id, "X-User-Id": user_id},
            files=files,
            data=data,
        )
    response.raise_for_status()
    return response.json()["data"]


def list_files(tenant_id: str, search: str = None, page: int = 1, limit: int = 20):
    params = {"page": page, "limit": limit}
    if search:
        params["search"] = search

    response = requests.get(
        f"{FILE_SERVICE}/api/files",
        headers={"X-Tenant-Id": tenant_id},
        params=params,
    )
    response.raise_for_status()
    return response.json()["data"]


def download_file(file_id: str, tenant_id: str, save_path: str):
    response = requests.get(
        f"{FILE_SERVICE}/api/files/{file_id}/download",
        headers={"X-Tenant-Id": tenant_id},
        stream=True,
    )
    response.raise_for_status()

    with open(save_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)


def rename_file(file_id: str, new_name: str, tenant_id: str, user_id: str = None):
    headers = {"X-Tenant-Id": tenant_id}
    if user_id:
        headers["X-User-Id"] = user_id

    response = requests.patch(
        f"{FILE_SERVICE}/api/files/{file_id}/rename",
        headers=headers,
        json={"name": new_name},
    )
    response.raise_for_status()
    return response.json()["data"]["file"]


def delete_file(file_id: str, tenant_id: str, permanent: bool = False):
    url = f"{FILE_SERVICE}/api/files/{file_id}"
    if permanent:
        url += "/permanent"

    response = requests.delete(url, headers={"X-Tenant-Id": tenant_id})
    response.raise_for_status()
    return response.json()


# Usage example
if __name__ == "__main__":
    # Upload
    uploaded = upload_file("./report.pdf", "tenant-a", "user-123",
                           description="Q1 report", tags=["report", "2026"])
    file_id = uploaded[0]["id"]
    print(f"Uploaded: {file_id}")

    # List
    result = list_files("tenant-a", search="report")
    print(f"Found {result['pagination']['total']} files")

    # Rename
    renamed = rename_file(file_id, "q1-report-final.pdf", "tenant-a", "user-123")
    print(f"Renamed to: {renamed['originalName']}")

    # Download
    download_file(file_id, "tenant-a", "./downloads/q1-report-final.pdf")
```

---

### cURL

#### Upload

```bash
curl -X POST http://localhost:4001/api/files/upload \
  -H "X-Tenant-Id: tenant-a" \
  -H "X-User-Id: user-123" \
  -F "files=@/path/to/photo.jpg" \
  -F "files=@/path/to/document.pdf" \
  -F "description=Batch upload" \
  -F "tags=photo" \
  -F "tags=batch"
```

#### List with filters

```bash
curl "http://localhost:4001/api/files?search=invoice&sort=-createdAt&limit=5" \
  -H "X-Tenant-Id: tenant-a"
```

#### Download file

```bash
# Save to disk
curl -o invoice.pdf \
  -H "X-Tenant-Id: tenant-a" \
  "http://localhost:4001/api/files/6650a123.../download"

# Preview (inline)
curl -H "X-Tenant-Id: tenant-a" \
  "http://localhost:4001/api/files/6650a123.../download?inline=1"
```

#### Rename file

```bash
curl -X PATCH http://localhost:4001/api/files/6650a123.../rename \
  -H "X-Tenant-Id: tenant-a" \
  -H "Content-Type: application/json" \
  -d '{"name": "new-filename.pdf"}'
```

#### Update metadata

```bash
curl -X PATCH http://localhost:4001/api/files/6650a123... \
  -H "X-Tenant-Id: tenant-a" \
  -H "Content-Type: application/json" \
  -d '{
    "metadata": {
      "description": "Updated description",
      "tags": ["invoice", "approved"],
      "custom": {"approvedBy": "manager-1"}
    }
  }'
```

#### Replace file content

```bash
curl -X PUT http://localhost:4001/api/files/6650a123.../replace \
  -H "X-Tenant-Id: tenant-a" \
  -H "X-User-Id: user-123" \
  -F "file=@/path/to/new-version.pdf"
```

#### Soft delete

```bash
curl -X DELETE http://localhost:4001/api/files/6650a123... \
  -H "X-Tenant-Id: tenant-a"
```

#### Permanent delete

```bash
curl -X DELETE http://localhost:4001/api/files/6650a123.../permanent \
  -H "X-Tenant-Id: tenant-a"
```

#### Get transactions

```bash
curl -H "X-Tenant-Id: tenant-a" \
  http://localhost:4001/api/files/6650a123.../transactions
```

---

## 9. Integration Patterns

### Proxy from a Node.js monolith

This is the recommended pattern when your main API already handles authentication. Install and configure a streaming proxy so multipart uploads are forwarded without buffering the entire file in memory.

```bash
# In your main service
npm install http-proxy-middleware
```

```js
// src/proxies/fileServiceProxy.js
const { createProxyMiddleware } = require('http-proxy-middleware');

const FILE_SERVICE_URL = process.env.FILE_SERVICE_URL || 'http://localhost:4001';

const fileServiceProxy = createProxyMiddleware({
  target: FILE_SERVICE_URL,
  changeOrigin: true,
  selfHandleResponse: false,
  on: {
    proxyReq: (proxyReq, req) => {
      // Inject identity headers resolved by your auth middleware
      if (req.tenantId)    proxyReq.setHeader('X-Tenant-Id', req.tenantId);
      if (req.user?.id)    proxyReq.setHeader('X-User-Id', req.user.id);
      if (req.user?.role)  proxyReq.setHeader('X-User-Role', req.user.role);
    },
    error: (err, req, res) => {
      res.status(502).json({ success: false, message: 'File service unavailable' });
    },
  },
});

module.exports = { fileServiceProxy };
```

```js
// app.js — mount BEFORE any body-parser middleware
const { fileServiceProxy } = require('./src/proxies/fileServiceProxy');

// ⚠️ This MUST come before express.json() and express.urlencoded()
app.use('/api/files', fileServiceProxy);

// Body parsers come after
app.use(express.json());
app.use(express.urlencoded({ extended: true }));
```

> **Why before body-parser?** Multer in the file service reads the raw multipart stream. If Express in the main service parses the body first, the stream is consumed and the file service receives an empty body.

Add to your main service `.env`:
```dotenv
FILE_SERVICE_URL=http://localhost:4001
```

---

### Direct frontend integration

If your frontend talks to the file service directly (via CORS), the gateway or backend must inject headers before the request reaches the service. The most common pattern is a lightweight token exchange:

1. Frontend requests a short-lived upload token from your main API: `POST /api/upload-token`
2. Main API verifies the user, generates a signed token containing `{ tenantId, userId, role }`, returns it
3. Frontend sends the token to the file service in a custom header, OR your NGINX/API Gateway validates it and injects the `X-Tenant-Id` / `X-User-Id` headers

```js
// Example: frontend using fetch
async function uploadFile(file, uploadToken) {
  const form = new FormData();
  form.append('files', file);

  const response = await fetch('https://files.yourdomain.com/api/files/upload', {
    method: 'POST',
    headers: {
      'X-Tenant-Id': currentTenantId,    // Set by your app context
      'X-User-Id': currentUserId,        // Set by your auth context  
      'Authorization': `Bearer ${uploadToken}`  // Validated by gateway
    },
    body: form,
  });

  const data = await response.json();
  if (!data.success) throw new Error(data.message);
  return data.data;
}
```

---

### Server-to-server integration

When a backend service calls the file service directly (e.g. a report generator saves PDFs):

```js
// Node.js backend service calling file service
const { Readable } = require('stream');
const FormData = require('form-data');
const axios = require('axios');

async function savePDFToFileService(pdfBuffer, filename, tenantId, metadata = {}) {
  const form = new FormData();

  // Append buffer as a file
  form.append('files', pdfBuffer, {
    filename,
    contentType: 'application/pdf',
    knownLength: pdfBuffer.length,
  });

  if (metadata.description) form.append('description', metadata.description);
  if (metadata.tags) metadata.tags.forEach(tag => form.append('tags', tag));

  const response = await axios.post(
    `${process.env.FILE_SERVICE_URL}/api/files/upload`,
    form,
    {
      headers: {
        ...form.getHeaders(),
        'X-Tenant-Id': tenantId,
        'X-User-Id': 'system',    // Use a service account identifier
        'X-User-Role': 'service',
      },
      maxBodyLength: Infinity,
    }
  );

  return response.data.data[0];  // Return first uploaded file
}
```

---

## 10. Multi-Tenancy

### How it works

Every file record, query, and storage path is namespaced by `tenantId` from the `X-Tenant-Id` header.

- **Storage path:** `files/{tenantId}/{userId}/{timestamp}-{uuid}-{name}{ext}`
- **Database queries:** all reads include `{ tenantId }` as a filter — cross-tenant ID lookups return `404`
- **Indexes:** compound indexes on `{tenantId, status}`, `{tenantId, createdAt}`, etc. for performance

### Tenant isolation modes

Set via `TENANCY_MODE` in `.env`:

| Mode | Description | Use when |
|---|---|---|
| `shared` (default) | Single MongoDB database, `tenantId` field on every document | Most SaaS applications, simpler ops |
| `per-db` | Each tenant gets its own MongoDB database, lazy-created | Regulatory requirements, strict data isolation |

### Shared mode (default)

```dotenv
TENANCY_MODE=shared
MONGO_URI=mongodb://localhost:27017/file_service_db
```

All tenants share one database. Tenant isolation is enforced entirely at the query level.

### Per-DB mode

```dotenv
TENANCY_MODE=per-db
MONGO_URI=mongodb://localhost:27017/{tenant}_file_db
```

The `{tenant}` placeholder is replaced at runtime with the actual tenant ID. Each tenant's data is in a separate database (e.g. `tenant_a_file_db`, `tenant_b_file_db`).

---

## 11. Rate Limiting

Upload requests are rate-limited per IP address.

| Variable | Default | Description |
|---|---|---|
| `UPLOAD_RATE_LIMIT` | `10` | Max upload requests per window |
| `UPLOAD_RATE_WINDOW` | `900000` | Window duration in ms (15 minutes) |

When the limit is exceeded, the service returns:

```json
{
  "success": false,
  "statusCode": 429,
  "message": "Too many upload requests, please try again later.",
  "error": { "code": "RATE_LIMIT_EXCEEDED" }
}
```

The response includes a `Retry-After` header with the number of seconds until the window resets.

To increase limits for trusted internal services, use a higher limit in your env and restrict access at the network level (VPC, nginx `allow`/`deny`).

---

## 12. Storage Backends

Select via `STORAGE_TYPE` in `.env`.

### Local Disk (default)

```dotenv
STORAGE_TYPE=local
LOCAL_UPLOAD_DIR=uploads
```

Files are stored at `{LOCAL_UPLOAD_DIR}/files/{tenantId}/...`. Make sure the directory is writable and that you mount a volume in Docker.

### AWS S3

```dotenv
STORAGE_TYPE=s3
S3_BUCKET=your-bucket-name
S3_REGION=us-east-1
S3_ACCESS_KEY=AKIA...
S3_SECRET_KEY=...
```

### Cloudflare R2 (S3-compatible)

```dotenv
STORAGE_TYPE=r2
R2_ENDPOINT=https://<account-id>.r2.cloudflarestorage.com
R2_ACCESS_KEY=...
R2_SECRET=...
R2_BUCKET=your-bucket-name
```

### Google Cloud Storage

```dotenv
STORAGE_TYPE=gcs
GCS_BUCKET=your-bucket-name
GCS_PROJECT_ID=my-project
GCS_KEY_FILE=./src/config/service-account.json
```

### Azure Blob Storage

```dotenv
STORAGE_TYPE=azure
AZURE_CONNECTION_STRING=DefaultEndpointsProtocol=https;AccountName=...
AZURE_CONTAINER=your-container-name
```

---

## 13. Docker Deployment

### Development

```bash
cp .env.example .env
# Set MONGO_PASS in .env (required by docker-compose)
docker compose up
```

This starts:
- **file-upload-service** on port `4001`  
- **mongo** on port `27018` (bound to `127.0.0.1` only — not accessible from outside the host)

The service waits for MongoDB to pass its health check before starting.

### Production Dockerfile

The Dockerfile runs as a **non-root user**, sets `NODE_ENV=production`, and registers a Docker-level health check:

```dockerfile
FROM node:20-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci --omit=dev
COPY . .
RUN addgroup -S appgroup && adduser -S appuser -G appgroup \
  && mkdir -p /app/uploads && chown -R appuser:appgroup /app/uploads
USER appuser
EXPOSE 4001
ENV NODE_ENV=production
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD wget -qO- http://localhost:4001/health || exit 1
CMD ["node", "server.js"]
```

```bash
# Build and run standalone
docker build -t file-upload-service .
docker run -d \
  -p 4001:4001 \
  --env-file .env \
  -v $(pwd)/uploads:/app/uploads \
  file-upload-service
```

### Environment variables checklist

Required for all modes:
```dotenv
MONGO_URI=mongodb://...
MONGO_PASS=your-strong-password     # Required for docker-compose MongoDB auth
STORAGE_TYPE=local                  # or s3, gcs, azure, r2
NODE_ENV=production
CORS_ORIGIN=https://yourdomain.com  # Comma-separated for multiple origins
DEFAULT_TENANT_ID=default           # Fallback when X-Tenant-Id header is absent
```

Add the appropriate backend credentials based on `STORAGE_TYPE`.

---

## 14. Troubleshooting

### `400 Validation failed — tenantId is required`

This error should no longer occur since `X-Tenant-Id` now defaults to the `DEFAULT_TENANT_ID` env var (`"default"` if not set). If you see it, check that `DEFAULT_TENANT_ID` is configured in your `.env`.

### `400 Unexpected field 'file'`

You used `file` (singular) for the upload endpoint. Use `files` (plural). The `/replace` endpoint uses `file` (singular).

### `400 Unexpected field 'files'`

You used `files` (plural) for the replace endpoint. Use `file` (singular).

### `413 File too large`

The uploaded file exceeds `MAX_FILE_SIZE` (default 10 MB). Either increase this env var or compress the file before uploading.

### `415 File type X not allowed`

The file's MIME type is not in `ALLOWED_MIME_TYPES`. Add the MIME type to the env var (comma-separated) and restart the service.

### Downloads always return `404 Route not found`

Make sure your proxy (or API gateway) does not strip the trailing path segments. The download URL is `/api/files/:id/download`.

### `502 File service unavailable` (from proxy)

The main service cannot reach the file service. Check:
1. `FILE_SERVICE_URL` env var in your main service is correct
2. The file service is running: `curl http://localhost:4001/health`
3. Network/firewall rules between services

### Uploads hang or timeout through the proxy

The proxy middleware must be mounted **before** `express.json()` and `express.urlencoded()`. If body parsers run first they consume the multipart stream; the file service then gets an empty body.

### Files appear in MongoDB but not on disk / in cloud

The `publicUrl` stored in the DB is the value returned by the storage adapter at upload time. For local storage it's a relative path under `LOCAL_UPLOAD_DIR`. Ensure:
1. The volume is mounted correctly in Docker
2. `LOCAL_UPLOAD_DIR` is consistent between the write path and the serving path

### Cross-tenant file access returns `404` (expected behaviour)

This is correct, not a bug. A valid file ID requested with the wrong `X-Tenant-Id` returns `404` because the query includes `{ tenantId }` as a filter. The file exists but is invisible to the requesting tenant.
