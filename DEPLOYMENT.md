# Deployment (Railway + Cloudflare)

The app is two services behind Cloudflare. The frontend (Caddy) is the only public entry
point; it serves the SPA and reverse-proxies `/api/*` to the backend over Railway's private
network. The backend has **no** public domain.

```
Cloudflare (proxy + WAF + Bot Fight)
        │
        ▼
Railway: frontend (Caddy, $PORT)  ──private──▶  backend (uvicorn, :8000)
                                                   │         │
                                              Postgres     Redis
                                                   ▲
                                            cron: retention (daily)
```

## Railway services

1. **Postgres** and **Redis** — add from Railway's catalog. Note their connection URLs.
2. **backend** — deploy from `backend/` (its `Dockerfile`). Variables:
   - `ENVIRONMENT=production`
   - `DATABASE_URL` = the Postgres URL as `postgresql+asyncpg://…`
   - `REDIS_URL` = the Redis URL
   - `PUBLIC_BASE_URL=https://app.yourdomain.com`
   - `CLIENT_IP_HEADER=X-Client-IP`
   - `JWT_SECRET_KEY`, `TOTP_ENCRYPTION_KEY` (generate: see `backend/.env.example`)
   - `TURNSTILE_SECRET_KEY`
   - E-mail: either `RESEND_API_KEY` (needs a verified domain) **or**, without a domain,
     `EMAIL_BACKEND=smtp` with `SMTP_HOST`/`SMTP_PORT`/`SMTP_USERNAME`/`SMTP_PASSWORD`
     (e.g. Gmail + app password). Plus `EMAIL_FROM` matching the transport.
   - `GEMINI_API_KEY`, and model ids if not the defaults
   - `LOG_JSON=true`
   - **Pre-deploy command:** `alembic upgrade head`
3. **frontend** — deploy from `frontend/` (its `Dockerfile`). Variables:
   - `BACKEND_URL=http://backend.railway.internal:8000` (the private backend address)
   - `VITE_TURNSTILE_SITE_KEY` must be set **at build time** (Railway build arg / variable).
   - Attach the public domain here.
4. **retention (cron)** — same image/repo as backend, schedule `0 3 * * *`, command
   `python -m app.tasks.retention`. It loads the full `Settings`, so it needs every required
   variable of the backend, not just `DATABASE_URL`: at minimum `JWT_SECRET_KEY` and
   `TOTP_ENCRYPTION_KEY` (use Railway variable references, e.g. `${{backend.JWT_SECRET_KEY}}`,
   so the values never drift), plus `ENVIRONMENT=production`.

## Cloudflare

- Proxy the app's DNS record (orange cloud) to the frontend service.
- Turn on **Bot Fight Mode** and a WAF rate-limiting rule on `/api/auth/*`.
- Caddy reads the client IP from `CF-Connecting-IP` and forwards it as `X-Client-IP`, which
  the backend trusts via `CLIENT_IP_HEADER`.

## First admin

Once the backend is up, open a one-off shell on the backend service and run:

```bash
python -m app.cli create-admin --email you@yourdomain.com
```

Then sign in and enable two-factor authentication (required for staff tools).

## Post-deploy checks

- `GET /api/health/ready` returns 200.
- `https://securityheaders.com` grades the public domain (CSP/HSTS come from middleware + Caddy).
- Run an OWASP ZAP baseline scan against the public domain before inviting students.
