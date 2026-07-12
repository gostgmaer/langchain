# Configuration Management

The platform reads **every** configuration value through
[`app/core/config.py`](../app/core/config.py) (the `Settings` class). There is
no direct use of `os.environ` or `os.getenv` anywhere in `app/`, and a
dedicated test (`tests/config/test_env_example_sync.py`) enforces that rule.

## Source of truth

```
Settings (pydantic-settings)
    ├── env_prefix          = AI_PLATFORM_
    ├── env_nested_delimiter = __
    ├── case_sensitive       = false
    └── env_file            = .env
```

`Settings` is constructed once at startup by `load_settings()` (LRU-cached).
Failure to validate any field raises `pydantic.ValidationError` **before** the
ASGI application is created, so the process exits fast with a structured
error.

## .env.example contract

[`.env.example`](../.env.example) is the operator-facing manifest. The
following invariants are CI-enforced:

| Invariant | Enforced by |
|-----------|-------------|
| Every `Settings` field has an `AI_PLATFORM_*` entry. | `tests/config/test_env_example_sync.py::test_env_example_is_in_sync_with_settings` |
| No phantom variables (entries with no matching `Settings` field). | same test |
| Nested mapping fields ship with a commented example block. | `test_env_example_documents_every_nested_mapping` |
| Production-required variables carry a `[REQUIRED in production]` marker. | `test_env_example_production_required_variables_documented` |
| Secret-shaped variables ship blank or commented. | `test_env_example_secrets_are_blank` |
| `.env.example` parses cleanly into a valid `Settings`. | `test_env_example_loads_into_settings` |
| No `os.environ` / `os.getenv` outside `Settings`. | `test_app_does_not_read_env_outside_settings` |

If a CI run fails one of these tests, fix `.env.example` (or remove the
offending `os.environ` call) before merging.

## Do we need all environment variables?

No. You do not need to set every variable to integrate with the platform.

- Most variables have safe defaults and are only needed for advanced tuning.
- Keep the full `.env.example` as the contract reference, but set only the
  minimum profile for your environment.
- Add advanced variables later when you need specific behavior (throughput,
  security hardening, cost controls, observability tuning).

### Minimum local integration profile

Use this when integrating another service in local/dev environments:

```dotenv
AI_PLATFORM_ENVIRONMENT=local
AI_PLATFORM_DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/ai_platform
AI_PLATFORM_REDIS_URL=redis://localhost:6379/0

# At least one provider key is needed outside test fixtures.
AI_PLATFORM_PROVIDER_API_KEYS__openai=<key-or-proxy-token>

# Optional when using local proxy endpoints (for example Ollama/OpenAI-compatible gateways).
AI_PLATFORM_PROVIDER_BASE_URLS__openai=http://localhost:11434/v1

# Optional, but recommended for deterministic routing.
AI_PLATFORM_DEFAULT_PROVIDER=openai
AI_PLATFORM_DEFAULT_MODEL=qwen3:14b
AI_PLATFORM_PROVIDER_FALLBACK=openrouter
```

### MVP model-validation profile (remote generation + local embeddings)

Use this profile when you want fast integration validation with real
generation responses from a remote OpenAI-compatible endpoint, while keeping
embeddings local via Ollama.

```dotenv
AI_PLATFORM_ENVIRONMENT=local
AI_PLATFORM_DATABASE_URL=postgresql+asyncpg://ai_platform:ai_platform@localhost:5432/ai_platform
AI_PLATFORM_REDIS_URL=redis://localhost:6379/0

# Generation path (remote)
AI_PLATFORM_PROVIDER_API_KEYS__openai=ollama
AI_PLATFORM_PROVIDER_BASE_URLS__openai=http://155.248.244.237:11434/v1
AI_PLATFORM_DEFAULT_PROVIDER=openai
AI_PLATFORM_DEFAULT_MODEL=gemma4:31b-cloud
AI_PLATFORM_PROVIDER_FALLBACK=openai

# Embedding path (local)
AI_PLATFORM_PROVIDER_API_KEYS__openrouter=ollama
AI_PLATFORM_PROVIDER_BASE_URLS__openrouter=http://localhost:11435/v1
AI_PLATFORM_EMBEDDING_PROVIDER=openrouter
AI_PLATFORM_EMBEDDING_MODEL=qwen3-embedding:0.6b
AI_PLATFORM_EMBEDDING_DIMENSIONS=768

# Optional: only if one workflow needs a different model than the global default.
# AI_PLATFORM_WORKFLOW_DEFAULT_MODELS__support_automation=gemma4:31b-cloud
```

