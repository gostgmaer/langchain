# SYSTEM DOCUMENTATION: AI INTEGRATION MODULE

---

## 1. MODULE OVERVIEW

### 1.1 Purpose & Responsibilities
Executes RAG prompts, selects and runs dynamic workflow tools, orchestrates conversational agent reasoning, controls human handoff triggers on low confidence, and tracks token consumption costs.

### 1.2 Dependencies & Owned Tables
* **Dependencies**: Foundation, Connector, Knowledge, Message.
* **Owned Tables**: `ai_agents`, `ai_sessions`, `ai_workflows`.

### 1.3 Diagrams

#### Component Diagram
```mermaid
graph TD
    Queue[Job Dispatcher] --> Engine[Reasoning Engine]
    Engine --> RAG[RAG Semantic Matcher]
    Engine --> Tool[Tool Call Executor]
    Engine --> Gateway[AI API Service]
```

#### Sequence Diagram
```mermaid
sequenceDiagram
    participant Queue
    participant Engine
    participant RAG
    participant Tool
    participant Gateway
    Queue->>Engine: Run AI Agent check on Message
    Engine->>RAG: Request Context Chunks
    RAG-->>Engine: Context Chunks List
    Engine->>Gateway: Send Chat History + Context Prompt
    Gateway-->>Engine: Tool Call Request: get_order_status(id)
    Engine->>Tool: Execute Connector Action
    Tool-->>Engine: Output Data
    Engine->>Gateway: Send Tool results to LLM
    Gateway-->>Engine: Final Reply (Confidence: 0.92)
```

#### ER Diagram
```mermaid
erDiagram
    ai_agents ||--o{ ai_sessions : creates
    ai_sessions {
        uuid id PK
        uuid tenant_id FK
        uuid conversation_id FK
        integer token_count
        numeric total_cost
        string session_state
    }
```

#### State Diagram
```mermaid
stateDiagram-v2
    [*] --> Idle
    Idle --> Thinking : Message Arrived
    Thinking --> ExecutingTool : Tool Call Detected
    ExecutingTool --> Thinking : Tool Results Returned
    Thinking --> Responding : Reply Generated (Conf > 0.85)
    Thinking --> Escalating : Handoff Triggered (Conf < 0.85)
    Responding --> Idle
    Escalating --> Idle
```

#### Request Flow Diagram
```mermaid
graph LR
    Msg[User Message] --> AgentActive{Is AI Enabled?}
    AgentActive -->|Yes| Prompt[Construct Prompt Context]
    AgentActive -->|No| Human[Direct to Human Queue]
    Prompt --> Gen[Generate Response]
```

---

## 2. BUSINESS FLOWS

### 2.1 Agent Message Loop & Handoff
* **Trigger**: `MESSAGE_SENT` event.
* **Processing**: Fetches the last 5 messages in conversation. Searches Knowledge Base for context. Sends payload to LLM. If confidence score < 0.85 or model returns a specific handoff tag, switches conversation assignment status to `ASSIGNED` and sends alert to the team queue.
* **Output**: Generated message response or human ticket routing.

---

## 3. DATA MODEL
```sql
CREATE TABLE ai_support_agent.ai_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    conversation_id UUID NOT NULL REFERENCES ai_support_agent.conversations(id),
    token_count INT DEFAULT 0,
    total_cost NUMERIC(10, 4) DEFAULT 0.0000,
    session_state VARCHAR(20) DEFAULT 'ACTIVE'
);
```

---

## 4. API & EVENT DOCUMENTATION
* `POST /v1/ai/session/:id/pause`:
  - Request: Empty body.
  - Response: `{"paused": true}`
  - Permissions: `conversation:write`
