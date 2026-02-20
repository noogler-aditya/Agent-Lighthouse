<p align="center">
  <img src="https://img.shields.io/badge/🔦-Agent%20Lighthouse-6366f1?style=for-the-badge" alt="Agent Lighthouse"/>
</p>

<h1 align="center">Agent Lighthouse</h1>

<p align="center">
  <strong>Multi-Agent Observability Platform</strong><br>
  Trace execution, monitor costs, and debug state — for any AI agent framework.
</p>

<p align="center">
  <a href="https://pypi.org/project/agent-lighthouse/"><img src="https://img.shields.io/pypi/v/agent-lighthouse" alt="PyPI"/></a>
  <img src="https://img.shields.io/badge/python-3.9+-3776ab?logo=python&logoColor=white" alt="Python"/>
  <img src="https://img.shields.io/badge/react-18+-61dafb?logo=react&logoColor=black" alt="React"/>
  <img src="https://img.shields.io/badge/fastapi-0.109+-009688?logo=fastapi&logoColor=white" alt="FastAPI"/>
  <img src="https://img.shields.io/badge/license-MIT-green" alt="License"/>
</p>

---

## Get Started in 2 Minutes

```bash
pip install agent-lighthouse
agent-lighthouse init          # interactive login → writes .env
```

Then add decorators to your code:

```python
from agent_lighthouse import trace_agent, trace_tool, get_tracer

@trace_agent("Researcher")
def research(topic):
    return search(topic)

@trace_tool("Web Search")
def search(query):
    return duckduckgo.search(query)

tracer = get_tracer()
with tracer.trace("My Workflow"):
    research("AI observability")
```