For this MVP profile, you can leave advanced controls at defaults (rate-limit,
quota, adaptive routing weights, prompt hot-reload cadence, OTEL exporter).
Enable those only when you move from model validation to load and reliability
hardening.

For local integration testing, you can keep these defaults unchanged unless
you explicitly need to test those controls:

- `AI_PLATFORM_OTEL_ENABLED=true` (or set `false` to reduce local noise)

### Staging integration profile (recommended baseline)

Use this baseline for shared environments where multiple services integrate
against the same platform instance:

```dotenv
AI_PLATFORM_ENVIRONMENT=staging
AI_PLATFORM_DATABASE_URL=<managed-postgres-url>
AI_PLATFORM_REDIS_URL=<managed-redis-url>

AI_PLATFORM_PROVIDER_API_KEYS__openai=<staging-key>
AI_PLATFORM_PROVIDER_FALLBACK=openrouter

AI_PLATFORM_RATE_LIMIT_BACKEND=redis
AI_PLATFORM_IDEMPOTENCY_BACKEND=redis
```

### Production profile

Production has enforced safety validation in `Settings.enforce_production_safety`.
Treat these as mandatory in addition to your provider/workflow configuration:

- encryption key configuration (`AI_PLATFORM_SECURITY_ACTIVE_KEY_VERSION`, `AI_PLATFORM_SECURITY_ENCRYPTION_KEYS__*`)
- redis-backed rate limit/idempotency/provider CB/quota backends
- at least one provider key configured

### Practical reduction strategy

If your `.env` feels too large, reduce complexity in this order:

1. Keep only required connection + provider + environment entries.
2. Remove per-workflow overrides (`AI_PLATFORM_WORKFLOW_DEFAULT_*`) unless
   you need workflow-specific routing.
3. Keep retry/circuit/quota settings at defaults until you have measured
   production traffic behavior.
4. Add observability and security hardening values as you move from local to
   staging/production.

## Variable catalog

The catalog below is generated from the same field metadata the audit test
uses. The order matches `.env.example` so operators can `diff` the two side
by side.

### Application metadata

| Variable | Type | Default | Notes |
|----------|------|---------|-------|
| `AI_PLATFORM_APP_NAME` | string | `Multi-Tenant AI Platform` | Logged in startup banner. |
| `AI_PLATFORM_APP_VERSION` | string | `0.1.0` | Surfaced via `/health/live`, `/health/ready`, and `/health`. |
| `AI_PLATFORM_ENVIRONMENT` | enum | `local` | One of `local`, `test`, `staging`, `production`. |
| `AI_PLATFORM_DEBUG` | bool | `false` | Must be `false` in production (validated). |
| `AI_PLATFORM_LOG_LEVEL` | enum | `INFO` | `DEBUG` is rejected in production. |

### PostgreSQL

| Variable | Type | Default | Notes |
|----------|------|---------|-------|
| `AI_PLATFORM_DATABASE_URL` | string | `postgresql+asyncpg://postgres:postgres@localhost:5432/ai_platform` | Must use the async asyncpg driver. |
| `AI_PLATFORM_DATABASE_POOL_SIZE` | int 1–100 | `10` | |
| `AI_PLATFORM_DATABASE_MAX_OVERFLOW` | int 0–200 | `20` | |
| `AI_PLATFORM_DATABASE_POOL_TIMEOUT_SECONDS` | float 0–120 | `30.0` | |

