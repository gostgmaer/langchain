# Database Schema

The PostgreSQL schema is the durable source of truth for tenants, workflows,
events, and audit data. This document is the integration-facing reference.
Migrations live in [`migrations/versions/`](../migrations/versions). The
authoritative DDL is the migration files; this document summarises shape,
partitioning, and the indexes you should expect production to keep online.

> **Making schema changes?** See
> [local-development.md §8](local-development.md#8-db-schema-changes--zero-touch-workflow)
> for the `make migrate` workflow — no manual container interaction needed.

All tables are tenant-scoped via a `tenant_id` column. All timestamps are
`timestamptz` and default to `now()` UTC. Soft-deletable rows carry
`deleted_at` / `deleted_by` and an optimistic-lock `lock_version`.

## Migration history

| Revision | Description |
|----------|-------------|
| `20260518_0001` | Initial platform schema (tenants, workflows, events, audit). |
| `20260518_0002` | Security events table. |
| `20260518_0003` | Event snapshots. |
| `20260518_0004` | Idempotency keys + audit FK. |
| `20260523_0001` | pgvector extension; embedding, memory, and semantic-cache tables (`vector(1536)`). |
| `20260523_0002` | Agent orchestration tables. |
| `20260523_0003` | Performance indexes. |
| `20260523_0004` | Resize vector columns to `vector(768)` for `gemini-embedding-001`. |
| `20260523_0005` | Resize vector columns to `vector(2560)` for `qwen3-embedding:0.6b`. HNSW indexes omitted (pgvector limit: 2 000 dims). |
| `20260531_0006` | Resize vector columns to `vector(1536)` while clearing incompatible 2560-dimension payloads. |
| `20260601_0007` | Restore vector columns to `vector(768)` for the repo default `gemini-embedding-001` profile. |

To check the live revision: `make db-current`

## Vector columns

The memory and cache tables carry a `vector(N)` column for semantic similarity
search. The dimension `N` must match `AI_PLATFORM_EMBEDDING_DIMENSIONS` (default
`768` with `gemini-embedding-001`). When switching embedding models, run
`make migrate msg="resize vectors to <N>"` to generate the ALTER migration.

**pgvector index limits** — HNSW and IVFFlat indexes require ≤ 2 000 dimensions.
Models with larger output (e.g. `qwen3-embedding:0.6b` at 2 560 dims) operate
without a vector index, using exact nearest-neighbour scan. For production
workloads, choose an embedding model with ≤ 2 000 dims to retain HNSW indexes,
or apply pgvector's `halfvec` type (available in pgvector ≥ 0.7).

## 1. Operational tables

### `contexts`

Tenant-scoped context store consumed by the prompt registry.

| Column | Type | Notes |
|--------|------|-------|
| `id` | uuid PK | `gen_random_uuid()` default. |
| `tenant_id` | varchar(128) | NOT NULL. |
| `context_id` | varchar(128) | tenant-unique logical id. |
| `version` | int | starts at 1, monotonic. |
| `payload` | jsonb | bounded by `AI_PLATFORM_REQUEST_MAX_BODY_BYTES`. |
| `schema_version` | int | document-shape version. |
| `created_at` / `updated_at` | timestamptz | |
| `lock_version` | int | optimistic concurrency. |
| `deleted_at` / `deleted_by` | nullable | soft-delete. |

Indexes:

* `uq_contexts_tenant_context_active` — unique on `(tenant_id, context_id)` where `deleted_at IS NULL`.
* `ix_contexts_tenant_version` on `(tenant_id, version)`.

### `prompt_versions`

Versioned prompt YAML store. One row per (`tenant_id`, `prompt_id`,
`version`), with at most one `is_active=true` per (`tenant_id`, `prompt_id`).

Indexes: `uq_prompt_versions_version`, `uq_prompt_versions_active` (partial),
`ix_prompt_versions_tenant_tags` (gin).

### `workflow_definitions`

Per-tenant workflow customisations layered over the plugin registry. The
plugin registry is global; entries here are optional overrides shipped as
JSON.

### `workflow_runs`

Projection of the workflow event stream into a row-shaped view used by the
API and worker leases.

| Column | Type | Notes |
|--------|------|-------|
| `workflow_id` | varchar(128) PK | external identifier. |
| `tenant_id` | varchar(128) | NOT NULL. |
| `workflow` | varchar(128) | registry name. |
| `state` | varchar(64) | one of `QUEUED`/`RUNNING`/`WAITING_TOOL`/`WAITING_APPROVAL`/`SUCCESS`/`FAILED`/`CANCELLED`/`DEAD`. |
| `attempt_count` | int | current retry attempt. |
| `priority` | int | dispatcher priority. |
| `lease_holder` | varchar(128) \| null | worker id holding the lease. |
| `lease_expires_at` | timestamptz \| null | wall-clock lease deadline. |
| `timeout_at` | timestamptz | engine deadline. |
| `started_at` / `completed_at` | timestamptz | wall-clock observation. |
| `pending_action` | jsonb \| null | snapshot of the current tool/approval gate. |
| `result` | jsonb \| null | populated on `SUCCESS`. |
| `error` | jsonb \| null | populated on `FAILED` / `DEAD`. |

Indexes are keyed on `(tenant_id, state, created_at)`, `(state,
lease_expires_at)`, and `trace_id`.

### `workflow_steps`

Step-level projection used by debugging endpoints.

### `tool_requests` / `approval_requests`

Outstanding tool-callback and approval gates. Both carry an optional
`idempotency_key` enforced unique per tenant (added in migration
[`20260518_0004`](../migrations/versions/20260518_0004_idempotency_and_audit_fk.py)).

## 2. Event store

### `event_store`

Hash-partitioned by `stream_id` into 16 partitions
(`event_store_p00 … event_store_p15`). Append-only. The event envelope
matches [`event-model.md`](event-model.md).

| Column | Type | Notes |
|--------|------|-------|
| `stream_id` | varchar(128) | partition key; typically `workflow:<workflow_id>`. |
| `stream_version` | int | per-stream monotonic; uniqueness enforced per partition. |
| `event_id` | uuid | global id. |
| `tenant_id` | varchar(128) | filter dimension. |
| `event_name` | varchar(128) | from `app.events.models.EventName`. |
| `payload` | jsonb | envelope body. |
| `occurred_at` | timestamptz | event time. |
| `trace_id` | varchar(128) | correlation id. |

### `event_snapshots`

Optional snapshots inserted every
`AI_PLATFORM_WORKFLOW_SNAPSHOT_INTERVAL` events for long-running streams.
PK is `(stream_id, stream_version)`. The latest snapshot is selected via
`ix_event_snapshots_latest`.

## 3. Cost and audit tables

### `ai_generations`

Range-partitioned monthly (e.g. `ai_generations_2026_05`, plus a default
catch-all partition). Stores per-attempt provider cost, latency, and token
counts for billing and routing decisions.

### `usage_metrics`

Range-partitioned monthly. Rolls up `ai_generations` per
(`tenant_id`, `day`, `provider`, `model`).

### `audit_logs`

Tenant audit trail for state-changing endpoints. As of migration
[`20260518_0004`](../migrations/versions/20260518_0004_idempotency_and_audit_fk.py),
`workflow_id` is nullable with `ON DELETE SET NULL`, so audit history
survives workflow archival.

### `security_events`

Security-sensitive events (auth failures, signing failures, RBAC denials,
approval decisions). Created in migration
[`20260518_0002`](../migrations/versions/20260518_0002_security_events.py).
Indexed by `(tenant_id, created_at)`, `(tenant_id, principal_id, created_at)`,
and `(workflow_id, created_at)`.

## 4. Queue, worker, and provider metrics

| Table | Purpose |
|-------|---------|
| `queue_metrics` | Periodic queue depth / lag / age samples. |
| `worker_metrics` | Per-worker heartbeat, claimed/completed counters, CPU/memory. |
| `provider_metrics` | Per-provider success/failure/latency rollups. |

These are operator-facing tables. The hot-path metrics surface for
dashboards is Prometheus; see
[`observability-metrics.md`](observability-metrics.md).

## 5. Failure-handling tables

### `failed_jobs`

Records the most recent failure for each queued job. Used by the retry
engine.

### `dead_letter_jobs`

Terminal failures after retries are exhausted. Operators replay rows from
here through `POST /v1/workflows/{workflow_id}/dead-letter/replay`. See
[`runbooks.md`](runbooks.md).

## 6. Intelligence tables (vector, memory, semantic cache)

### `documents`

Source documents ingested for RAG retrieval. Tracks ingestion status and
content hash for idempotent re-ingest.

| Column | Type | Notes |
|--------|------|-------|
| `id` | uuid PK | `gen_random_uuid()` default. |
| `tenant_id` | varchar(128) | NOT NULL. |
| `namespace` | varchar(128) | retrieval namespace, e.g. `support`, `resumes`. |
| `source_type` | varchar(64) | e.g. `resume`, `email`, `contract`. |
| `title` | varchar(500) | optional document title. |
| `source_uri` | text | optional source URI. |
| `content_hash` | varchar(64) | SHA-256; idempotency guard. |
| `total_chunks` | int | number of chunks produced. |
| `status` | varchar(32) | `PENDING`/`PROCESSING`/`COMPLETED`/`FAILED`. |
| `metadata` | jsonb | arbitrary key-value. |
| `ingested_at` | timestamptz \| null | populated on successful ingestion. |
| `created_at` / `updated_at` | timestamptz | |
| `created_by` | varchar(128) \| null | optional actor id. |
| `deleted_at` | timestamptz \| null | soft-delete marker. |

Indexes: `uq_documents_tenant_hash` (unique active tenant + namespace + content_hash),
`ix_documents_tenant_namespace`, `ix_documents_tenant_status`.

### `embeddings`

Chunk-level vector embeddings linked to `documents`. Uses pgvector
`vector(768)` with HNSW indexes.

| Column | Type | Notes |
|--------|------|-------|
| `id` | uuid PK | |
| `tenant_id` | varchar(128) | NOT NULL. |
| `namespace` | varchar(128) | retrieval namespace. |
| `source_id` | uuid | source document id. |
| `source_type` | varchar(64) | document source type. |
| `chunk_index` | int | position within document. |
| `content_text` | text | raw chunk text. |
| `content_hash` | varchar(64) | deduplication key. |
| `embedding` | vector(768) | HNSW indexed (cosine). |
| `token_count` | int | chunk token count. |
| `metadata` | jsonb | |
| `created_at` | timestamptz | |
| `expires_at` | timestamptz \| null | optional TTL. |

Indexes: `ix_embeddings_vector_hnsw` (HNSW, `vector_cosine_ops`, m=16, ef=64),
`uq_embeddings_content_hash`, `ix_embeddings_tenant_namespace`, `ix_embeddings_source`.

### `conversation_memories`

Short-term conversation turns for session-aware context.

| Column | Type | Notes |
|--------|------|-------|
| `id` | uuid PK | |
| `tenant_id` | varchar(128) | NOT NULL. |
| `session_id` | varchar(128) | groups conversation turns. |
| `role` | varchar(32) | `user`/`assistant`/`system`/`tool`. |
| `content` | text | message text. |
| `embedding` | vector(768) | optional semantic search. |
| `summary_of` | uuid[] | optional summarized message ids. |
| `token_count` | int | token count. |
| `metadata` | jsonb | |
| `expires_at` | timestamptz | TTL-based cleanup. |
| `created_at` | timestamptz | |

Indexes: `ix_convo_mem_vector` (HNSW), `ix_convo_mem_session`,
`ix_convo_mem_expires`.

### `episodic_memories`

Notable events recorded for long-term recall.

| Column | Type | Notes |
|--------|------|-------|
| `id` | uuid PK | |
| `tenant_id` | varchar(128) | NOT NULL. |
| `principal_id` | varchar(128) \| null | actor id. |
| `workflow_name` | varchar(128) | workflow that produced the memory. |
| `workflow_run_id` | uuid \| null | source workflow run. |
| `input_summary` | text | summarized input. |
| `output_summary` | text | summarized output. |
| `outcome` | varchar(32) | `success`/`failure`/`partial`/`timeout`. |
| `quality_score` | float \| null | 0.0–1.0 scoring. |
| `embedding` | vector(768) | HNSW indexed. |
| `metadata` | jsonb | |
| `relevance_decay_at` | timestamptz \| null | scheduled relevance decay. |
| `created_at` | timestamptz | |

Indexes: `ix_episodic_vector_hnsw`, `ix_episodic_tenant_workflow`.

### `semantic_memories`

Long-term semantic facts with confidence decay.

| Column | Type | Notes |
|--------|------|-------|
| `id` | uuid PK | |
| `tenant_id` | varchar(128) | NOT NULL. |
| `principal_id` | varchar(128) \| null | actor id. |
| `category` | varchar(128) | e.g. `preference`, `fact`, `constraint`. |
| `fact` | text | the semantic fact. |
| `embedding` | vector(768) | HNSW indexed. |
| `confidence` | float | decays over time (factor 0.95/day). |
| `source_workflow_id` | varchar(128) \| null | source workflow id. |
| `source_type` | varchar(64) | source class, default `workflow`. |
| `access_count` | int | incremented on recall. |
| `last_accessed_at` | timestamptz | |
| `metadata` | jsonb | |
| `expires_at` | timestamptz \| null | optional TTL. |
| `created_at` | timestamptz | |

Indexes: `ix_semantic_vector_hnsw`, `ix_semantic_tenant_category`,
`ix_semantic_expires`.

### `semantic_cache`

Avoids redundant LLM calls by caching results keyed on embedding
similarity.

| Column | Type | Notes |
|--------|------|-------|
| `id` | uuid PK | |
| `tenant_id` | varchar(128) | NOT NULL. |
| `workflow_name` | varchar(128) | scope cache to workflow type. |
| `request_hash` | varchar(64) | SHA-256 of request content. |
| `request_embedding` | vector(768) | HNSW indexed. |
| `response` | jsonb | cached LLM response. |
| `provider` | varchar(64) | provider used. |
| `model` | varchar(128) | model used. |
| `token_count` | int | token count for cached response. |
| `hit_count` | int | analytics. |
| `last_hit_at` | timestamptz \| null | |
| `expires_at` | timestamptz | TTL-based invalidation. |
| `created_at` | timestamptz | |

Indexes: `uq_semantic_cache_hash`, `ix_semantic_cache_vector_hnsw`,
`ix_semantic_cache_expires`.

### `agent_orchestrations`

Tracks DB-backed multi-agent orchestration runs. API replicas and worker
replicas never rely on in-memory agent state.

| Column | Type | Notes |
|--------|------|-------|
| `id` | uuid PK | |
| `tenant_id` | varchar(128) | NOT NULL. |
| `orchestration_id` | varchar(128) | public orchestration id. |
| `trace_id` | varchar(128) | request trace id. |
| `objective` | text | orchestration goal. |
| `strategy` | varchar(32) | currently `parallel`. |
| `status` | varchar(32) | `QUEUED`, `RUNNING`, `SUCCESS`, `FAILED`, `DEAD`, `CANCELLED`. |
| `workflow_count` | int | number of child workflow agents. |
| `metadata` | jsonb | caller supplied metadata. |
| `created_at` / `updated_at` | timestamptz | audit timestamps. |
| `deleted_at` | timestamptz \| null | soft delete marker. |

Indexes: `uq_agent_orchestrations_tenant_orchestration`,
`ix_agent_orchestrations_tenant_status`.

### `agent_workflow_links`

Links each specialist agent task to its queued workflow run.

| Column | Type | Notes |
|--------|------|-------|
| `id` | uuid PK | |
| `tenant_id` | varchar(128) | NOT NULL. |
| `orchestration_id` | varchar(128) | parent orchestration id. |
| `agent_name` | varchar(128) | unique within request. |
| `role` | varchar(128) | specialist role. |
| `workflow_id` | varchar(128) | child workflow id. |
| `job_id` | varchar(128) | child job id. |
| `workflow_name` | varchar(128) | workflow handler/plugin name. |
| `status` | varchar(32) | child status projection at queue time. |
| `created_at` / `updated_at` | timestamptz | audit timestamps. |

Indexes: `uq_agent_workflow_links_workflow`,
`ix_agent_workflow_links_orchestration`, `ix_agent_workflow_links_agent`.

## 7. Retention and archival

| Table | Retention | Archive |
|-------|-----------|---------|
| `event_store` | hot 30 d, warm 180 d | partitions detached and copied to object storage. |
| `ai_generations` | hot 30 d | monthly partition export. |
| `usage_metrics` | 13 months hot | rolled up to data warehouse, then partition dropped. |
| `audit_logs` | 13 months hot | quarterly partition export. |
| `security_events` | 24 months hot | quarterly partition export. |
| `workflow_runs` | hot until DEAD + 30 d | archived alongside event stream. |

See [`disaster-recovery.md`](disaster-recovery.md) for backup, PITR, and
event-replay procedures.

## 8. Adding a column or table

The recommended zero-touch workflow (Docker stack must be running):

```bash
# 1. Edit app/db/models.py — add the column/table/index to the ORM model

# 2. Generate the migration automatically from the model diff
make migrate msg="add <what you added>"

# 3. Review the generated file in migrations/versions/
#    Check for any conditional guards (IF NOT EXISTS) if needed

# 4. Apply it (or restart — entrypoint auto-applies on next boot)
make db-upgrade
```

For manual migration authoring, name the file
`YYYYMMDD_NNNN_<change>.py` and use `IF NOT EXISTS` guards for
columns and indexes where appropriate.

After any schema change:

- Update the relevant section of this document.
- Add a regression test under `tests/migrations/`.
