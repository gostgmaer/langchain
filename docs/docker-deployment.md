# Docker Deployment

Operational guide for running the platform with Docker and Docker
Compose. For Kubernetes, see [deployment.md §3](deployment.md#3-kubernetes).
For host-Python development, see
[local-development.md](local-development.md).

---

## 1. Images

The repository ships a single multi-stage `Dockerfile`:

| Stage | Purpose |
|-------|---------|
| `builder` | Installs the package and locked dependencies into `/opt/venv`. |
| `runtime` | `python:3.12-slim-bookworm`, non-root user `app:app` (UID 1001). |

The entrypoint `docker/entrypoint.sh`:

1. Runs `alembic upgrade head` under a Postgres advisory lock (safe on
   parallel API + worker startup).
2. Execs the requested command (`uvicorn`, `python -m app.workers.main`, etc.).

Build:

```bash
docker build -t ai-platform:local .
```

Healthcheck (baked into the image): `GET /health/live` on port 8000
every 30 s, 5 s timeout, 3 retries.

---

## 2. Compose topology

`docker-compose.yml` defines the standard local topology:

```
┌──────────┐      ┌──────────┐
│   api    │◄────►│  redis   │
└────┬─────┘      └────┬─────┘
     │                 │
     │            ┌────┴─────┐
     └───────────►│ postgres │
                  └────┬─────┘
                       │
                  ┌────┴─────┐
                  │  worker  │
                  └──────────┘
```

| Service | Image | Notes |
|---------|-------|-------|
| `postgres` | `pgvector/pgvector:pg17` | Includes the `vector` extension required by memory/RAG tables. Host port via `POSTGRES_HOST_PORT`. |
| `redis` | `redis:7-alpine` | Volume `redisdata`. |
| `api` | built from `Dockerfile` | Runs `uvicorn`. Exposes `8000`. |
| `worker` | built from `Dockerfile` | Runs `python -m app.workers.main`. No HTTP listener; no Docker healthcheck. |

Start in dependency order:

```bash
make up              # equivalent to docker compose up -d
# or manually:
docker compose up -d
```

Migrations are applied automatically by the entrypoint on every container
start. No separate migration step is required. See
[local-development.md §8](local-development.md#8-db-schema-changes--zero-touch-workflow).

Other common operations:

```bash
make logs            # tail all containers
make logs-api        # tail api only
make logs-worker     # tail worker only
make rebuild         # full no-cache image rebuild
make reset           # ⚠ wipe volumes + restart from scratch
```

Apply additional overlays:

- `docker-compose.e2e.yml` — wires the local E2E smoke harness against
  real OpenRouter traffic (see [deployment.md §5](deployment.md#5-smoke-validation)).
- `docker-compose.observability.yml` — Prometheus + Grafana with preloaded
  scrape config, alert rules, and dashboards.

---

## 3. Required environment variables

For any non-`local` environment, Compose must inherit these values from
your shell or a secrets file:

```dotenv
AI_PLATFORM_ENVIRONMENT=production            # or staging
AI_PLATFORM_DATABASE_URL=postgresql+asyncpg://...
AI_PLATFORM_REDIS_URL=redis://...

AI_PLATFORM_RATE_LIMIT_BACKEND=redis
AI_PLATFORM_IDEMPOTENCY_BACKEND=redis
AI_PLATFORM_PROVIDER_CIRCUIT_BREAKER_BACKEND=redis
AI_PLATFORM_PROVIDER_QUOTA_BACKEND=redis
AI_PLATFORM_ADAPTIVE_PROVIDER_ROUTING_ENABLED=true

AI_PLATFORM_SECURITY_ACTIVE_KEY_VERSION=v1
AI_PLATFORM_SECURITY_ENCRYPTION_KEY_V1=<32-byte base64>

AI_PLATFORM_PROVIDER_API_KEYS__gemini=<key>
AI_PLATFORM_PROVIDER_API_KEYS__openrouter=<key>
AI_PLATFORM_PROVIDER_DAILY_TOKEN_QUOTAS__gemini=250000
AI_PLATFORM_PROVIDER_DAILY_TOKEN_QUOTAS__openrouter=250000
AI_PLATFORM_DEFAULT_PROVIDER=gemini
AI_PLATFORM_PROVIDER_FALLBACK=openrouter

AI_PLATFORM_SEMANTIC_CACHE_ENABLED=true
AI_PLATFORM_CONTEXT_COMPRESSION_ENABLED=true
AI_PLATFORM_WORKFLOW_LEARNING_ENABLED=true
AI_PLATFORM_WORKFLOW_WORKER_CONCURRENCY=4

AI_PLATFORM_OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317
```

If `AI_PLATFORM_ENVIRONMENT=production`, the API refuses to start until
every safety flag above is enabled. See
[deployment.md §4](deployment.md#4-production-required-settings).

---

## 4. Sizing for 500–1 000 concurrent workflows

Reference allocation for the documented load (500–1 000 in-flight
workflows, 50–100 RPS API):

| Service | Replicas | Per-replica CPU | Per-replica RAM | Notes |
|---------|---------|-----------------|------------------|-------|
| `api` | 3 | 1 vCPU | 1 GiB | Stateless. Behind L7 LB with sticky `trace_id` propagation. |
| `worker` | 4–8 | 1 vCPU | 1–2 GiB | Each pod runs `AI_PLATFORM_WORKFLOW_WORKER_CONCURRENCY` lease loops. Scale replicas before raising per-pod concurrency. |
| `postgres` | 1 primary + 1 replica | 4 vCPU | 8 GiB | Use a managed offering in production. `max_connections=200`. |
| `redis` | 1 + sentinel/replica | 2 vCPU | 2 GiB | Persistence: AOF every second. |
| PgBouncer (recommended) | 1 | 0.5 vCPU | 256 MiB | `pool_mode=transaction`, `max_db_connections=100`. |

Application connection pool per API/worker replica:

```dotenv
AI_PLATFORM_DATABASE_POOL_SIZE=5
AI_PLATFORM_DATABASE_MAX_OVERFLOW=5
AI_PLATFORM_DATABASE_POOL_TIMEOUT_SECONDS=10
```

Total backend connections at full scale:
`(3 api + 12 worker) × (5 + 5) = 150` ⇒ comfortably under `max_connections=200`
without PgBouncer, and trivial with PgBouncer.

---

## 5. Graceful shutdown

The API and worker both trap `SIGTERM`:

- API: `uvicorn` drains in-flight HTTP requests up to
  `--timeout-graceful-shutdown` (default 30 s).
- Worker: stops accepting new leases, finishes the current workflow,
  releases its lease, exits.

Set the orchestrator's `terminationGracePeriodSeconds` (k8s) or Compose
`stop_grace_period` to at least `(handler_timeout_seconds + 10)` —
default 70 s.

---

## 6. Observability hooks

The API exposes:

- `GET /health/live` — process health (always 200 if the event loop is alive).
- `GET /health/ready` — composite readiness (Postgres, Redis, event store,
  workflow queue, worker heartbeat, providers).
- `GET /metrics` — Prometheus text format.

Wire to Prometheus:

```yaml
scrape_configs:
  - job_name: ai-platform-api
    static_configs:
      - targets: ['api:8000']

  - job_name: ai-platform-worker
    static_configs:
      - targets: ['worker:9100']
```

The worker process now serves its own Prometheus exposition on
`AI_PLATFORM_WORKER_METRICS_PORT` (default `9100`). Queue depth, queue lag,
active worker counts, workflow transitions, retries, dead-letter growth, and
provider execution metrics come from that worker endpoint because those events
are recorded inside the worker process.

To bring up the full local stack with dashboards:

```bash
docker compose -f docker-compose.yml -f docker-compose.observability.yml up -d
```

Prometheus is then available on `http://127.0.0.1:9090` and Grafana on
`http://127.0.0.1:3000` (`admin` / `admin` by default unless you override
`GRAFANA_ADMIN_USER` and `GRAFANA_ADMIN_PASSWORD`).

OpenTelemetry traces are emitted when
`AI_PLATFORM_OTEL_EXPORTER_OTLP_ENDPOINT` is set. The default sampler is
parent-based; override for high-volume environments with
`OTEL_TRACES_SAMPLER=traceidratio` + `OTEL_TRACES_SAMPLER_ARG=0.1`.

---

## 7. Persistence and backups

- **Postgres**: nightly logical dump + 15 min WAL archive. Restore
  procedures in [disaster-recovery.md](disaster-recovery.md).
- **Redis**: AOF enabled (`appendonly yes`, `appendfsync everysec`).
  Redis is not the system of record; on data loss the worst case is
  re-delivery of in-flight workflows (idempotency guards downstream).
- **Prompts**: kept in the image. To support hot-reload across replicas
  in production, mount `app/prompts/` from object storage with a
  read-through cache, or distribute updates via image rolls.

---

## 8. Common operational tasks

| Task | `make` shortcut | Raw command |
|------|-----------------|-------------|
| Start stack | `make up` | `docker compose up -d` |
| Stop stack | `make down` | `docker compose down` |
| Tail all logs | `make logs` | `docker compose logs -f` |
| Tail API logs | `make logs-api` | `docker compose logs -f api` |
| Tail worker logs | `make logs-worker` | `docker compose logs -f worker` |
| Rebuild images | `make build` | `docker compose build` |
| Full no-cache rebuild | `make rebuild` | `docker compose build --no-cache --pull` |
| Wipe volumes + restart | `make reset` | `docker compose down -v --remove-orphans && docker compose up -d` |
| Generate migration from model | `make migrate msg="…"` | `docker compose exec api alembic revision --autogenerate -m "…"` |
| Apply pending migrations | `make db-upgrade` | `docker compose exec api alembic upgrade head` |
| Roll back one migration | `make db-downgrade` | `docker compose exec api alembic downgrade -1` |
| Show current revision | `make db-current` | `docker compose exec api alembic current` |
| Open psql prompt | `make shell-db` | `docker compose exec postgres psql -U ai_platform -d ai_platform` |
| Open shell in api | `make shell-api` | `docker compose exec api bash` |
| Run smoke test | `make smoke` | `python scripts/full_smoke_test.py` |
| Trigger DLQ inspection | — | `docker compose exec api python -m app.cli workflows dlq list` |

### Migration volume mount

The `migrations/` directory is bind-mounted into both `api` (read-write) and
`worker` (read-only) containers. This means:

- A migration file created with `make migrate` is **immediately visible** to
  the running containers — no image rebuild needed.
- On the next `docker compose up` (or `make db-upgrade`), the entrypoint
  applies it automatically.
- The Dockerfile still copies `migrations/` into the image so that
  production deployments without volume mounts work correctly.

CLI commands are described in [runbooks.md](runbooks.md).
