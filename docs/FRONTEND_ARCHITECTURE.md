# FRONTEND ARCHITECTURE SYSTEM DOCUMENTATION: EASYDEV SUPPORT AI

---

## 1. SYSTEM OVERVIEW & ARCHITECTURE

### 1.1 Technology Stack
* **Framework**: Next.js 15 (App Router, Server Components where applicable)
* **Language**: TypeScript 5+ (Strict Type safety)
* **Styling**: TailwindCSS 4+ & ShadCN UI (CSS variables for tenant branding customization)
* **State Management**: 
  - Server Cache: React Query (TanStack Query v5) for cache control and optimistic updates.
  - Client State: Zustand (for session indicators, UI toggles, and sidebar states).
* **Realtime Network**: Socket.IO client (pointing to `ws.easydev.in/socket.io/`).

### 1.2 Folder Layout Structure
```
easydev-support-ai-web/
├── apps/
│   ├── admin-portal/         # Next.js App Router (Port: 3005)
│   ├── agent-workspace/      # Next.js App Router (Port: 3006)
│   ├── customer-widget/      # Vanilla JS / React Bundle loaded in shadow-DOM
│   └── help-center/          # Next.js SSG / Dynamic Portal
```

---

## 2. PORTAL DESIGNS

### 2.1 Admin Portal (`apps/admin-portal`)

#### Directory Structure
```
apps/admin-portal/
├── src/
│   ├── app/                  # App Router Layouts and Pages
│   │   ├── (auth)/login      # Login Page
│   │   ├── tenants/          # Tenant Registry (/tenants)
│   │   ├── settings/         # Tenant settings (/settings)
│   │   └── layout.tsx
│   ├── components/           # ShadCN Custom Wrappers
│   └── store/                # Zustand Admin preferences
```

#### Page Reference: Tenant Registry (/tenants)
* **Purpose**: Allows global system admins to create, edit, audit, and suspend tenant bounds.
* **Route**: `/tenants`
* **Permissions Required**: `sysadmin:write`, `sysadmin:read`
* **Components**: `<TenantTable />`, `<CreateTenantModal />`, `<SuspensionDialog />`.
* **API Integrations**:
  - `GET /v1/admin/tenants` (React Query: `useQuery(['tenants'])`)
  - `POST /v1/admin/tenants/create` (React Query Mutation)
* **State Management**:
  - Zustand (`useTenantAdminStore`): tracks active filters, paging indexes, and selected tenant context.
* **User Actions**:
  - Trigger tenant suspension: issues `PATCH /v1/admin/tenants/:id/status` with payload `{"status":"SUSPENDED"}`.
  - Zod Validation:
    ```typescript
    const TenantCreateSchema = z.object({
      name: z.string().min(3).max(100),
      domain: z.string().regex(/^[a-z0-9-]+(\.[a-z0-9-]+)*$/)
    });
    ```
* **Accessibility**:
  - WAI-ARIA tables, modal focus traps, color contrast ratio > 4.5:1.

---

### 2.2 Agent Workspace (`apps/agent-workspace`)

#### Directory Structure
```
apps/agent-workspace/
├── src/
│   ├── app/
│   │   ├── inbox/            # Unified Inbox Routing (/inbox)
│   │   ├── tickets/          # Ticket detail panels (/tickets)
│   │   └── analytics/        # Agent Analytics (/analytics)
│   ├── components/           # MessagePanel, ConversationList, RAGContext
│   └── store/                # Zustand Real-time status / Active threads
```

#### Page Reference: Unified Inbox (/inbox)
* **Purpose**: Core interface for agents to read messages, send replies, apply tags, and search histories.
* **Route**: `/inbox`
* **Permissions Required**: `conversation:read`
* **Components**: `<InboxSidebar />`, `<ConversationThread />`, `<ChatInput />`, `<PIIAlertBanner />`, `<RAGSourceList />`.
* **Realtime Requirements**:
  - Listen to `message:new` (appends message item to active thread cache).
  - Listen to `typing:status` (displays typing indicators above chat inputs).
  - Emit `typing:indicator` on keypress events.
* **Zustand State (`useInboxStore`)**:
  - Tracks `activeConversationId`, `onlineAgentsList`, `sidebarFilterState`.

---

### 2.3 Customer Widget (`apps/customer-widget`)

#### Layout & Shadow DOM
To prevent host webpage styling conflicts, the Widget initializes inside a **Shadow Root**:
```typescript
const container = document.createElement('div');
const shadowRoot = container.attachShadow({ mode: 'open' });
// Inject Tailwind styles directly into shadowRoot
```

#### Page Reference: Chat Session
* **Route**: Root mounting (`/`)
* **Components**: `<ChatLauncherButton />`, `<WidgetChatPanel />`, `<PreChatLeadForm />`, `<FileUploadArea />`.
* **API Integrations**:
  - `POST /v1/widget/session/start` (Starts anonymous visitor session).
  - `POST /v1/widget/lead/capture` (Saves lead data before conversation starts).
* **Validation Rules**:
  - In pre-chat form: Email field validation requires standard email pattern matching.

---

### 2.4 Help Center (`apps/help-center`)

#### Page Reference: Article View
* **Route**: `/articles/:slug`
* **Purpose**: Displays self-service documentation pages.
* **Loading States**: Static Site Generation (SSG) with fallback loading skeletons.
* **API Integrations**:
  - `GET /v1/knowledge/articles/:slug` (Fetches article metadata and markdown).

---

## 3. RESPONSIVE BEHAVIOR DESIGN MATRIX

| Component | Desktop Layout (>= 1200px) | Tablet Layout (768px - 1199px) | Mobile Layout (< 768px) |
|:---|:---|:---|:---|
| **Unified Inbox** | 3-Column: Navigation sidebar, thread selection list, active chat panel. | 2-Column: Thread list and active chat panel (navigation collapsed into burger). | 1-Column: Stacked navigation (Thread list swaps screen to active chat on selection). |
| **Admin Dashboard**| Grid of 4 columns representing analytics summaries. Sidebar expanded. | Grid of 2 columns. Sidebar collapsed into mini-icons. | Grid of 1 column. Navigation placed in header sheets. |
| **Customer Widget**| Floats at bottom right (width: 380px, height: 600px). | Floats at bottom right (width: 380px, height: 600px). | Fills the entire browser viewport (full-screen modal overlay). |
