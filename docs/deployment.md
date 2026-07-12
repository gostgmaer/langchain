# Deployment Setup

This guide covers the supported ways to run the platform from a developer
machine through a production-like Kubernetes deployment.

For single-host Linux rollout, see [vps-deployment.md](vps-deployment.md).

## 1. Local Python

Install the package and dev tools:

```bash
python -m pip install -e .[dev]
```

Create local configuration:

```bash
cp .env.example .env
```

At minimum, point `AI_PLATFORM_DATABASE_URL` and `AI_PLATFORM_REDIS_URL` at
reachable services. Configure a real Gemini key for primary execution and a
real OpenRouter key for fallback in local, staging, and E2E validation, then
set explicit workflow defaults in `.env`:

```dotenv
AI_PLATFORM_PROVIDER_API_KEYS__gemini="<your-gemini-key>"
AI_PLATFORM_PROVIDER_API_KEYS__openrouter="sk-or-..."
AI_PLATFORM_PROVIDER_FALLBACK="openrouter"
AI_PLATFORM_PROVIDER_MODEL_ALIASES__openrouter__gemini-3.1-flash-lite="google/gemini-2.0-flash-001"
AI_PLATFORM_WORKFLOW_DEFAULT_PROVIDERS__support_automation="gemini"
AI_PLATFORM_WORKFLOW_DEFAULT_MODELS__support_automation="gemini-2.0-flash"
# Platform-wide default provider applied when no higher-precedence override
# is configured for a workflow.
AI_PLATFORM_DEFAULT_PROVIDER="gemini"
# Per-prompt provider overrides (optional). Use underscores in place of dots.
# AI_PLATFORM_PROMPT_DEFAULT_PROVIDERS__ANALYTICS_ANOMALY_DETECTION="openai"
POSTGRES_HOST_PORT="5432"
```

