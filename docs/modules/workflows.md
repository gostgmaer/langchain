# SYSTEM DOCUMENTATION: WORKFLOW MODULE

---

## 1. MODULE OVERVIEW

### 1.1 Purpose & Responsibilities
Executes rule-based automated event pipelines. It interprets conditional logic rules, triggers actions (such as sending emails, routing tickets, or calling connectors), manages approval flows, and handles execution schedules.

### 1.2 Dependencies & Owned Tables
* **Dependencies**: Foundation, Connector, Ticket, Conversation.
* **Owned Tables**: `workflow_templates`, `workflow_versions`, `workflow_executions`, `workflow_triggers`, `workflow_conditions`, `workflow_actions`, `workflow_approvals`, `workflow_schedules`, `workflow_audit_logs`, `workflow_variables`.

### 1.3 Diagrams

#### Component Diagram
```mermaid
graph TD
    Queue[Execution Queue] --> Processor[DAG Processor]
    Processor --> Conditions[Condition Checker]
    Processor --> Actions[Action Dispatcher]
    Processor --> DB[(PostgreSQL)]
```

#### Sequence Diagram
```mermaid
sequenceDiagram
    participant Event
    participant Processor
    participant Check
    participant Action
    participant DB
    Event->>Processor: Event Fired (e.g. Ticket Created)
    Processor->>DB: Load active workflows for Trigger
    DB-->>Processor: Workflows active list
    Processor->>Check: Match conditions criteria
    Check-->>Processor: Criteria matched (TRUE)
    Processor->>Action: Dispatch Action job
    Action-->>Processor: Action complete
    Processor->>DB: Save WorkflowExecution status (SUCCESS)
```

#### ER Diagram
```mermaid
erDiagram
    workflow_templates ||--o{ workflow_versions : has
    workflow_versions ||--o{ workflow_triggers : defines
    workflow_versions ||--o{ workflow_conditions : checks
    workflow_versions ||--o{ workflow_actions : executes
    workflow_versions ||--o{ workflow_executions : records
    workflow_templates {
        uuid id PK
        uuid tenant_id FK
        string name
        boolean is_active
    }
```

#### State Diagram
```mermaid
stateDiagram-v2
    [*] --> Pending
    Pending --> CheckingConditions : Event Triggered
    CheckingConditions --> ExecutingActions : Conditions Passed
    CheckingConditions --> Terminated : Conditions Failed
    ExecutingActions --> AwaitingApproval : Action requires approval
    AwaitingApproval --> ExecutingActions : Approved
    AwaitingApproval --> Terminated : Rejected
    ExecutingActions --> Completed : All Actions Done
    ExecutingActions --> Failed : Action Runtime Error
```

#### Request Flow Diagram
```mermaid
graph LR
    Trigger[Trigger Event] --> Load[Load Active DAG]
    Load --> Eval[Evaluate Expressions]
    Eval --> Dispatch[Run Action Workers]
```

---

## 2. BUSINESS FLOWS

### 2.1 Workflow Pipeline Execution
* **Trigger**: Workspace domain events (e.g. `TICKET_CREATED`, `CONVERSATION_ASSIGNED`).
* **Processing**: Fetches the workflow DAG mapping to the trigger. Evaluates variables against condition expressions (e.g. `ticket.priority == 'HIGH'`). Runs matched execution actions sequentially.
* **Output**: Writes audit trails, performs connector integrations or notifications.

---

## 3. DATA MODEL
```sql
CREATE TABLE ai_support_agent.workflow_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    name VARCHAR(100) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE ai_support_agent.workflow_executions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    template_id UUID NOT NULL REFERENCES ai_support_agent.workflow_templates(id),
    status VARCHAR(20) DEFAULT 'PENDING', -- 'PENDING', 'RUNNING', 'COMPLETED', 'FAILED'
    execution_log JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

---

## 4. API & EVENT DOCUMENTATION
* `POST /v1/workflows/trigger`:
  - Request: `{"eventId": "uuid", "eventType": "TICKET_CREATED"}`
  - Response: `{"executionId": "uuid"}`
  - Permissions: Internal / Service
