<p align="center">
  <img src="https://img.shields.io/badge/🔦-Agent%20Lighthouse-6366f1?style=for-the-badge" alt="Agent Lighthouse"/>
</p>

<h1 align="center">Agent Lighthouse</h1>

<p align="center">
  <strong>Multi-Agent Observability Dashboard</strong><br>
  A framework-agnostic visual debugger for agentic AI systems
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.9+-3776ab?logo=python&logoColor=white" alt="Python"/>
  <img src="https://img.shields.io/badge/react-18+-61dafb?logo=react&logoColor=black" alt="React"/>
  <img src="https://img.shields.io/badge/fastapi-0.109+-009688?logo=fastapi&logoColor=white" alt="FastAPI"/>
  <img src="https://img.shields.io/badge/redis-7+-dc382d?logo=redis&logoColor=white" alt="Redis"/>
  <img src="https://img.shields.io/badge/license-MIT-green" alt="License"/>
</p>

---

## 🎯 The Problem

When running multi-agent systems (CrewAI, LangGraph, AutoGen, etc.), debugging is a nightmare:

| Challenge | Impact |
|-----------|--------|
| **Black Box Execution** | Can't see what's happening inside agent loops |
| **Opaque Failures** | If it fails at step 10, which agent caused it? |
| **Hidden Costs** | Token usage spirals without visibility |
| **No State Inspection** | Can't pause and inspect agent memory |
| **Log Analysis Hell** | Debugging requires parsing walls of text |

## ✨ The Solution

Agent Lighthouse provides a **visual debugging layer** for any multi-agent system:

```
Your Agent Code → Lighthouse SDK → Visual Dashboard
```

### Key Features

| Feature | Description |
|---------|-------------|
| 🔍 **Trace Visualization** | Interactive flowchart showing agent execution |
| 💰 **Token Burn-Rate Monitor** | Real-time tracking of costs per agent/tool |
| 🔧 **State Inspection** | Pause, inspect memory as JSON, edit, and resume |
| ⚡ **Real-Time Updates** | WebSocket-powered live updates |
| 🔌 **Framework Agnostic** | Works with CrewAI, LangGraph, AutoGen, or custom agents |

---

## 🖥️ Dashboard Preview

Run the stack locally to view the dashboard at `http://localhost:5173`.

**Dashboard Components:**
- **Sidebar**: Searchable list of all traces with quick stats
- **Trace Graph**: React Flow visualization with Agent, Tool, and LLM nodes
- **Token Monitor**: Pie/bar charts showing cost distribution
- **State Inspector**: Monaco editor for viewing/editing agent state

---

## 🚀 Quick Start

### Prerequisites

- Python 3.9+
- Node.js 18+
- Redis (or Docker)

### Option 1: Docker Compose (Recommended)

```bash
git clone https://github.com/noogler-aditya/Agent-Lighthouse.git
cd Agent-Lighthouse

docker-compose up -d
```

Default local API key in `docker-compose.yml`: `local-dev-key`.

### Option 2: Manual Setup

```bash
# 1. Start Redis
docker run -d -p 6379:6379 redis:7-alpine

# 2. Start PostgreSQL
docker run -d -p 5432:5432 \
  -e POSTGRES_USER=lighthouse \
  -e POSTGRES_PASSWORD=lighthouse \
  -e POSTGRES_DB=lighthouse \
  postgres:16-alpine

# 3. Start Backend
cd backend
pip install -r requirements.txt
export MACHINE_API_KEYS=local-dev-key:trace:write|trace:read
export JWT_SECRET=dev-secret
export ALLOWED_ORIGINS=http://localhost:5173
export DATABASE_URL=postgresql://lighthouse:lighthouse@localhost:5432/lighthouse
python3 -m uvicorn main:app --reload --port 8000

# 4. Start Frontend (new terminal)
cd frontend
npm install
npm run dev
```

### Access Points

| Service | URL |
|---------|-----|
| **Dashboard** | http://localhost:5173 |
| **API Docs** | http://localhost:8000/docs |
| **WebSocket** | ws://localhost:8000/ws |

UI requests use `Authorization: Bearer <token>` after `/api/auth/register` or `/api/auth/login`.
Machine-to-machine SDK ingestion uses scoped `X-API-Key`.

### Verification Flow (Recommended)

Run these checks in order after startup:

```bash
# 1) Backend health
curl http://localhost:8000/health/live
curl http://localhost:8000/health/ready

# 2) User auth and trace list API
# First-time setup (register). If you get a 409, use /api/auth/login instead.
TOKEN=$(curl -s http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"demo","password":"demo"}' | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/traces

# Optional: use the API key returned by /api/auth/register for SDK ingestion
# curl -H "X-API-Key: <api_key>" http://localhost:8000/api/traces

# 3) Deterministic smoke trace ingestion
cd sdk
LIGHTHOUSE_API_KEY=local-dev-key python3 examples/smoke_trace_check.py
```