### Redis

| Variable | Type | Default | Notes |
|----------|------|---------|-------|
| `AI_PLATFORM_REDIS_URL` | string | `redis://localhost:6379/0` | `redis://` or `rediss://`. |
| `AI_PLATFORM_REDIS_SOCKET_TIMEOUT_SECONDS` | float 0–60 | `5.0` | |

### Health / ingress headers

This service is fully internal and sits behind a trusted API gateway that
performs authentication and authorization. It does not validate or enforce
the headers below — it only reads them into request context for propagation
and logging.

| Variable | Type | Default | Notes |
|----------|------|---------|-------|
| `AI_PLATFORM_HEALTH_CHECK_TIMEOUT_SECONDS` | float 0–30 | `2.0` | Per-component timeout for readiness and aggregate health checks. |
| `AI_PLATFORM_REQUEST_TRACE_HEADER` | string | `x-trace-id` | Normalised to lowercase. |
| `AI_PLATFORM_REQUEST_TENANT_HEADER` | string | `x-tenant-id` | Trusted, forwarded by the gateway; not validated by this service. |
| `AI_PLATFORM_REQUEST_PRINCIPAL_HEADER` | string | `x-principal-id` | Trusted, forwarded by the gateway; not validated by this service. |

### Edge protection

| Variable | Type | Default | Notes |
|----------|------|---------|-------|
| `AI_PLATFORM_REQUEST_MAX_BODY_BYTES` | int 1024–67108864 | `1048576` | Pre-parsing cap. |
| `AI_PLATFORM_RATE_LIMIT_ENABLED` | bool | `true` | |
| `AI_PLATFORM_RATE_LIMIT_BACKEND` | enum | `memory` | `memory` or `redis`; **[REQUIRED outside local/test]** `redis`. |
| `AI_PLATFORM_RATE_LIMIT_REQUESTS_PER_MINUTE` | int 1–100000 | `600` | Per-tenant or per-IP. |
| `AI_PLATFORM_RATE_LIMIT_BURST` | int 1–10000 | `120` | Token-bucket capacity. |

### Idempotency

| Variable | Type | Default | Notes |
|----------|------|---------|-------|
| `AI_PLATFORM_IDEMPOTENCY_ENABLED` | bool | `true` | |
| `AI_PLATFORM_IDEMPOTENCY_BACKEND` | enum | `memory` | `memory` or `redis`; **[REQUIRED outside local/test]** `redis`. |
| `AI_PLATFORM_IDEMPOTENCY_TTL_SECONDS` | int 60–604800 | `86400` | |
| `AI_PLATFORM_IDEMPOTENCY_MAX_ENTRIES` | int 10–1000000 | `10000` | In-process LRU cap. |

### Security / encryption

| Variable | Type | Default | Notes |
|----------|------|---------|-------|
| `AI_PLATFORM_SECURITY_ACTIVE_KEY_VERSION` | string \| null | – | **[REQUIRED outside local/test]** active envelope-encryption key version. |
| `AI_PLATFORM_SECURITY_ENCRYPTION_KEYS__<version>` | secret | – | **[REQUIRED outside local/test]** nested mapping. Inject from a vault. |

### Workflow engine

