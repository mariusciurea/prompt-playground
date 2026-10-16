# AI Playground

A course platform for learning prompt engineering and AI security with Google Gemini.
It is **access-gated**: anyone can register, but only members of an active course cohort can
run the interactive features. Students get a daily prompt quota; admins and instructors manage
access from an admin panel.

| Page | What it does |
| --- | --- |
| **Playground** | Write a system + user prompt, tune the temperature, watch the answer stream in. |
| **Engage** | Prompt-injection game: talk the model into revealing a password hidden in its system prompt, then learn why each defence failed. |
| **Reservation** | Chat with a Google ADK agent that can book movies and read stored data — a demo of *excessive agency*. |
| **Skills Lab** | Install skills that hide prompt-injection payloads and watch them exfiltrate fake secrets; toggle defences and see what stops the attack. |
| **Learn** | Short security best-practice articles (prompt injection, vetting skills, least privilege). Open to everyone, even without access. |
| **Admin** | Cohorts, e-mail import (CSV/XLSX), access requests, user management, usage stats, audit log. |

## Architecture

- **`backend/`** — FastAPI (async SQLAlchemy + Postgres, Redis for rate limits/cache), Gemini
  via `google-genai`, agents via Google ADK. Password auth with mandatory e-mail verification,
  rotating refresh tokens, CSRF protection, Turnstile, TOTP for staff, and a per-user daily quota.
- **`frontend/`** — Vite + React + TypeScript SPA, served by Caddy which also proxies `/api`
  to the backend (single origin, `SameSite=Strict` cookies, no CORS).

Both run behind Cloudflare in production. See [DEPLOYMENT.md](DEPLOYMENT.md).

## Local development

Everything in one command (needs Docker):

```bash
# in a .env at the repo root, set JWT_SECRET_KEY, TOTP_ENCRYPTION_KEY (and optionally GEMINI_API_KEY)
docker compose up --build
# app on http://localhost:8080
```

Or run the two sides separately:

```bash
# Backend (no Docker needed: embedded Postgres via pgserver)
cd backend
uv sync
uv run python scripts/dev_db.py --write-env   # starts a local Postgres, writes DATABASE_URL into .env
cp .env.example .env                           # then fill JWT_SECRET_KEY, TOTP_ENCRYPTION_KEY, GEMINI_API_KEY
uv run alembic upgrade head
uv run uvicorn app.services:create_app --factory --reload
uv run python -m app.cli create-admin --email you@example.com

# Frontend
cd frontend
npm install
npm run dev                                    # http://localhost:5173, proxies /api to :8000
```

## Tests & checks

```bash
# Backend (spins up a throwaway Postgres; no network, no real Gemini)
cd backend && uv run ruff check . && uv run mypy app && uv run pytest -q -p no:logging

# Frontend
cd frontend && npm run typecheck && npx eslint . && npm run test && npm run build
```

## A note on the teaching sandboxes

The Reservation agent's `read_from_disc` tool and the entire Skills Lab are **intentionally
insecure teaching aids**. Their tools are fakes that never touch the real network or disk, and
every "secret" is a decoy. Never wire them to real files, credentials, or outbound requests.
