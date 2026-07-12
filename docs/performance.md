# Performance Validation

Performance validation in this repository is driven by the operational harness
at [scripts/platform_validation.py](../scripts/platform_validation.py) and the
k6 submission lanes in [load/k6-workflows.js](../load/k6-workflows.js).

## Signals Collected

The harness scrapes `/metrics` before and after each major suite and records
runtime container samples when Docker is available. The most important metrics
for the generated reports are:

- `ai_platform_request_latency_seconds`
- `ai_platform_queue_depth`
- `ai_platform_queue_lag_seconds`
- `ai_platform_active_workers`
- `ai_platform_provider_latency_seconds`
- `ai_platform_provider_cost_usd_total`
- `ai_platform_workflow_retries_total`
- `ai_platform_dead_letter_jobs_total`
- `ai_platform_embedding_operations_total`
- `ai_platform_embedding_cache_hits_total`
- `ai_platform_semantic_cache_total`
- `ai_platform_context_compression_total`
- `ai_platform_context_compression_tokens_saved_total`
- `ai_platform_reranking_operations_total`

When Docker is available, the harness also captures container CPU and memory
pressure from `docker stats --no-stream` for the API, worker, PostgreSQL, Redis,
and any other visible containers in the stack.

## Generated Reports

Each full run writes a JSON summary and six Markdown reports:

- `smoke-test-report.md`: dependency and startup validation.
- `stress-test-report.md`: aggregate stress and burst results.
- `concurrency-report.md`: explicit 500 and 1000 concurrency profile outcomes.
- `bottleneck-analysis.md`: heuristics that flagged API, worker, queue, or runtime saturation.
- `failure-analysis.md`: resilience drill outcomes and recovery notes.
- `scaling-recommendations.md`: next-step capacity guidance derived from the collected signals.

## Heuristics Used

The current heuristics call out bottlenecks when any of these conditions are
observed:

- Submission latency p95 exceeds 1500 ms.
- Queue exit latency p95 exceeds 5000 ms.
- Sampled workflows dead-letter during the load lanes.
- Runtime CPU or memory exceeds 80% for a visible container.
- Memory/RAG validation checks fail for vector filtering, reranking, or cache behavior.

The scaling recommendations then bias toward the most likely bottleneck:

- High submission p95 suggests scaling the API tier or increasing front-end connection limits.
- High queue exit p95 suggests scaling workers before the API tier.
- PostgreSQL or Redis saturation suggests capacity increases or retention reductions on those tiers.
- Dead letters or repeated failures suggest tightening retry policies and replay processes before raising concurrency ceilings.

## Recommended Workflow

1. Run [scripts/platform_validation.py](../scripts/platform_validation.py) with `--mode full` after infra or provider changes.
2. Run [load/k6-workflows.js](../load/k6-workflows.js) against staging for longer steady-state soak periods.
3. Compare `metric_delta` in `summary.json` between runs instead of relying on absolute counters alone.
4. Keep each run tenant-scoped so queue growth, retries, and dead letters are attributable to one validation window.