| Variable | Type | Default | Notes |
|----------|------|---------|-------|
| `AI_PLATFORM_WORKFLOW_QUEUE_NAME` | string | `workflow_queue` | |
| `AI_PLATFORM_WORKFLOW_WORKER_LEASE_SECONDS` | float 0–3600 | `60.0` | |
| `AI_PLATFORM_WORKFLOW_WORKER_POLL_INTERVAL_SECONDS` | float 0–60 | `1.0` | Worker idle poll interval. |
| `AI_PLATFORM_WORKFLOW_WORKER_TIMEOUT_SCAN_INTERVAL_SECONDS` | float 0–300 | `5.0` | Timeout scanner interval. |
| `AI_PLATFORM_WORKFLOW_WORKER_TIMEOUT_BATCH_SIZE` | int 1–10000 | `100` | Timeout scanner batch size. |
| `AI_PLATFORM_WORKFLOW_WORKER_MAX_INFLIGHT_PER_TENANT` | int 1–100000 | `100` | Per-tenant active lease cap to reduce noisy-neighbor risk. |
| `AI_PLATFORM_WORKFLOW_SNAPSHOT_INTERVAL` | int 0–10000 | `25` | Save an event snapshot every N workflow events; `0` disables snapshots. |
| `AI_PLATFORM_WORKFLOW_DEFAULT_TIMEOUT_SECONDS` | int 1–604800 | `1800` | |
| `AI_PLATFORM_WORKFLOW_MAX_ATTEMPTS` | int 1–10 | `3` | |
| `AI_PLATFORM_WORKFLOW_RETRY_INITIAL_BACKOFF_SECONDS` | float 0–3600 | `5.0` | |
| `AI_PLATFORM_WORKFLOW_RETRY_MAX_BACKOFF_SECONDS` | float 0–86400 | `300.0` | |
| `AI_PLATFORM_WORKFLOW_DEFAULT_MODELS__<workflow>` | string | – | Optional per-workflow model fallback when the request omits `provider.model`. |
| `AI_PLATFORM_WORKFLOW_DEFAULT_PROVIDERS__<workflow>` | enum | – | Optional per-workflow preferred provider when the request omits `provider.provider`. Values use the configured provider names (`openai`, `gemini`, `anthropic`, `deepseek`, `openrouter`, `xai`). |
| `AI_PLATFORM_WORKFLOW_DEFAULT_ROUTING_HINTS__<workflow>` | enum | – | Optional per-workflow routing hint override. Values: `auto`, `premium_communication`, `structured_json`, `long_context`, `bulk_processing`, `fallback`. |

> `<workflow>` accepts any registered workflow identifier matching
> `^[a-z][a-z0-9_]*$` — the workflow plugin registry is authoritative
> ([app/workflows/plugin_registry.py](../app/workflows/plugin_registry.py)).
> The set of registered workflows is discoverable at runtime via
> `GET /v1/workflows`; settings validators only enforce the identifier
> format, not registry membership, so env overrides for unknown names load
> cleanly and silently no-op until the workflow is registered.

The `workflow_worker` readiness component considers a worker active when a
Redis heartbeat named `worker_metrics:workflow-worker-*` is fresher than
`max(30, AI_PLATFORM_WORKFLOW_WORKER_POLL_INTERVAL_SECONDS * 10)` seconds.

When these per-workflow defaults are set, the precedence order is:

1. request payload `provider.model` / `provider.provider`
2. `AI_PLATFORM_WORKFLOW_DEFAULT_*__<workflow>`
3. router/provider fallback behavior (`AI_PLATFORM_PROVIDER_FALLBACK`) where applicable

If neither the request nor workflow defaults provide a model, prompt-backed
workflow execution fails fast with a validation error instead of silently
using a code-pinned model.

### Context resolution

| Variable | Type | Default | Notes |
|----------|------|---------|-------|
| `AI_PLATFORM_CONTEXT_CACHE_TTL_SECONDS` | int 0–86400 | `300` | |
| `AI_PLATFORM_MAX_CONTEXT_IDS_PER_REQUEST` | int 0–500 | `50` | |

### Prompt registry

| Variable | Type | Default | Notes |
|----------|------|---------|-------|
| `AI_PLATFORM_PROMPT_REGISTRY_PATH` | string | `app/prompts` | Filesystem path. |
| `AI_PLATFORM_PROMPT_CACHE_TTL_SECONDS` | int 0–86400 | `300` | |
| `AI_PLATFORM_PROMPT_HOT_RELOAD_ENABLED` | bool | `true` | Disable in immutable images. |
| `AI_PLATFORM_PROMPT_RELOAD_INTERVAL_SECONDS` | float 0–300 | `1.0` | |

