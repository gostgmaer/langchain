# Provider Routing

The platform abstracts six LLM providers — **OpenAI, Anthropic, Gemini,
DeepSeek, OpenRouter, xAI** — behind a single API. Integrators never call
providers directly. This document explains how the platform chooses one,
what the failover chains look like, what overrides you have, and how to
plan for cost and capacity at scale.

## 1. Capability matrix

| Capability | OpenAI | Anthropic | Gemini | DeepSeek | OpenRouter | xAI |
|------------|:------:|:---------:|:------:|:--------:|:----------:|:---:|
| generate | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| classify | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| extract | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| summarize | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| rerank | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| embed | ✓ | ✗ | ✓ | ✗ | ✓ | ✗ |

If you request a capability/provider combination that is not supported, the
gateway returns HTTP 422 `validation_error`. Without a provider hint, the
router picks an eligible one for you.

## 2. Routing hints (request-side)

You influence routing in two ways:

1. **Workflow + task** — the workflow handler registry supplies the default
  routing hint for each workflow.
2. **Explicit `provider` selection in the request** — a weak hint that the
   router honors when it is healthy and compatible.

Routing hints map to provider chains:

| Hint | Chain (first → last) |
|------|----------------------|
| `PREMIUM_COMMUNICATION` | Anthropic → OpenRouter |
| `STRUCTURED_JSON` | OpenAI → OpenRouter |
| `LONG_CONTEXT` | Gemini → OpenAI → OpenRouter |
| `BULK_PROCESSING` | DeepSeek → OpenRouter |
| `FALLBACK` | OpenRouter |
| `AUTO` (default) | OpenAI → OpenRouter |

When the requested capability is `embed`, the chain is overridden to
`OpenAI → Gemini` regardless of hint.

`LONG_CONTEXT` is auto-selected when `token_budget.estimated_input_tokens`
exceeds 100 000.

## 3. Selection algorithm

```text
1. Load the tenant policy from the configured policy store.
2. Filter candidates by:
   - tenant allow/deny list
   - data residency
   - circuit breaker state (skip OPEN)
   - max_input_tokens ≥ estimated input
   - capability supported by provider
3. If adaptive routing is enabled and the request is not pinned to a
  capability-specific or explicit provider chain, score candidates by EWMA
  latency, EWMA error rate, and estimated cost.
4. If empty → enqueue retry; if persistent, dead-letter (provider_exhausted).
5. Call head of list.
6. On retriable failure → record EWMA error, advance to next candidate.
7. On full exhaustion → dead-letter (provider_exhausted).
```

The selected provider, model, and reason are emitted as the
`PROVIDER_SELECTED` event for every attempt.

Adaptive routing is controlled by:

```dotenv
AI_PLATFORM_ADAPTIVE_PROVIDER_ROUTING_ENABLED=true
AI_PLATFORM_ADAPTIVE_PROVIDER_LATENCY_WEIGHT=0.35
AI_PLATFORM_ADAPTIVE_PROVIDER_COST_WEIGHT=0.45
AI_PLATFORM_ADAPTIVE_PROVIDER_ERROR_WEIGHT=0.20
```

Explicit workflow/provider policies remain authoritative. Adaptive scoring is
used only when the platform has room to choose among equivalent candidates.

## 4. Per-tenant overrides

A tenant can override:

* The effective routing hint.
* Deny lists (e.g. block xAI entirely).
* Allow lists (e.g. only OpenAI and OpenRouter).
* Per-provider daily token quotas.

The current implementation exposes the policy store as an injectable
interface in [app/providers/router.py](../app/providers/router.py). Standalone
deployments can use the in-memory store; production deployments should back it
with a durable control-plane store before exposing tenant self-service
overrides.

## 5. Cost & capacity planning

Cost is recorded per attempt in `ai_generations` and rolled up into
`usage_metrics`. A typical reference cost-per-1k-tokens table (the platform
keeps its own canonical version — these are illustrative):

| Provider | Model class | Input $/1k | Output $/1k |
|----------|-------------|-----------:|------------:|
| OpenAI | `gpt-4o-mini` | $0.00015 | $0.0006 |
| OpenAI | `gpt-4o` | $0.0025 | $0.01 |
| Anthropic | `claude-haiku` | $0.00025 | $0.00125 |
| Anthropic | `claude-sonnet` | $0.003 | $0.015 |
| Gemini | `flash` | $0.0001 | $0.0004 |
| DeepSeek | `deepseek-chat` | $0.0001 | $0.0002 |
| OpenRouter | passthrough + 5% | — | — |
| xAI | `grok` | varies | varies |

Plan accordingly:

* **High volume / low cost** — keep workflows on `BULK_PROCESSING`.
* **Premium communication** — accept the higher Anthropic cost.
* **Mixed workloads** — set tenant ceilings; the router will fail over to
  cheaper providers when ceilings approach.

## 6. Health, failover, and recovery

* `/health/ready` and `/health` expose one provider component per configured
  adapter, named `provider:<provider>`. A one-key OpenRouter development or E2E
  stack reports `provider:openrouter`.
* Provider health checks call the adapter health probe, map adapter status to
  `ok` or `degraded`, and include capabilities plus provider metadata in the
  component details.
* The router tracks **EWMA error rates** per `(provider, model)`.
* On sustained errors, a circuit breaker opens, and the provider is skipped
  for new requests until a recovery timeout elapses (default 30s). Production
  deployments use Redis-backed breaker state so all API and worker replicas
  share the same provider health view.
* The router never decides failover based on raw exception bursts — a
  health monitor mediates state transitions to prevent retry storms.
* See [scaling.md](scaling.md) for autoscaling guidance under provider
  degradation.

## 7. Provider failure modes

| Failure | Behavior |
|---------|----------|
| 5xx / connection refused | Retriable; advance to next candidate. |
| 429 (rate limit) | Retriable with `Retry-After` or the configured minimum 429 backoff; does not open the provider circuit breaker. |
| 401 / 403 | Non-retriable; alerted; provider disabled until ops fixes credentials. |
| Schema violation in response | Non-retriable on that attempt; the parser may attempt a single repair. |
| Timeout | Retriable; cancel in-flight call. |

## 8. SDK considerations

Integrators do not need a provider SDK. They only need:

* The platform’s HTTP contract ([api.md](api.md)).
* A signing helper ([authentication.md](authentication.md)).
* A polling helper ([getting-started.md](getting-started.md)).

If you must hard-pin a model (e.g. for evaluation), pass
`provider.required_capability` plus `provider.provider` and
`provider.model`. The selected provider is tried first when it is configured,
healthy, and capability-compatible; the router can still fail over to the
remaining chain on retriable provider failures.