See [configuration.md](configuration.md#provider-configuration) for the full
provider-resolution precedence chain (six levels).

`POSTGRES_HOST_PORT` publishes the Compose Postgres container to the host so
you can inspect data with `psql`, a database IDE, or another local client.

Apply migrations:

```bash
alembic upgrade head
```

Run the API and one worker in separate terminals:

```bash
uvicorn app.main:app --reload
python -m app.workers.main
```

Validate:

```bash
curl http://127.0.0.1:8000/health/live
curl http://127.0.0.1:8000/health/ready
```

`/health/ready` is expected to return `status: "ok"` only after the API can
reach PostgreSQL, Redis, the event-store tables, the Redis workflow queues, at
least one workflow-worker heartbeat, and every configured provider adapter. In
the Gemini-first development loop, the provider components are typically
`provider:gemini` and `provider:openrouter`.

## 2. Docker Compose

Compose runs API, worker, Postgres, and Redis:

```bash
docker compose up --build api worker postgres redis
```

The image entrypoint runs `alembic upgrade head` before the requested process.
When Compose starts the worker with `command: ["python", "-m", "app.workers.main"]`,
the entrypoint now executes that worker command after migrations. Alembic uses
a Postgres advisory lock, so concurrent API/worker startup does not apply the
same migration twice.

The worker container is not an HTTP server, so the base Compose file disables a
Docker healthcheck for it. Platform readiness still verifies worker availability
through the Redis heartbeat consumed by the `workflow_worker` health component.

For local Compose, shared-state backends default to `memory`. For staging or
production-like Compose, set:

```dotenv
AI_PLATFORM_RATE_LIMIT_BACKEND=redis
AI_PLATFORM_IDEMPOTENCY_BACKEND=redis
AI_PLATFORM_PROVIDER_CIRCUIT_BREAKER_BACKEND=redis
AI_PLATFORM_PROVIDER_QUOTA_BACKEND=redis
AI_PLATFORM_PROVIDER_DAILY_TOKEN_QUOTAS__gemini=250000
AI_PLATFORM_PROVIDER_DAILY_TOKEN_QUOTAS__openrouter=250000
AI_PLATFORM_SECURITY_ACTIVE_KEY_VERSION=v1
AI_PLATFORM_SECURITY_ENCRYPTION_KEYS__v1=<inject>
```

## 3. Kubernetes

Reference manifests live in [k8s](../k8s):

| File | Purpose |
|------|---------|
| [namespace.yaml](../k8s/namespace.yaml) | Namespace. |
| [configmap.yaml](../k8s/configmap.yaml) | Non-secret production settings. |
| [secret.example.yaml](../k8s/secret.example.yaml) | Example secret keys; replace with a real secret manager. |
| [api-deployment.yaml](../k8s/api-deployment.yaml) | API Deployment with health probes. |
| [worker-deployment.yaml](../k8s/worker-deployment.yaml) | Worker Deployment. |
| [service.yaml](../k8s/service.yaml) | ClusterIP Service for API pods. |
| [hpa.yaml](../k8s/hpa.yaml) | API and worker autoscaling baselines. |
| [networkpolicy.yaml](../k8s/networkpolicy.yaml) | Default-deny scaffold and API/worker allowances. |

Apply order:

```bash
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f <your-secret-or-external-secret>.yaml
kubectl apply -f k8s/api-deployment.yaml
kubectl apply -f k8s/worker-deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/hpa.yaml
kubectl apply -f k8s/networkpolicy.yaml
```

Production deployments should use managed Postgres and Redis, not single pods
in the application namespace.

## 4. Production Required Settings

`AI_PLATFORM_ENVIRONMENT=production` fails startup unless these are true:

* `AI_PLATFORM_RATE_LIMIT_BACKEND=redis`
* `AI_PLATFORM_IDEMPOTENCY_BACKEND=redis`
* `AI_PLATFORM_PROVIDER_CIRCUIT_BREAKER_BACKEND=redis`
* `AI_PLATFORM_PROVIDER_QUOTA_BACKEND=redis`
* `AI_PLATFORM_PROVIDER_DAILY_TOKEN_QUOTAS__<provider>` set for every configured provider key
* `AI_PLATFORM_SECURITY_ACTIVE_KEY_VERSION` and matching encryption key set
* `AI_PLATFORM_OTEL_EXPORTER_OTLP_ENDPOINT` set when OTEL is enabled
* at least one `AI_PLATFORM_PROVIDER_API_KEYS__<provider>` configured

See [configuration.md](configuration.md) for the full catalog.

## 5. Smoke Validation

Run the fast local gate:

```bash
python -m pytest -q
python -m ruff check .
python -m mypy app
```

Run Docker-backed integration smoke tests when Docker is available:

```bash
RUN_TESTCONTAINERS=1 python -m pytest tests/integration/test_testcontainers_smoke.py -q
```

Run the local Docker E2E smoke suite with real OpenRouter traffic:

```powershell
docker compose -f docker-compose.yml -f docker-compose.e2e.yml down -v --remove-orphans
docker compose -f docker-compose.yml -f docker-compose.e2e.yml up -d postgres redis api worker
python scripts/docker_e2e_smoke.py
```

The suite waits for `/health/ready` to reach `status: "ok"` and asserts the
required components: `postgresql`, `redis`, `event_store`, `workflow_queue`,
`workflow_worker`, and `provider:openrouter`. It then covers metrics,
capability enqueue endpoints, workflow status/job polling, tool callbacks,
tenant isolation, validation errors, idempotency replay/conflict,
dead-letter listing, and dead-letter replay. The default scenario set is
`E2E_SCENARIO_SET=core` so the run stays inside typical OpenRouter free-model
rate limits. Use `E2E_SCENARIO_SET=full` for the larger provider-heavy matrix
when your OpenRouter account/model has enough quota. Each run writes:

* `logs/docker-e2e/<timestamp>/summary.md`
* `logs/docker-e2e/<timestamp>/requests.jsonl`

The request log captures the readiness attempts, every API request/response,
and all negative-scenario responses used as validation evidence.

The E2E overlay requires `AI_PLATFORM_PROVIDER_API_KEYS__openrouter` in `.env`
and keeps provider traffic on the real OpenRouter endpoint. To test a specific
OpenRouter model, set `E2E_OPENROUTER_MODEL`; the default is
`openrouter/auto`. Real upstream models, especially free OpenRouter models,
can take longer than local checks. The harness defaults to
`E2E_POLL_TIMEOUT_SECONDS=180` and `E2E_PROVIDER_COOLDOWN_SECONDS=20`; set
`E2E_WORKFLOW_TIMEOUT_SECONDS` only when you need each submitted workflow to
use a custom API-level timeout instead of the server default.

Run the load smoke script against staging or a canary tenant:

```bash
k6 run -e BASE_URL=https://staging-api.example.com \
  -e TENANT_ID=tenant_load_test \
  load/k6-workflows.js
```

See [end-to-end-validation.md](end-to-end-validation.md) for workflow-level
integration validation.