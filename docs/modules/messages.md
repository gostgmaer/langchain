# SYSTEM DOCUMENTATION: MESSAGE MODULE

---

## 1. MODULE OVERVIEW

### 1.1 Purpose & Responsibilities
Governs the creation, storage, rendering, and delivery tracking of messages. Triggers automated AI agents based on conversation message histories, tracks browser read receipts, and validates document attachments.

### 1.2 Dependencies & Owned Tables
* **Dependencies**: Foundation, Conversation, File Security (for parsing attachments).
* **Owned Tables**: `messages`, `attachments`.

### 1.3 Diagrams

#### Component Diagram
```mermaid
graph TD
    API[Message Controller] --> Service[Message Service]
    Service --> Security[File Security Service]
    Service --> AI[AI Dispatch Queue]
    Service --> DB[(PostgreSQL)]
```

#### Sequence Diagram
```mermaid
sequenceDiagram
    participant API
    participant Serv
    participant AI
    participant DB
    API->>Serv: Send Message (Inbound/Outbound)
    Serv->>DB: Save Message record (Status: PENDING)
    Serv->>AI: Enqueue message for AI processing check
    DB-->>Serv: Confirm Save
    Serv-->>API: Message DTO (Status: SENT)
```

#### ER Diagram
```mermaid
erDiagram
    messages ||--o{ attachments : includes
    messages {
        uuid id PK
        uuid tenant_id FK
        uuid conversation_id FK
        uuid sender_id FK
        string content
        string status
    }
```

#### State Diagram
```mermaid
stateDiagram-v2
    [*] --> Draft
    Draft --> Sent : Send Triggered
    Sent --> Delivered : Gateway Confirmed
    Delivered --> Read : Client Webhook / Read receipt
```

#### Request Flow Diagram
```mermaid
graph LR
    Msg[New Message] --> Scan[Security Malware Scan]
    Scan --> Save[Persist DB]
    Save --> Embed[Auto AI Ingestion Trigger]
```

---

## 2. BUSINESS FLOWS

### 2.1 Outbound Message Send
* **Trigger**: Post request on `/v1/messages/send`.
* **Processing**: Performs size checking. Runs attachments through file security scanners (Spoof/double extension detection). Persists row to `messages`. Emits `MESSAGE_SENT` event.
* **Output**: Delivers payloads to external channel integrations (WhatsApp, email, slack).

---

## 3. DATA MODEL
```sql
CREATE TABLE ai_support_agent.messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    conversation_id UUID NOT NULL REFERENCES ai_support_agent.conversations(id),
    content TEXT,
    status VARCHAR(20) DEFAULT 'SENT', -- 'DRAFT', 'SENT', 'DELIVERED', 'READ'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

---

## 4. API & EVENT DOCUMENTATION
* `POST /v1/messages/send`:
  - Request: `{"conversationId": "uuid", "content": "hello"}`
  - Response: Message object.
  - Permissions: `conversation:write`
