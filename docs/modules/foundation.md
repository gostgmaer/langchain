# SYSTEM DOCUMENTATION: FOUNDATION MODULE

---

## 1. MODULE OVERVIEW

### 1.1 Purpose & Responsibilities
The Foundation Module manages the shared infrastructure, tenant context propagation, global database connection pooling, BullMQ client instances, and OpenTelemetry instrumentation hooks.

### 1.2 Dependencies & Owned Tables
* **Dependencies**: NestJS Core, Drizzle ORM, Redis 8, PostgreSQL 17.
* **Owned Tables**: None (allocates global database schema wrapper `ai_support_agent`).

### 1.3 Diagrams

#### Component Diagram
```mermaid
graph TD
    ClientReq[Client Request] --> Middleware[Tenant & Trace Middleware]
    Middleware --> Context[Execution Context Store]
    Context --> DB[Drizzle DB Pool]
    Context --> Cache[Redis Client Pool]
    Context --> Queue[BullMQ Connection Pool]
```

#### Sequence Diagram
```mermaid
sequenceDiagram
    participant Client
    participant Middleware
    participant Context
    participant DB
    Client->>Middleware: Request with x-tenant-id
    Middleware->>Context: Set Tenant ID in AsyncLocalStorage
    Context->>DB: Query execution with Tenant Context
    DB-->>Context: Results
    Context-->>Client: Response
```

#### ER Diagram
```mermaid
erDiagram
    TENANT ||--o{ AUDIT_LOG : generates
    TENANT {
        uuid id PK
        string domain
        string status
    }
    AUDIT_LOG {
        integer id PK
        uuid tenant_id FK
        string action
        timestamp created_at
    }
```

#### State Diagram
```mermaid
stateDiagram-v2
    [*] --> Unauthenticated
    Unauthenticated --> ContextLoaded : Header Parsed
    ContextLoaded --> ExecutionActive : DB Connection Allocated
    ExecutionActive --> ContextCleared : Request Closed
    ContextCleared --> [*]
```

#### Request Flow Diagram
```mermaid
graph LR
    Req[Request Ingress] --> Parse[Parse Tenant Headers]
    Parse --> Validate[Validate Tenant UUID]
    Validate --> Context[Initialize Context Store]
    Context --> Target[Execute Target Handler]
```

---

## 2. BUSINESS FLOWS

### 2.1 Tenant Context Ingestion
* **Trigger**: HTTP Request, WebSocket message, or Queue Job.
* **Processing**: Extract `x-tenant-id` header or job payload metadata. Initialize `AsyncLocalStorage` instance containing Tenant and Trace contexts.
* **Failure Handling**: Reject request with HTTP 400 if tenant context is missing and route is tenant-protected.

---

## 3. DATA MODEL
No tables directly owned. Registers schema boundaries for Drizzle:
```typescript
export const pgSchema = pgSchema('ai_support_agent');
```
* **Tenant Isolation Strategy**: Enforces row-level-security (RLS) policies using session parameters (`SET LOCAL app.current_tenant_id = 'tenant_id'`).

---

## 4. API & EVENT DOCUMENTATION
Global middleware registers HTTP filters and intercepts events to inject trace/tenant contexts.
No direct public API endpoints or event production.
