# Notification Service — Rollback Runbook

This service deploys differently from IAM/payment-microservice/file-upload-service:
no Docker image, no registry. `.github/workflows/deploy.yml` builds `dist/` and
SCPs it directly to a fixed server (`/home/opc/notification-service`), then
`pm2 restart`s it. `.github/workflows/auto-tag.yml` creates a semver git tag
after each push to main, but the deploy step never references it - "what's
currently running" is just whatever `dist/` happens to be on the server.

## When to roll back

- Post-deploy, emails stop sending or the service crash-loops under PM2
  (`max-memory-restart 150M` means a memory regression in the new version
  will visibly loop-restart, not just silently degrade).

## Step 1: Find the last-known-good commit/tag

```bash
git tag --list 'v*' --sort=-v:refname | head -5
# or, to find the commit a specific tag points at:
git log -1 v1.4.2
```

## Step 2: Redeploy that ref

This workflow previously only triggered on push to `main` - there was no way
to redeploy an older commit without pushing a new one. It now also accepts
`workflow_dispatch`, so you can re-run it directly against the known-good
tag:

```bash
gh workflow run deploy.yml --repo <owner>/notification-service --ref v1.4.2
```

(Or via the Actions UI: select "Deploy Notification Service" → "Run workflow"
→ pick the tag/branch in the "Use workflow from" dropdown.)

This re-builds `dist/` from that ref, re-uploads it, and `pm2 restart`s with
the older build - functionally a real rollback, not just a description of one.

## Step 3: If GitHub Actions itself is unavailable

Manual fallback directly on the server:

```bash
ssh opc@<SERVER_IP>
cd /home/opc/notification-service
git fetch --tags
git checkout v1.4.2   # only works if the server has a git checkout, not just dist/ + package.json - confirm this before an incident, not during one
npm install --omit=dev --prefer-offline
npm run build
pm2 restart notification --update-env
pm2 save
```

**Unverified**: whether the server actually keeps a full git checkout (the
deploy step only SCPs `dist,package.json,pnpm-lock.yaml` - if the server
directory is *only* ever populated by SCP, there's no `.git` to check out
from, and this fallback path doesn't work as written). Confirm this on the
actual server before treating Step 3 as a real option, not during a live
incident.

## Step 4: Verify

```bash
curl -f https://<notification-host>/v1/health
pm2 logs notification --lines 50
```

Send a real test email through `/v1/email/send` (or whatever the actual
public-facing trigger is) to confirm the rolled-back version's SMTP path
works, not just that the process is up.

## Known gaps

- No environment parity check between what's on the server and what git/CI
  thinks should be there - `pm2 describe` and a `git status` on the server
  are the only ways to confirm drift, and neither happens automatically.
- This service correctly fails closed on missing `CORS_ORIGINS`/`API_KEY` in
  production (`main.ts`) - rollback won't reintroduce that specific class of
  gap, but any other env-var drift introduced by an `--update-env` restart
  using a stale `.env` is not checked.