Expected results:
- `/health` returns JSON with `status` and Redis connectivity
- `/api/traces` returns a `traces` array (may be empty before smoke test)
- `smoke_trace_check.py` exits with `[PASS]` and prints a trace ID
- Dashboard sidebar should show at least one trace after refresh

### If Dashboard Is Empty

Use this checklist:

1. Confirm frontend auth and backend auth settings:
   - frontend signs in via `/api/auth/register` or `/api/auth/login`
   - backend has valid `JWT_SECRET`, `DATABASE_URL`, `ALLOWED_ORIGINS`
2. Confirm frontend backend URL:
   - `VITE_API_URL` should point to `http://localhost:8000`
3. Confirm backend CORS origin:
   - `ALLOWED_ORIGINS` includes `http://localhost:5173`
4. Run the smoke script and verify it passes:
   - `python3 sdk/examples/smoke_trace_check.py`
5. Check sidebar error panel text:
   - `401/403` means auth/session/token issue
   - `Backend unreachable` means URL/backend availability issue

## 🔐 Production Security Checklist

- Set a strong `JWT_SECRET`
- Use explicit `MACHINE_API_KEYS` scopes for SDK ingestion only
- Configure `ALLOWED_ORIGINS` to exact trusted origins
- Keep Redis private (no public host port mapping)
- Run behind HTTPS/WSS
- Rotate machine keys and monitor auth logs

## 🔁 CI/CD

This repo now includes GitHub Actions workflows for open-source style quality gates and delivery:

- **CI** (`.github/workflows/ci.yml`)
  - Runs on pull requests and pushes to `main`
  - Frontend: install, lint, build, tests, dependency audit
  - Backend: static/security checks + pytest suite + app import check
  - SDK: multi-Python static/security checks + pytest suite (3.9-3.12)
  - Integration: Redis + backend + SDK smoke trace ingestion test
  - Failed pull requests are labeled/commented for follow-up (not auto-closed)

- **CD** (`.github/workflows/cd.yml`)
  - Runs on merge/push to `main`
  - Builds and publishes Docker images to GHCR:
    - `ghcr.io/<noogler-aditya>/<repo>/backend:latest`
    - `ghcr.io/<noogler-aditya>/<repo>/frontend:latest`
    - plus immutable `sha-<commit>` tags

- **CodeQL** (`.github/workflows/codeql.yml`)
  - GitHub code scanning for Python and JavaScript

- **Release** (`.github/workflows/release.yml`)
  - Creates GitHub releases automatically on `v*` tags

### Recommended Repository Settings

1. Protect `main` branch and require passing checks from CI before merge.
2. Keep GitHub Packages enabled for GHCR publishing.
3. Prefer squash merge for cleaner release history.
4. Optionally require signed commits for maintainers.

---

## 📚 Project Documentation

Core project and community docs:

- [README](README.md) - setup, architecture, and API overview
- [CONTRIBUTING](CONTRIBUTING.md) - contribution workflow and quality gates
- [SECURITY](SECURITY.md) - vulnerability reporting and handling
- [SUPPORT](SUPPORT.md) - support channels and triage expectations
- [CODE_OF_CONDUCT](CODE_OF_CONDUCT.md) - community behavior standards
- [GOVERNANCE](GOVERNANCE.md) - decision-making and maintainer model
- [MAINTAINERS](MAINTAINERS.md) - maintainer roles and ownership areas
- [RELEASE](RELEASE.md) - release process and versioning policy
- [CHANGELOG](CHANGELOG.md) - notable changes
- [Architecture](docs/ARCHITECTURE.md) - system design details
- [Operations Runbook](docs/OPERATIONS.md) - production operations and incident flow
- [Troubleshooting](docs/TROUBLESHOOTING.md) - empty dashboard and common failure recovery

---

## 📦 SDK Installation

```bash
pip install agent-lighthouse
```

Or install from source:
```bash
cd sdk
pip install -e .
```

The SDK is published on PyPI. Install it with the `pip install` command above.

---

## 🛠️ Usage

### Basic Tracing

```python
from agent_lighthouse import LighthouseTracer

tracer = LighthouseTracer()

with tracer.trace("My Agent Workflow"):
    with tracer.span("Research Agent", kind="agent"):
        result = research(query)
    
    with tracer.span("Writer Agent", kind="agent"):
        content = write(result)
```

### Decorator-Based (Recommended)

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

# Run with tracing
tracer = get_tracer()
with tracer.trace("Research Workflow"):
    research_agent("AI Trends 2024")
