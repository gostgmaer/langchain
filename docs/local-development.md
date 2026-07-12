# Local Development

A focused guide for running the platform end-to-end on a developer
workstation. For Docker/Kubernetes targets see
[docker-deployment.md](docker-deployment.md) and
[deployment.md](deployment.md).

---

## 1. Prerequisites

| Tool | Minimum version | Notes |
|------|-----------------|-------|
| Python | 3.12 | The codebase uses `match`, `StrEnum`, PEP 695 syntax. |
| PostgreSQL | 14 | 16 recommended. Hash and range partitions are used. |
| Redis | 6.2 | 7.x recommended for Streams stability. |
| Docker (optional) | 24 | Only required for Compose smoke. |
| `make` | 3.81+ | Required for the migration and dev-ops targets described below. |

Windows: use PowerShell 5.1 or 7; commands below show the cross-platform form.

---

## 2. One-time setup

```bash
git clone <repo>
cd multi-tennet-ai-agent
python -m venv .venv
. .venv/Scripts/Activate.ps1     # Windows
# source .venv/bin/activate      # macOS/Linux
python -m pip install -e .[dev]
cp .env.example .env
```

Pick a strategy for backing services:

- **Native install** of Postgres + Redis on the host. Faster iteration.
- **`docker compose up -d postgres redis`** without bringing up `api`/`worker`.
  Recommended; mirrors CI.

Apply schema against the native services:

```bash
make db-init-local   # sources .env, then runs alembic upgrade head
# or directly:
alembic upgrade head
```

When running the full Docker stack, migrations run automatically on every
container start — no manual step needed. See §8 (DB schema changes) for
the full workflow.

---

## 3. Minimum `.env`

The defaults in `.env.example` are correct for local except secrets and
database URLs. The absolute minimum to make the API reach `ready` is:

```dotenv
AI_PLATFORM_ENVIRONMENT=local
AI_PLATFORM_DATABASE_URL=postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/ai_platform
AI_PLATFORM_REDIS_URL=redis://127.0.0.1:6379/0

# At least one provider must have a working key.
AI_PLATFORM_PROVIDER_API_KEYS__gemini=<your-gemini-key>
AI_PLATFORM_PROVIDER_FALLBACK=openrouter
AI_PLATFORM_PROVIDER_API_KEYS__openrouter=<your-openrouter-key>

AI_PLATFORM_DEFAULT_PROVIDER=gemini
```

`AI_PLATFORM_ENVIRONMENT=local` deliberately keeps encryption optional. The
production guard (`enforce_production_safety`) only fires when
`ENVIRONMENT=production`. This service performs no authentication or
authorization of its own in any environment — see
[authentication.md](authentication.md).

See [configuration.md](configuration.md) for the full env-var catalog
and provider-resolution precedence.

---

## 4. Running the stack

Three terminals:

```bash
# Terminal 1 – API
uvicorn app.main:app --reload --port 8000

# Terminal 2 – worker
python -m app.workers.main

# Terminal 3 – ad-hoc checks
curl http://127.0.0.1:8000/health/live
curl http://127.0.0.1:8000/health/ready
```

`/health/ready` must report `status: "ok"` with every component
healthy (`postgresql`, `redis`, `event_store`, `workflow_queue`,
`workflow_worker`, and at least one `provider:*` entry) before traffic
is meaningful.

---

## 5. First request

```bash
curl -X POST http://127.0.0.1:8000/v1/workflows/run \
  -H "Content-Type: application/json" \
  -H "x-tenant-id: tenant_dev" \
  -H "x-principal-id: dev_user" \
  -d '{
    "tenant_id": "tenant_dev",
    "workflow": "support_automation",
    "task": "generate_customer_reply",
    "payload": {
      "channel": "email",
      "subject": "Where is my order?",
      "body": "Hi, where is my order?",
      "from": "customer@example.com"
    }
  }'
```

The response is `HTTP 202` with a `workflow_id` and `job_id`. Poll
`GET /v1/workflows/{workflow_id}` to watch state transitions. See
[api.md](api.md) and [integration-guide.md](integration-guide.md).

---

## 6. Working with prompts

