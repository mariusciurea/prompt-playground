# CLAUDE.md

Guidance for Claude Code (claude.ai/code) when working in this repository.

## What this is

An access-gated course platform for prompt engineering and AI security, built on Google
Gemini. A **FastAPI backend** (`backend/`) and a **Vite + React + TypeScript frontend**
(`frontend/`), served as a single origin by Caddy behind Cloudflare. See README.md for the
user-facing description and DEPLOYMENT.md for the Railway/Cloudflare topology.

## Commands

```bash
# Backend (uv; embedded Postgres for dev/tests, no Docker required)
cd backend
uv sync
uv run python scripts/dev_db.py --write-env        # local Postgres → DATABASE_URL in .env
uv run alembic upgrade head
uv run uvicorn app.services:create_app --factory --reload
uv run ruff check . && uv run ruff format . && uv run mypy app
uv run pytest -q -p no:logging                     # -p no:logging silences pgserver's noisy teardown
uv run python -m app.cli create-admin --email you@example.com
uv run alembic revision --autogenerate -m "msg"    # after changing db_models

# Frontend
cd frontend
npm install
npm run dev                                        # proxies /api → :8000
npm run gen:api                                    # regenerate src/api/schema.d.ts from backend/openapi.json
npm run typecheck && npx eslint . && npm run test && npm run build

# Whole stack
docker compose up --build                          # app on :8080
```

## Backend architecture (`backend/app/`)

Entry point is `services.py` (`create_app()` factory). Layering is strict: **routers →
domain → crud → db**, and nothing in `domain/`/`crud/` imports FastAPI. Long-lived resources
(engine, store, http client, email sender, LLM, agents) are built once in `core/lifespan.py`
into `core/state.AppState` and reached through typed dependencies in `core/state.py`.

- `core/` — `settings.py` (pydantic-settings, the only place env vars are read; extend
  `Settings`, never add `os.getenv` elsewhere), `logging.py`, `exceptions.py` (domain errors
  → JSON; raise an `AppError` subclass, never return error dicts), `middleware.py` (request
  ID, security headers, CSRF double-submit), `store.py` (`Store` protocol: Redis in prod,
  in-memory otherwise), `rate_limit.py`, `state.py`.
- `db_models/` — SQLAlchemy 2 models (UUID PKs, `str_enum` for enums). `data_models/` —
  Pydantic request/response schemas (base `Schema` forbids extras).
- `crud/` — data access only. `domain/` — business rules: `auth.py` (register/verify/login/
  refresh-rotation/reset), `access.py` (cohort access, Redis-cached with a generation counter),
  `quota.py` (atomic daily reservation + refund), `staff.py` (admin/instructor actions, all
  audited), `imports.py` (CSV/XLSX e-mail parsing), `prompting.py` (the LLM/agent guard:
  availability → rate limit → one-stream lock → quota, then SSE streaming + history).
- `llm/gemini.py` — async streaming `LLMService`. `llm/adk.py` — shared ADK model + session
  service. `agents/runtime.py` — wraps ADK runners into a typed event stream; `agents/
  reservation/` and `agents/skills_lab/`.
- `routers/` — thin HTTP layer; `routers/admin/` is the staff sub-app. `content/` — static
  Engage levels, Playground examples, Learn articles (Markdown), demos.
- `tasks/retention.py` — daily cron (purge unverified accounts and expired history).

### Security-relevant design points

- **Engage** passwords and system prompts live only in `content/engage_levels.py` and are
  checked server-side; they must never be serialized to the client (`EngageLevelOut` omits them).
- **Skills Lab** (`agents/skills_lab/`) and the Reservation `read_from_disc` tool are
  **intentionally insecure teaching aids**. All Skills Lab tools are fakes backed by the ADK
  session state — `http_request`/`send_email` only append to in-memory logs, nothing hits the
  network or disk. `tests/test_skills_lab_tools.py` asserts the module imports no network/fs
  client. Keep it that way; never wire real I/O.
- The malicious catalog skills assemble their payloads programmatically (HTML comment / Unicode
  tags / Base64) in `catalog.py`; the `scanner.py` detector and the `catalog` are tested
  together so every technique stays detectable.
- Prompt length is bounded by `Settings.max_prompt_length` **server-side** (the Pydantic cap is
  just an outer ceiling); any new prompt field needs the same check.
- Admins are exempt from rate limits and quota by role checks in `dependencies.py`/`quota.py` —
  preserve those when adding guarded endpoints.

## Frontend architecture (`frontend/src/`)

`api/client.ts` is the single fetch wrapper (adds the CSRF header on unsafe calls, parses
`{error:{code,message}}` into `ApiError`, and exposes `sse()` for streaming). `api/types.ts`
holds hand-written response types; `api/schema.d.ts` is generated (don't edit). `auth/
AuthContext.tsx` owns session state and does one silent refresh on a 401. `components/guards.tsx`
gate routes **for UX only — the server is the real authority**. Pages live in `pages/`, the
authenticated shell in `components/Shell.tsx`. Model output is always rendered through
`SafeMarkdown` (react-markdown, raw HTML disabled).

## Testing

Backend tests use a throwaway embedded Postgres (`pgserver`), migrated with Alembic, and fake
e-mail/HTTP/LLM/agents — **no test hits the network or the real Gemini API**. Key fixtures in
`tests/conftest.py`: `settings` (isolated from the dev env), `client`/`make_client` (an
`ApiClient` that fetches and echoes the CSRF token), `login`/`register_and_verify`. The
`_env_file=None` trick keeps `Settings` off the developer's `.env`. Run with `-p no:logging`.

## Database changes

Edit `db_models/`, then `uv run alembic revision --autogenerate -m "…"` and review the
generated file (partial indexes and `str_enum` columns need a glance). `migrations/env.py`
reads the URL from `Settings` (or `config.attributes["database_url"]` in tests) and targets
`Base.metadata`.