```

### Zero-Touch Auto-Instrumentation (Magic Import)

No decorators required — just import once at the top of your script:

```python
import agent_lighthouse.auto
```

This will automatically instrument:
- OpenAI and Anthropic client calls
- `requests.post` to known LLM endpoints
- Frameworks like LangChain/LangGraph, CrewAI, and AutoGen (when installed)

Content capture is **off by default**. Enable only if you explicitly want payloads:

```bash
export LIGHTHOUSE_CAPTURE_CONTENT=true
```

### State Inspection

```python
@trace_agent("Writer Agent")
def writer_agent(research):
    tracer = get_tracer()
    
    # Expose state for dashboard inspection
    tracer.update_state(
        memory={"research": research, "draft_count": 0},
        context={"agent": "writer"},
        variables={"temperature": 0.7}
    )
    
    draft = generate_draft(research)
    return draft
```

Pause from the dashboard to:
1. View current state as JSON
2. Edit memory/context/variables
3. Resume execution with modified state

---

## 🏗️ Architecture

```
┌─────────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Your Agent Code   │────▶│  Lighthouse SDK  │────▶│  FastAPI Backend│
│  (CrewAI/LangGraph) │     │ (trace_agent,etc)│     │   (Port 8000)   │
└─────────────────────┘     └──────────────────┘     └────────┬────────┘
                                                              │
                                                              ▼
                            ┌──────────────────┐     ┌─────────────────┐
                            │  React Dashboard │◀────│      Redis      │
                            │   (Port 5173)    │     │  (Port 6379)    │
                            └──────────────────┘     └─────────────────┘
```

---

## 📁 Project Structure

```
Agent-Lighthouse/
├── backend/                    # FastAPI Backend
│   ├── main.py                # Application entry point
│   ├── models/                # Pydantic data models
│   │   ├── trace.py          # Trace & Span models
│   │   ├── agent.py          # Agent model
│   │   ├── state.py          # State & Control models
│   │   └── metrics.py        # Token metrics models
│   ├── routers/               # API endpoints
│   │   ├── traces.py         # Trace CRUD operations
│   │   ├── agents.py         # Agent registration
│   │   ├── state.py          # State inspection/control
│   │   └── websocket.py      # Real-time updates
│   └── services/              # Business logic
│       ├── redis_service.py  # Data persistence
│       └── connection_manager.py  # WebSocket management
│
├── frontend/                   # React Dashboard
│   └── src/
│       ├── components/
│       │   ├── TraceGraph/   # React Flow visualization
│       │   ├── TokenMonitor/ # Recharts cost display
│       │   ├── StateInspector/ # Monaco JSON editor
│       │   └── Sidebar/      # Trace list
│       └── hooks/             # Custom React hooks
│           ├── useWebSocket.js
│           ├── useTraces.js
│           └── useAgentState.js
│
├── sdk/                        # Python SDK
│   └── agent_lighthouse/
│       ├── tracer.py         # LighthouseTracer class
│       ├── client.py         # HTTP client
│       └── examples/         # Usage examples
│
├── docker-compose.yml          # Full stack deployment
└── README.md
```

---

## 🔌 API Reference

### Traces

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/traces` | GET | List all traces |
| `/api/traces` | POST | Create new trace |
| `/api/traces/{id}` | GET | Get trace by ID |
| `/api/traces/{id}/tree` | GET | Get trace as tree |
| `/api/traces/{id}/spans` | POST | Add span to trace |

### State Control

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/state/{id}` | GET | Get agent state |
| `/api/state/{id}` | PUT | Update state |
| `/api/state/{id}/pause` | POST | Pause execution |
| `/api/state/{id}/resume` | POST | Resume execution |
| `/api/state/{id}/step` | POST | Step execution |

### WebSocket

Connect to `/ws` for real-time updates:
```javascript
const ws = new WebSocket('ws://localhost:8000/ws');
ws.send(JSON.stringify({ action: 'subscribe', trace_id: 'xxx' }));
```

---

## 🧪 Run Demo

```bash
cd sdk
pip install -e .
python examples/demo_multi_agent.py
```

This creates a sample workflow with Research, Writer, and Editor agents visible in the dashboard.

---

## 🛣️ Roadmap

- [ ] **CrewAI Integration** - Auto-instrumentation for CrewAI
- [ ] **LangGraph Integration** - Auto-instrumentation for LangGraph
- [ ] **Breakpoints** - Set breakpoints on specific agent/tool calls
- [ ] **Time-Travel Debugging** - Replay execution from snapshots
- [ ] **Cost Alerts** - Notifications when burn rate exceeds threshold
- [ ] **Export/Import** - Save and share trace data

---

## 🤝 Contributing

Contributions are welcome! Please read our [Contributing Guidelines](CONTRIBUTING.md) first.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

<p align="center">
  <strong>Built with ❤️ for the AI Agent Community</strong>
</p>

<p align="center">
  <a href="https://github.com/noogler-aditya/Agent-Lighthouse">⭐ Star this repo</a> •
  <a href="https://github.com/noogler-aditya/Agent-Lighthouse/issues">🐛 Report Bug</a> •
  <a href="https://github.com/noogler-aditya/Agent-Lighthouse/issues">💡 Request Feature</a>
</p>
