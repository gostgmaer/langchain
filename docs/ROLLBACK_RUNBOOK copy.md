# File Upload Service — Rollback Runbook

Until this session, this repo had no real deploy pipeline to roll back from at
all - `.github/workflows/auto-tag-on-main.yml` only bumped a version tag on
every push to main, with no build/test/deploy step behind it (a tag could
exist for a release that was never even verified to build). `.github/workflows/ci-cd.yml`
(added this session, mirroring IAM/payment-microservice's existing pattern)
now builds → pushes to GHCR (`ghcr.io/<owner>/easydev-file-upload-service`) →
dispatches `deploy-core` to `easydev-infra` → tags a release only after a
verified build.

## When to roll back

- Post-deploy, uploads start failing, the virus-scan/cleanup-job background
  work introduced this session misbehaves, or local-storage signed URLs
  (also new this session, RR-30) start rejecting valid requests.

## Step 1: Identify the last-known-good image tag

```bash
gh release list --repo <owner>/file-upload-service --limit 10
gh api /orgs/<owner>/packages/container/easydev-file-upload-service/versions
```

## Step 2: Re-dispatch a deploy with the prior image tag

```bash
gh api repos/<owner>/easydev-infra/dispatches \
  -f event_type=deploy-core \
  -f 'client_payload[service]=file-upload-service' \
  -f 'client_payload[image_tag]=main-build-<KNOWN_GOOD_RUN_NUMBER>'
```

Fallback if `easydev-infra` doesn't support an explicit tag override (confirm
in that repo): re-point `:latest` at the known-good digest and re-fire with no
override, same pattern as the other 3 services' runbooks.

## Step 3: Data-layer considerations

This service has no schema migrations (MongoDB/Mongoose, no migration
framework in use) - an image-only rollback is schema-safe by construction.
Two things this session added that *do* carry state worth checking after a
rollback:

- **`scanStatus` on `File` documents** (RR-30) - if the bad version ran with
  a misconfigured `CLAMAV_HOST`, files uploaded during that window may have
  `scanStatus: 'ERROR'`/`'SKIPPED'` instead of a real result. Rolling back
  the image doesn't retroactively re-scan them - if that matters, re-run
  `FileService.cleanupExpiredFiles()`'s sibling concept doesn't apply here;
  there's no re-scan job yet (a known follow-up, not built this session).
- **`LOCAL_SIGNED_URL_SECRET`** (RR-30) - any signed URLs issued by the bad
  version remain valid (signed with the same secret, which doesn't change on
  rollback) until their embedded expiry passes - this is expected, not a bug.

## Step 4: Verify

```bash
curl -f https://files.easydev.in/health
curl -f https://files.easydev.in/metrics   # confirm the RR-11 metrics endpoint is up post-rollback too
```

Then do one real upload + download round-trip (not just the health check) -
`docker-compose.yml`'s own healthcheck only hits `/health`, which doesn't
exercise the storage adapter at all.

## Known gaps

- `easydev-infra`'s actual support for an explicit `image_tag` override was
  not verified from this repo (same caveat as the other 3 services' runbooks).
- This pipeline and this runbook are new as of this session and have never
  been exercised against a real deploy - treat the first real rollback as a
  test of the runbook itself, not just of the rollback.
