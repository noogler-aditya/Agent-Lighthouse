# Architecture

## System Components

```
┌──────────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Your Agent Code    │────▶│  Lighthouse SDK  │────▶│  FastAPI Backend │
│  (Any framework)     │     │  (pip package)   │     │   (Render)      │
└──────────────────────┘     └──────────────────┘     └────────┬────────┘
                                      │                        │
                                      ▼                        ▼
                             ┌──────────────────┐     ┌─────────────────┐
                             │       CLI        │     │  React Dashboard │
                             │  (init/status)   │     │   (Vercel)      │
                             └──────────────────┘     └────────┬────────┘
                                                               │
                                                      ┌────────┴────────┐
                                                      │  Redis + Postgres│
                                                      └─────────────────┘
```

| Component | Technology | Role |
|-----------|-----------|------|
| `frontend/` | React + Vite | Visual dashboard — traces, spans, tokens, state |
| `backend/` | FastAPI + WebSocket | Authenticated API layer over Redis/Postgres |
| `sdk/` | Python (pip) | Instrumentation client — decorators, auto-tracing, CLI |
| Redis | Redis 7+ | Real-time data persistence and event backbone |
| PostgreSQL | Postgres 16+ | User accounts, API keys, persistent storage |

## Request and Data Flow

1. Agent code uses SDK decorators (`@trace_agent`, `@trace_tool`, `@trace_llm`) or auto-instrumentation.
2. SDK sends span data to backend via HTTP (`X-API-Key` header).
3. Backend validates, persists to Redis, and broadcasts via WebSocket.
4. Dashboard pulls trace lists and subscribes to live updates.
5. User inspects graph, token metrics, and agent state.
6. CLI provides terminal-based diagnostics (`status`, `traces`).

## Authentication

Two auth methods:

| Method | Used By | Header |
|--------|---------|--------|
| JWT Bearer token | Dashboard (browser) | `Authorization: Bearer <token>` |
| API key (`lh_` prefix) | SDK, CLI, machine access | `X-API-Key: lh_...` |

- Users register/login via `/api/auth/register` and `/api/auth/login`.
- API keys are issued at registration or via `/api/auth/api-key`.
- Backend enforces scoped permissions (`trace:read`, `trace:write`, `state:read`, `state:write`).

## Trust Boundaries

- SDK and frontend are untrusted clients from backend perspective.
- Backend is the auth boundary and enforces all access checks.
- Redis and Postgres should be private to trusted network scope.

## Primary Operational Risks

- Misconfigured API keys between frontend/backend/SDK
- CORS misconfiguration causing browser-side request failures
- Redis connectivity failures degrading backend to unhealthy state
- Render free tier cold starts causing timeout on first request
