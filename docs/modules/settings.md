# SYSTEM DOCUMENTATION: SETTINGS MODULE

---

## 1. MODULE OVERVIEW

### 1.1 Purpose & Responsibilities
Maintains configuration variables for all tenants, including active channels, branding parameters, weekly business calendars, AI thresholds, and feature flags.

### 1.2 Dependencies & Owned Tables
* **Dependencies**: Foundation.
* **Owned Tables**: `tenant_settings`, `tenant_preferences`, `tenant_branding`, `tenant_business_hours`.

### 1.3 Diagrams

#### Component Diagram
```mermaid
graph TD
    API[Settings Controller] --> Service[Settings Service]
    Service --> Cache[Redis Cache]
    Service --> DB[(PostgreSQL)]
```

#### Sequence Diagram
```mermaid
sequenceDiagram
    participant API
    participant Serv
    participant Cache
    participant DB
    API->>Serv: Update Business Hours
    Serv->>DB: Save timezone and hour rules
    Serv->>Cache: Invalidate Settings Cache
    DB-->>Serv: Confirm Save
    Serv-->>API: Updated Configurations
```

#### ER Diagram
```mermaid
erDiagram
    tenant_settings ||--|| tenant_branding : has
    tenant_settings ||--o{ tenant_business_hours : defines
    tenant_settings {
        uuid id PK
        uuid tenant_id FK
        boolean enable_ai
        string locale
    }
```

#### State Diagram
```mermaid
stateDiagram-v2
    [*] --> Active
    Active --> ConfigUpdated : Preferences changed
    ConfigUpdated --> Active : Cache warmed
```

---

## 2. BUSINESS FLOWS

### 2.1 Settings Update propagation
* **Trigger**: PATCH call to settings endpoints.
* **Processing**: Persists values to Postgres settings tables. Dispatches a cache invalidation signal over Redis Pub/Sub to reload system behaviors.
* **Output**: Flushed settings caches on active nodes.

---

## 3. DATA MODEL
```sql
CREATE TABLE ai_support_agent.tenant_settings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID UNIQUE NOT NULL,
    enable_ai BOOLEAN DEFAULT FALSE,
    locale VARCHAR(10) DEFAULT 'en',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE ai_support_agent.tenant_business_hours (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES ai_support_agent.tenant_settings(tenant_id),
    day_of_week INT NOT NULL, -- 0 (Sunday) to 6 (Saturday)
    start_time TIME NOT NULL,
    end_time TIME NOT NULL
);
```

---

## 4. API & EVENT DOCUMENTATION
* `PATCH /v1/settings/preferences`:
  - Request: `{"enableAi": true}`
  - Response: Updated preferences payload.
  - Permissions: `settings:write`
