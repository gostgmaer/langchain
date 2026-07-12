# VPS Deployment Runbook

This runbook deploys the platform on a single Linux VPS with Docker Compose.

Use this for:
- early production or private tenant rollout
- low to medium traffic where a single node is acceptable

Do not use this as your long-term topology for high availability. Move to
Kubernetes or a managed container platform once uptime and scale requirements
increase.

## 1. Minimum host requirements

- OS: Ubuntu 24.04 LTS (recommended)
- CPU: 4 vCPU
- RAM: 8 GB
- Disk: 80 GB SSD
- Public networking: 80/443 open

For safer headroom:
- CPU: 8 vCPU
- RAM: 16 GB
- Disk: 160 GB SSD

## 2. Install Docker and Compose plugin

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo usermod -aG docker $USER
newgrp docker
docker --version
docker compose version
```

## 3. Clone repo and prepare env

```bash
git clone <your-repo-url> multi-tennet-ai-agent
cd multi-tennet-ai-agent
cp .env.production.minimum.example .env
```

Edit `.env` and inject real values:
- `AI_PLATFORM_DATABASE_URL`
- `AI_PLATFORM_REDIS_URL`
- `AI_PLATFORM_SECURITY_ENCRYPTION_KEYS__v1`
- provider keys such as `AI_PLATFORM_PROVIDER_API_KEYS__openai`
- `AI_PLATFORM_PROVIDER_API_KEYS__openrouter` for fallback
- `AI_PLATFORM_OTEL_EXPORTER_OTLP_ENDPOINT`

## 4. Choose data plane strategy

Preferred production MVP:
- Managed Postgres
- Managed Redis
- Compose only for `api` and `worker`

Fallback single-node strategy (lower reliability):
- Run `postgres` and `redis` containers from `docker-compose.yml`

If you use managed services, your `.env` should point to external endpoints and
you can still run full compose; app services will use your explicit URLs.

## 5. Build and start services

```bash
docker compose pull || true
docker compose -f docker-compose.yml -f docker-compose.managed.yml -f docker-compose.production.yml up -d --build api worker
docker compose ps
```

The image entrypoint runs migrations (`alembic upgrade head`) automatically.

If you intentionally run local Postgres/Redis on the VPS instead of managed
services, use:

```bash
docker compose -f docker-compose.yml -f docker-compose.production.yml up -d --build postgres redis api worker
```

Production override file used above:
- `docker-compose.production.yml`

## 6. Verify health before traffic

```bash
curl -fsS http://127.0.0.1:8000/health/live
curl -fsS http://127.0.0.1:8000/health/ready
curl -fsS http://127.0.0.1:8000/metrics | head
docker compose logs --tail=200 api
docker compose logs --tail=200 worker
```

`/health/ready` must report healthy dependencies, including worker heartbeat and
configured provider adapters.

Optional deploy script in this repo:

```bash
chmod +x deploy/scripts/deploy-healthcheck.sh
./deploy/scripts/deploy-healthcheck.sh http://127.0.0.1:8000
```

## 7. Put behind HTTPS reverse proxy

Use Nginx, Caddy, or your cloud load balancer.

Minimum Nginx upstream shape:

```nginx
server {
    listen 443 ssl http2;
    server_name api.example.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header x-trace-id $request_id;
    }
}
```

Ready-to-copy file in this repo:
- `deploy/nginx/ai-platform.conf`

If your API is behind Cloudflare, use:
- `deploy/nginx/ai-platform.cloudflare.conf`

Enable Nginx site on VPS:

```bash
sudo cp deploy/nginx/ai-platform.conf /etc/nginx/sites-available/ai-platform.conf
sudo ln -sf /etc/nginx/sites-available/ai-platform.conf /etc/nginx/sites-enabled/ai-platform.conf
sudo nginx -t
sudo systemctl reload nginx
```

Cloudflare variant note:
- this repo includes a template at `deploy/nginx/cloudflare-realip.conf`
- install it on VPS before enabling `ai-platform.cloudflare.conf`:

```bash
sudo mkdir -p /etc/nginx/snippets
sudo cp deploy/nginx/cloudflare-realip.conf /etc/nginx/snippets/cloudflare-realip.conf
sudo cp deploy/nginx/ai-platform.cloudflare.conf /etc/nginx/sites-available/ai-platform.conf
sudo ln -sf /etc/nginx/sites-available/ai-platform.conf /etc/nginx/sites-enabled/ai-platform.conf
sudo nginx -t
sudo systemctl reload nginx
```

- keep the snippet synced with Cloudflare official IP list:
    https://www.cloudflare.com/ips/

Automatic refresh option (recommended):

```bash
sudo install -m 0755 deploy/nginx/update-cloudflare-realip.sh /usr/local/bin/update-cloudflare-realip.sh
sudo /usr/local/bin/update-cloudflare-realip.sh /etc/nginx/snippets/cloudflare-realip.conf
sudo nginx -t && sudo systemctl reload nginx
```

Cron example (daily at 03:15 UTC):

```bash
echo '15 3 * * * root /usr/local/bin/update-cloudflare-realip.sh /etc/nginx/snippets/cloudflare-realip.conf && /usr/sbin/nginx -t && /bin/systemctl reload nginx' | sudo tee /etc/cron.d/cloudflare-realip-refresh > /dev/null
```

Apply WAF/rate policies at the edge as needed.

## 8.1 Optional: systemd auto-start for compose stack

This repo includes a unit file at:
- `deploy/systemd/ai-platform.service`

Install it on VPS:

```bash
sudo mkdir -p /opt
sudo rsync -av --delete ./ /opt/multi-tennet-ai-agent/
sudo cp /opt/multi-tennet-ai-agent/deploy/systemd/ai-platform.service /etc/systemd/system/ai-platform.service
sudo systemctl daemon-reload
sudo systemctl enable ai-platform.service
sudo systemctl start ai-platform.service
sudo systemctl status ai-platform.service --no-pager
```

After edits to `.env` or compose files:

```bash
sudo systemctl restart ai-platform.service
```

## 8.2 Optional: systemd timer for Cloudflare IP refresh

Use this instead of cron if your API is behind Cloudflare:

```bash
sudo install -m 0755 deploy/nginx/update-cloudflare-realip.sh /usr/local/bin/update-cloudflare-realip.sh
sudo cp deploy/systemd/cloudflare-realip-refresh.service /etc/systemd/system/cloudflare-realip-refresh.service
sudo cp deploy/systemd/cloudflare-realip-refresh.timer /etc/systemd/system/cloudflare-realip-refresh.timer
sudo systemctl daemon-reload
sudo systemctl enable --now cloudflare-realip-refresh.timer
sudo systemctl list-timers --all | grep cloudflare-realip-refresh
```

Manual run:

```bash
sudo systemctl start cloudflare-realip-refresh.service
```

## 8.3 Optional: rolling restart helper

Use this helper to rebuild and restart API then worker with readiness checks:

```bash
chmod +x deploy/scripts/rolling-restart.sh deploy/scripts/deploy-healthcheck.sh
./deploy/scripts/rolling-restart.sh http://127.0.0.1:8000
```

## 9. Smoke test gate

Run validation from your CI runner or admin workstation:

```bash
python -m pytest -q
python -m ruff check .
python -m mypy app
```

For Docker-backed E2E in this repo:

```bash
python scripts/docker_e2e_smoke.py
```

Open traffic only after smoke passes and readiness remains stable.

## 10. Operations baseline

Daily:
- check `/health/ready`
- review API and worker error logs
- track queue depth and dead-letter growth

Weekly:
- rotate signing and encryption keys according to policy
- verify backup restore points for Postgres and Redis

Release:
- deploy API first, then worker
- confirm readiness after each rollout
- keep rollback image tag available

## 11. Scale path from VPS to production-grade

When any of these happens, move to Kubernetes or managed orchestration:
- sustained CPU above 65%
- queue lag continuously increasing
- single-node downtime is unacceptable
- tenant count or provider throughput grows rapidly

Migration target for this repo:
- use manifests under `k8s/`
- managed Postgres and Redis
- independent HPA for API and worker
- secret manager integration for all keys

## 12. Known validation caveats from latest smoke baseline

Most workflows/plugins pass, but keep watch on:
- openrouter provider probe returning HTTP 404 in smoke harness
- discord workflow malformed JSON path ending in `DEAD`

Treat those as release gates if those paths are in your active tenant scope.

## 13. Final verification command bundle

Use this to produce deploy evidence in one run:

```bash
chmod +x deploy/scripts/deploy-healthcheck.sh deploy/scripts/final-verification.sh
./deploy/scripts/final-verification.sh http://127.0.0.1:8000
```

Artifacts are written under:
- `logs/deployment-verification/<timestamp>/`

Default artifacts:
- `healthcheck.log`
- `compose-ps.log`
- `api.log`
- `worker.log`
- `docker-e2e-smoke.log`

Custom artifact output directory:

```bash
./deploy/scripts/final-verification.sh http://127.0.0.1:8000 logs/deployment-verification/manual-run
```