### Observability (OpenTelemetry)

| Variable | Type | Default | Notes |
|----------|------|---------|-------|
| `AI_PLATFORM_OTEL_ENABLED` | bool | `true` | |
| `AI_PLATFORM_OTEL_SERVICE_NAME` | string | `multi-tenant-ai-platform` | |
| `AI_PLATFORM_OTEL_SERVICE_NAMESPACE` | string | `ai-platform` | |
| `AI_PLATFORM_OTEL_SERVICE_INSTANCE_ID` | string | UUID per process | Override per-pod in Kubernetes. |
| `AI_PLATFORM_OTEL_EXPORTER_OTLP_ENDPOINT` | string \| null | – | **[REQUIRED in production]** when OTEL is enabled. |
| `AI_PLATFORM_OTEL_TRACE_SAMPLE_RATIO` | float 0–1 | `1.0` | |

### AI provider credentials

Provider adapters never read environment variables directly. The
[`app/providers/config.py`](../app/providers/config.py) factory builds
`ProviderConfig` instances from the fields below; if no API key is registered
for a provider, the factory returns `None` and callers must treat that as
"provider not enabled".

| Variable | Type | Default | Notes |
|----------|------|---------|-------|
| `AI_PLATFORM_PROVIDER_API_KEYS__<provider>` | secret | – | Nested mapping. `<provider>` ∈ {`openai`, `gemini`, `anthropic`, `deepseek`, `openrouter`, `xai`}. **[REQUIRED outside local/test]** at least one entry. |
| `AI_PLATFORM_PROVIDER_BASE_URLS__<provider>` | URL | – | Optional override for approved upstream proxies or gateways. Must start with `http://` or `https://`; validation uses the real upstream endpoint. |
| `AI_PLATFORM_PROVIDER_REQUEST_TIMEOUT_SECONDS` | float 0–300 | `30.0` | Shared transport timeout. |
| `AI_PLATFORM_PROVIDER_MAX_RETRY_ATTEMPTS` | int 1–10 | `3` | Shared retry policy. |
| `AI_PLATFORM_PROVIDER_RETRY_INITIAL_BACKOFF_SECONDS` | float 0–3600 | `0.5` | First provider retry delay when the upstream does not send `Retry-After`. |
| `AI_PLATFORM_PROVIDER_RETRY_MAX_BACKOFF_SECONDS` | float 0–86400 | `30.0` | Upper bound for exponential provider retry delay. |
| `AI_PLATFORM_PROVIDER_RETRY_JITTER_RATIO` | float 0–1 | `0.1` | Random jitter applied to provider retry delays. |
| `AI_PLATFORM_PROVIDER_RATE_LIMIT_MIN_BACKOFF_SECONDS` | float 0–86400 | `5.0` | Minimum retry delay for provider HTTP 429 responses that omit `Retry-After`. |
| `AI_PLATFORM_PROVIDER_HEALTH_CHECK_ON_STARTUP` | bool | `false` | When true, startup fails if a configured provider is unavailable. |
| `AI_PLATFORM_PROVIDER_CIRCUIT_BREAKER_BACKEND` | enum | `memory` | `memory` or `redis`; **[REQUIRED outside local/test]** `redis`. |
| `AI_PLATFORM_PROVIDER_QUOTA_BACKEND` | enum | `memory` | `memory` or `redis`; **[REQUIRED outside local/test]** `redis`. |
| `AI_PLATFORM_PROVIDER_DAILY_TOKEN_QUOTAS__<provider>` | int | – | Default daily token quota per tenant for each configured provider key. **[REQUIRED outside local/test]** for every provider in `AI_PLATFORM_PROVIDER_API_KEYS`. |
| `AI_PLATFORM_PROVIDER_CIRCUIT_BREAKER_FAILURE_THRESHOLD` | int 1–100 | `5` | Failures before opening a provider circuit. |
| `AI_PLATFORM_PROVIDER_CIRCUIT_BREAKER_RECOVERY_TIMEOUT_SECONDS` | float 0–3600 | `30.0` | Cooldown before half-open probe. |
| `AI_PLATFORM_PROVIDER_CIRCUIT_BREAKER_HALF_OPEN_SUCCESS_THRESHOLD` | int 1–100 | `1` | Successful probes required before closing. |
| `AI_PLATFORM_PROVIDER_FALLBACK` | enum \| null | `openrouter` in the shipped examples | When set, requests for unconfigured providers are transparently served by this one. Use `openrouter` for local, staging, E2E, and single-provider deployments. In production the fallback must itself have a key registered. |
| `AI_PLATFORM_DEFAULT_PROVIDER` | enum \| null | – | Platform-wide default provider applied to a workflow when no higher-precedence layer specifies one (see resolution chain below). Allowed values: `openai`, `gemini`, `anthropic`, `deepseek`, `openrouter`, `xai`. |
| `AI_PLATFORM_DEFAULT_MODEL` | string \| null | – | Platform-wide default model applied when request-level, workflow-level, and plugin-level model values are absent. |
| `AI_PLATFORM_PROMPT_DEFAULT_PROVIDERS__<PROMPT_KEY>` | enum | – | Per-prompt provider override keyed by `prompt_id`. The `<PROMPT_KEY>` portion uses underscores in place of dots — e.g. `AI_PLATFORM_PROMPT_DEFAULT_PROVIDERS__CALENDAR_MEETING_EXTRACTION=deepseek` overrides the `calendar.meeting_extraction` prompt. Lets you mix providers prompt-by-prompt (one prompt on `openai`, another on `anthropic`, another on `deepseek`) without code changes. Resolution order for a workflow handler's default provider: (1) request `provider.provider`, (2) `AI_PLATFORM_WORKFLOW_DEFAULT_PROVIDERS__<workflow>`, (3) `AI_PLATFORM_PROMPT_DEFAULT_PROVIDERS__<prompt>`, (4) `metadata.default_provider` in the prompt YAML, (5) plugin spec `default_provider`, (6) `AI_PLATFORM_DEFAULT_PROVIDER`. |