Prompts live in `app/prompts/<category>/<name>.yaml`. The registry
hot-reloads on file change in development. After editing, the next
request picks up the new version; older active versions stay reachable
until version bumps roll forward. See
[workflows.md](workflows.md#prompts-and-versioning).

To pin a workflow's provider for local dev:

```dotenv
AI_PLATFORM_WORKFLOW_DEFAULT_PROVIDERS__support_automation=gemini
AI_PLATFORM_WORKFLOW_DEFAULT_MODELS__support_automation=gemini-2.0-flash
```

---

## 7. Quick reference — `make` targets

A `Makefile` at the repository root wraps all common operations. Run
`make help` to list every target with its description.

```
make up              # docker compose up -d   (auto-applies pending migrations)
make down            # docker compose down
make build           # rebuild images
make rebuild         # full no-cache rebuild
make reset           # ⚠ wipe DB volumes + restart fresh

make migrate msg="…" # generate migration from model changes (see §8)
make db-upgrade      # apply pending migrations now
make db-downgrade    # roll back one migration
make db-current      # show current revision
make db-history      # full migration history

make test            # full test suite (inside container)
make test-unit       # unit tests only
make smoke           # end-to-end smoke test

make shell-api       # bash inside the api container
make shell-db        # psql prompt
```

---

## 8. DB schema changes — zero-touch workflow

The platform uses **Alembic** for schema migrations. The workflow is
designed so you never need to manually copy files into containers or run
`alembic` by hand in Docker.

### How it works

1. `migrations/` is **volume-mounted** into both `api` and `worker`
   containers (`docker-compose.yml`), so files you create locally are
   immediately visible to the running containers.
2. The container **entrypoint** runs `alembic upgrade head` on every boot.
   Alembic tracks which migrations have already run in the
   `alembic_version` table and skips them — it is safe to call on every
   start, including parallel API replicas (advisory lock serialises
   concurrent runners).
3. `make migrate` runs `alembic revision --autogenerate` **inside the api
   container**, which compares your SQLAlchemy models against the live DB
   and generates the diff as a migration file. Because of the volume
   mount, the file lands in your local `migrations/versions/` directory
   immediately.

### Typical change cycle

```bash
# 1. Edit app/db/models.py
#    (add a table, add a column, add/remove an index)

# 2. Generate the migration (runs inside the container against the live DB)
make migrate msg="add tenant_preferences table"

# 3. Review the generated file
cat migrations/versions/<timestamp>_add_tenant_preferences_table.py

# 4. Apply it immediately — or just restart; the entrypoint does it
make db-upgrade

# 5. Verify
make db-current    # should show the new revision as (head)
```

### Non-Docker deployments (CI/CD, VPS, bare-metal)

```bash
# In your deploy script, after pulling the new image or code:
alembic upgrade head

# Or using the Makefile shortcut (sources .env automatically):
make db-init-local
```

Alembic is idempotent — running `upgrade head` on an already-migrated DB
does nothing.

### Vector dimension migrations

The memory/RAG tables (`embeddings`, `episodic_memories`,
`conversation_memories`, `semantic_memories`, `semantic_cache`) store
vector embeddings. The column type is `vector(N)` where `N` is determined
by the embedding model in use.

| Setting | Default | Notes |
|---------|---------|-------|
| `AI_PLATFORM_EMBEDDING_MODEL` | `gemini-embedding-001` | any Ollama or cloud embedding model |
| `AI_PLATFORM_EMBEDDING_DIMENSIONS` | `768` | must match the pgvector column size used by the current schema |

Changing the model (and its dimension count) requires a migration to
`ALTER COLUMN … TYPE vector(N)`. A helper migration script is provided
(`migrations/versions/20260601_0007_vector_768_dimensions.py`) as a
template. Note that **pgvector's HNSW and IVFFlat indexes are limited to
2 000 dimensions**; models with a larger output skip index creation and
fall back to exact nearest-neighbour (full table scan), which is
acceptable for local/dev workloads. If you intentionally override the local
profile to `qwen3-embedding:0.6b`, you can keep
`AI_PLATFORM_EMBEDDING_DIMENSIONS=768` and let the embedding service coerce the
provider output to the schema-compatible size. Only switch to `2560` after
running a matching vector-dimension migration and accepting the no-index
tradeoff.

---

## 9. Tests

```bash
# Fast gate (unit + integration without containers)
python -m pytest -q
# or via make:
make test-unit

# Lint + type
python -m ruff check .
python -m mypy app

# Full suite inside container (matches CI)
make test

# End-to-end smoke against the running stack
make smoke

# Testcontainers-backed integration smoke (requires Docker)
$env:RUN_TESTCONTAINERS = "1"
python -m pytest tests/integration/test_testcontainers_smoke.py -q
```

Coverage is collected via `pytest-cov`. There is no enforced floor today;
target ≥ 90 % on changed modules before merging.

---

## 10. Database reset

```bash
# Docker stack — wipe volumes and restart (entrypoint re-migrates from scratch)
make reset

# Native install — roll back all migrations then reapply
alembic downgrade base
alembic upgrade head

# Or drop and recreate the database
psql -h 127.0.0.1 -U postgres -c "drop database ai_platform"
psql -h 127.0.0.1 -U postgres -c "create database ai_platform"
alembic upgrade head
```

Redis state is mostly ephemeral; flush the dev DB if a queue or
idempotency cache gets stuck:

```bash
redis-cli -n 0 flushdb
```

---

## 11. Common pitfalls

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| `/health/ready` shows `workflow_worker: N/A` | Worker process not running, or running against a different Redis. | Start `python -m app.workers.main`; check `AI_PLATFORM_REDIS_URL` matches the API. |
| `provider:<x>` is `degraded` | API key absent or invalid for `<x>`. | Either set the key or remove the provider from `AI_PLATFORM_PROVIDER_FALLBACK`/router chains. |
| Idempotency replays unexpectedly | Stale Redis entry. | Redis keys are SHA-256 hashed (`idempotency:<hash>`), so prefer flushing the dev Redis DB or using the request log to locate the key. |
| Alembic complains about partition mismatch | Old DB created before partitioning migration. | Recreate the database (step 8). |

For runtime production-style issues see [troubleshooting.md](troubleshooting.md).