Traces appear on the [dashboard](https://agent-lighthouse.vercel.app) in real time.

---

## Why Agent Lighthouse?

When running multi-agent systems (CrewAI, LangGraph, AutoGen, etc.), debugging is hard:

| Challenge | What Lighthouse Gives You |
|-----------|--------------------------|
| Can't see inside agent loops | **Trace graph** — interactive flowchart of execution |
| Which agent caused the failure? | **Span-level errors** with input/output data |
| Token costs spiral without visibility | **Token monitor** — real-time cost per agent/tool |
| Can't inspect agent memory | **State inspector** — pause, view, edit, resume |
| Debugging requires parsing logs | **Visual dashboard** with search and filtering |

---

## Features

| Feature | Description |
|---------|-------------|
| 🔍 **Trace Visualization** | Interactive graph showing agent calls, tools, and LLM spans |
| 💰 **Token Monitor** | Track token usage and costs per agent, tool, and model |
| 🔧 **State Inspector** | Pause execution, inspect memory as JSON, edit, and resume |
| ⚡ **Real-Time Updates** | WebSocket-powered live dashboard updates |
| 🖥️ **CLI** | `init`, `status`, `traces` from terminal — zero browser required |
| 🔌 **Framework Agnostic** | Works with LangChain, CrewAI, AutoGen, or plain Python |
| 🪄 **Auto-Instrumentation** | `import agent_lighthouse.auto` — zero code changes |

---

## CLI

```bash
agent-lighthouse init              # Login + write .env
agent-lighthouse status            # Check health + auth
agent-lighthouse status --json     # Machine-readable output
agent-lighthouse traces --last 5   # List recent traces
al traces --last 3 --json          # Short alias
```

---

## SDK Usage

### Decorators (Recommended)

```python
from agent_lighthouse import trace_agent, trace_tool, trace_llm, get_tracer

@trace_tool("Web Search")
def search_web(query: str) -> list:
    return requests.get(f"https://api.search.com?q={query}").json()

@trace_llm("GPT-4", model="gpt-4", cost_per_1k_prompt=0.03)
def call_gpt4(prompt: str):
    return openai.chat.completions.create(...)

@trace_agent("Research Agent")
def research_agent(topic: str):
    results = search_web(topic)
    analysis = call_gpt4(f"Analyze: {results}")
    return analysis

tracer = get_tracer()
with tracer.trace("Research Workflow"):
    research_agent("AI Trends 2025")
```

### Auto-Instrumentation

No decorators needed — import once at the top of your script:

```python
import agent_lighthouse.auto
```

Captures OpenAI, Anthropic, and HTTP calls automatically. Content capture is off by default:

```bash
export LIGHTHOUSE_CAPTURE_CONTENT=true
```

### State Inspection

```python
tracer = get_tracer()
tracer.update_state(
    memory={"goal": "...", "plan": plan},
    context={"current_step": "planning"},
    variables={"temperature": 0.7},
)
```

---

## Local Development

### Prerequisites

- Python 3.9+, Node.js 18+, Redis (or Docker)

### Option 1: Docker Compose

```bash
git clone https://github.com/noogler-aditya/Agent-Lighthouse.git
cd Agent-Lighthouse
docker-compose up -d
```

### Option 2: Manual Setup

```bash
# Redis + Postgres
docker run -d -p 6379:6379 redis:7-alpine
docker run -d -p 5432:5432 \
  -e POSTGRES_USER=lighthouse \
  -e POSTGRES_PASSWORD=lighthouse \
  -e POSTGRES_DB=lighthouse \
  postgres:16-alpine

# Backend
cd backend
pip install -r requirements.txt
export MACHINE_API_KEYS=local-dev-key:trace:write|trace:read
export JWT_SECRET=dev-secret
export ALLOWED_ORIGINS=http://localhost:5173
export DATABASE_URL=postgresql://lighthouse:lighthouse@localhost:5432/lighthouse
python3 -m uvicorn main:app --reload --port 8000

# Frontend (new terminal)
cd frontend
npm install
npm run dev
```

### Access Points

| Service | URL |
|---------|-----|
| Dashboard | http://localhost:5173 |
| API Docs | http://localhost:8000/docs |
| WebSocket | ws://localhost:8000/ws |

---

## API Reference

### Traces

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/traces` | List traces (paginated, searchable) |
| `POST` | `/api/traces` | Create a new trace |
| `GET` | `/api/traces/:id` | Get trace details with all spans |
| `DELETE` | `/api/traces/:id` | Delete a trace |
| `POST` | `/api/traces/:id/complete` | Mark trace as complete |
| `GET` | `/api/traces/:id/tree` | Get trace as hierarchical tree |
| `GET` | `/api/traces/:id/export` | Download trace as JSON |
| `GET` | `/api/traces/:id/metrics` | Token/cost summary |

### Spans

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/traces/:id/spans` | Create a span |
| `POST` | `/api/traces/:id/spans/batch` | Batch create up to 100 spans |
| `PATCH` | `/api/traces/:id/spans/:span_id` | Update span (status, output, tokens) |

### State & Execution Control

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/state/:id` | Get current state |
| `POST` | `/api/state/:id` | Initialize state |
| `PATCH` | `/api/state/:id` | Modify a state path |
| `PUT` | `/api/state/:id/bulk` | Bulk update state |
| `POST` | `/api/state/:id/pause` | Pause execution |
| `POST` | `/api/state/:id/resume` | Resume execution |
| `POST` | `/api/state/:id/step` | Step N then pause |
| `POST` | `/api/state/:id/breakpoints` | Set breakpoints |

### Agents

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/agents` | List registered agents |
| `POST` | `/api/agents` | Register an agent |
| `GET` | `/api/agents/:id` | Get agent details |
| `GET` | `/api/agents/:id/metrics` | Agent performance metrics |

### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/auth/register` | Create account |
| `POST` | `/api/auth/login` | Login |
| `POST` | `/api/auth/refresh` | Refresh token |
| `GET` | `/api/auth/me` | Current user info |
| `GET` | `/api/auth/api-key` | Get/create API key |

### WebSocket

```javascript
const ws = new WebSocket('ws://localhost:8000/ws');
ws.send(JSON.stringify({ action: 'subscribe', trace_id: 'xxx' }));
```

---

## Architecture

```
┌──────────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Your Agent Code    │────▶│  Lighthouse SDK  │────▶│  FastAPI Backend │
│  (Any framework)     │     │  (pip package)   │     │   (Port 8000)   │
└──────────────────────┘     └──────────────────┘     └────────┬────────┘
                                                               │
                             ┌──────────────────┐     ┌────────┴────────┐
                             │  React Dashboard │◀───▶│  Redis + Postgres│
                             │   (Port 5173)    │     │                 │
                             └──────────────────┘     └─────────────────┘
```

## Project Structure

```
Agent-Lighthouse/
├── backend/                    # FastAPI Backend
│   ├── main.py                # Entry point + health endpoints
│   ├── routers/               # API routes
│   │   ├── traces.py         # Trace + span CRUD, batch, export
│   │   ├── agents.py         # Agent registration + metrics
│   │   ├── state.py          # State inspection, execution control
│   │   ├── auth.py           # Register, login, refresh, JWT
│   │   ├── api_keys.py       # API key issuance
│   │   └── websocket.py      # Real-time updates
│   ├── models/                # Pydantic data models
│   ├── services/              # Business logic (Redis, auth)
│   └── security.py           # Auth middleware + rate limiting
│
├── frontend/                   # React Dashboard
│   └── src/
│       ├── components/
│       │   ├── TraceGraph/   # React Flow visualization
│       │   ├── TokenMonitor/ # Cost distribution charts
│       │   ├── StateInspector/ # State viewer/editor
│       │   ├── Timeline/     # Span timeline
│       │   ├── LandingPage.jsx
│       │   └── DocsPage.jsx  # Full documentation page
│       └── App.jsx            # Routing + auth
│
├── sdk/                        # Python SDK (PyPI: agent-lighthouse)
│   └── agent_lighthouse/
│       ├── __init__.py       # Public API exports
│       ├── tracer.py         # LighthouseTracer + decorators
│       ├── client.py         # HTTP client
│       ├── cli.py            # CLI (init, status, traces)
│       ├── auto.py           # Auto-instrumentation
│       └── adapters/         # Framework adapters
│           └── langchain.py  # LangChain/LangGraph callback handler
│
├── docker-compose.yml
├── CHANGELOG.md
└── README.md
```

---

## Security Checklist

- Set a strong `JWT_SECRET`
- Use explicit `MACHINE_API_KEYS` scopes for SDK ingestion
- Configure `ALLOWED_ORIGINS` to exact trusted origins
- Keep Redis and Postgres private
- Run behind HTTPS/WSS
- Rotate API keys periodically

---

## CI/CD

| Workflow | Trigger | What It Does |
|----------|---------|-------------|
| CI | PRs, push to `main` | Lint, test, security scan for frontend, backend, and SDK |
| CD | Push to `main` | Build + publish Docker images to GHCR |
| Publish SDK | Tag `v*` | Build + publish to PyPI |
| CodeQL | Schedule | GitHub code scanning for Python and JavaScript |
| Release | Tag `v*` | Auto-create GitHub release |

---

## Documentation

- [Architecture](docs/ARCHITECTURE.md) — system design and data flow
- [Troubleshooting](docs/TROUBLESHOOTING.md) — common issues and fixes
- [Operations Runbook](docs/OPERATIONS.md) — production operations
- [Contributing](CONTRIBUTING.md) — contribution workflow
- [Security](SECURITY.md) — vulnerability reporting
- [Changelog](CHANGELOG.md) — release history

---

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

See [CONTRIBUTING.md](CONTRIBUTING.md) for details.

---

## License

MIT License — see [LICENSE](LICENSE).

<p align="center">
  <strong>Built for the AI Agent Community</strong>
</p>

<p align="center">
  <a href="https://github.com/noogler-aditya/Agent-Lighthouse">⭐ Star this repo</a> •
  <a href="https://github.com/noogler-aditya/Agent-Lighthouse/issues">🐛 Report Bug</a> •
  <a href="https://github.com/noogler-aditya/Agent-Lighthouse/issues">💡 Request Feature</a>
</p>