Configured providers also appear in `/health/ready` as `provider:<provider>`
components. For OpenRouter the adapter health check calls the configured base
URL's OpenAI-compatible models endpoint. Local and staging validation should use
the official OpenRouter endpoint with a real key.

#### Configure Gemini primary with OpenRouter fallback

For local development, staging, and Docker E2E, configure Gemini in `.env` as
the preferred workflow provider and keep OpenRouter as the runtime fallback
when Gemini is unavailable.

1. Create or obtain a Gemini API key and an OpenRouter API key.
2. Put both in your local `.env` (never commit them):

   ```dotenv
   AI_PLATFORM_PROVIDER_API_KEYS__gemini="<your-gemini-key>"
   AI_PLATFORM_PROVIDER_API_KEYS__openrouter="sk-or-..."
   AI_PLATFORM_PROVIDER_FALLBACK="openrouter"
   ```

   Docker Compose and Docker E2E read the same credentials from `.env`.

3. Set workflow defaults explicitly in `.env` for each workflow that should use
   Gemini by default:

   ```dotenv
   AI_PLATFORM_WORKFLOW_DEFAULT_PROVIDERS__support_automation="gemini"
   AI_PLATFORM_WORKFLOW_DEFAULT_MODELS__support_automation="gemini-2.0-flash"
   AI_PLATFORM_PROVIDER_MODEL_ALIASES__openrouter__gemini-3.1-flash-lite="google/gemini-2.0-flash-001"
   ```

   Repeat the same pattern for `ai_communication_automation`,
   `job_automation`, `recruiter_automation`, `calendar_automation`,
   `crm_workflow`, `crm_workflows`, and `document_intelligence` when they
   should all use the same provider/model.

4. Workflow requests can now omit the `provider` block entirely and use those
   env-driven workflow defaults.

   If a caller wants to pin explicitly, use Gemini model names directly:

   - `provider=gemini`
   - `model=gemini-2.0-flash`

5. Keep transparent fallback enabled so requests still resolve through
   OpenRouter when Gemini is unavailable:

   ```dotenv
   AI_PLATFORM_PROVIDER_FALLBACK="openrouter"
   AI_PLATFORM_PROVIDER_MODEL_ALIASES__openrouter__gemini-3.1-flash-lite="google/gemini-2.0-flash-001"
   ```

   With this set, the router still prefers Gemini when it is available, while
   unconfigured or failing providers can fall through to the real OpenRouter
   adapter using a provider-pinned OpenRouter model alias for the Gemini
   workflow default.

6. `configured_providers(settings)` will report whichever direct keys are set.
   With both keys present locally, readiness exposes `provider:gemini` and
   `provider:openrouter`.

This gives the team a Gemini-first loop with a real fallback path in every
local and staging environment. If you later decide to change the primary model
or provider for a specific workflow, do it through the workflow-default
settings rather than editing handler code.

## Production validation

`Settings.enforce_production_safety` (a `model_validator`) blocks startup when
`AI_PLATFORM_ENVIRONMENT=production` and any of the following are true:

- `debug=true`
- `log_level=DEBUG`
- `otel_enabled=true` but `otel_exporter_otlp_endpoint` is unset
- encryption active key or key material is missing
- rate limiting or idempotency backend is not `redis`
- no provider API key is configured

These checks run during `Settings()` construction; the FastAPI app is never
instantiated if they fail.

## Startup audit log

`create_app` logs a redacted snapshot of the resolved settings under the
`settings.loaded` event. Secret-typed fields (anything declared as `SecretStr`
or a `dict[str, SecretStr]`) are replaced with `***` in the log.

## Docker

The runtime container reads variables directly from the process environment.
`docker-compose.yml` reads `.env` from the project root and injects the
`AI_PLATFORM_*` variables alongside the Postgres / Redis credentials.

Compose starts both the API and worker. Run `docker compose up api worker
postgres redis` for a complete local event-driven stack.

The compose file additionally consumes a small set of non-application
variables (`POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`,
`API_HOST_PORT`). These are listed in `DOCKER_COMPOSE_VARIABLES` in
`app/core/config_audit.py`; adding a new entry there is the documented way to
introduce another non-application variable.

## Kubernetes (future migration)

The same `AI_PLATFORM_*` names map cleanly to a `ConfigMap` + `Secret` pair:

- Non-secret variables → `ConfigMap` keys, mounted via `envFrom.configMapRef`.
- Secret-shaped variables (`SECURITY_ENCRYPTION_KEYS__<version>`) →
  `Secret`, mounted via `envFrom.secretRef`.
- `AI_PLATFORM_OTEL_SERVICE_INSTANCE_ID` should be injected per-pod:

  ```yaml
  env:
    - name: AI_PLATFORM_OTEL_SERVICE_INSTANCE_ID
      valueFrom:
        fieldRef:
          fieldPath: metadata.uid
  ```

Because field names are stable and the audit test enforces sync, manifest
templates can grep `.env.example` directly to generate the ConfigMap keys.

## Adding a new configuration variable

1. Add the field to `Settings` in `app/core/config.py` with a typed default
   and validators (range / format).
2. If the value is sensitive, type it as `SecretStr` (or `dict[str, SecretStr]`
   for versioned mappings) and add the field name to `NESTED_MAPPING_FIELDS`
   in `app/core/config_audit.py` if applicable.
3. Add a matching `AI_PLATFORM_<UPPER_FIELD_NAME>=` line to `.env.example`,
   grouped under the relevant heading with a one-line comment.
4. Run `pytest tests/config -q`. CI will fail the merge if you skip step 3.
5. Update `docs/configuration.md` (this file) with the new row.
