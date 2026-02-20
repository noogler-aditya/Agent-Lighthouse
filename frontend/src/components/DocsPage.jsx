import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Bot } from './icons/AppIcons';
import './DocsPage.css';

const REPO_URL = 'https://github.com/noogler-aditya/Agent-Lighthouse';
const PYPI_URL = 'https://pypi.org/project/agent-lighthouse/';

const sections = [
  { id: 'quickstart', title: 'Quickstart' },
  { id: 'installation', title: 'Installation' },
  { id: 'sdk-usage', title: 'SDK Usage' },
  { id: 'auto-instrumentation', title: 'Auto-Instrumentation' },
  { id: 'langchain-adapter', title: 'LangChain / LangGraph' },
  { id: 'authentication', title: 'Authentication' },
  { id: 'api-reference', title: 'API Reference' },
  { id: 'environment', title: 'Environment Variables' },
  { id: 'deployment', title: 'Deployment' },
  { id: 'troubleshooting', title: 'Troubleshooting' },
];

function CodeBlock({ code, language = '' }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="docs-code-wrap">
      {language && <span className="docs-code-lang">{language}</span>}
      <button type="button" className="docs-code-copy" onClick={handleCopy} aria-label="Copy code">
        {copied ? '✓ Copied' : 'Copy'}
      </button>
      <pre className="docs-code"><code>{code}</code></pre>
    </div>
  );
}

function EndpointRow({ method, path, description }) {
  return (
    <div className="docs-endpoint-row">
      <span className={`docs-method-badge ${method.toLowerCase()}`}>{method}</span>
      <code className="docs-endpoint-path">{path}</code>
      <span className="docs-endpoint-desc">{description}</span>
    </div>
  );
}

export function DocsPage({ isAuthenticated, onLoginClick }) {
  const navigate = useNavigate();

  return (
    <div className="docs-page">
      <header className="docs-header">
        <div className="docs-header-inner">
          <div className="docs-brand">
            <Link to="/" className="docs-brand-link" aria-label="Go to home">
              <span className="docs-brand-logo" aria-hidden="true">
                <Bot className="ui-icon" />
              </span>
              <span>Agent Lighthouse</span>
            </Link>
            <span className="docs-breadcrumb">/ Docs</span>
          </div>

          <div className="docs-header-actions">
            <a href={PYPI_URL} target="_blank" rel="noreferrer" className="docs-text-link">PyPI</a>
            <a href={REPO_URL} target="_blank" rel="noreferrer" className="docs-text-link">GitHub</a>
            {isAuthenticated ? (
              <button type="button" className="btn btn-primary btn-sm" onClick={() => navigate('/dashboard')}>
                Open Dashboard
              </button>
            ) : (
              <button type="button" className="btn btn-secondary btn-sm" onClick={onLoginClick}>
                Get Started
              </button>
            )}
          </div>
        </div>
      </header>

      <main className="docs-main">
        <aside className="docs-sidebar" aria-label="Documentation navigation">
          <div className="docs-sidebar-card">
            <p className="docs-sidebar-title">On this page</p>
            <nav>
              {sections.map((section) => (
                <a key={section.id} href={`#${section.id}`} className="docs-anchor-link">
                  {section.title}
                </a>
              ))}
            </nav>
          </div>
        </aside>

        <section className="docs-content">
          {/* ── Intro ── */}
          <article className="docs-section docs-intro">
            <p className="docs-kicker">Documentation</p>
            <h1>Build and operate agent tracing with confidence</h1>
            <p>
              Agent Lighthouse gives engineering teams a practical debugging surface for multi-agent systems:
              trace flow, token metrics, state inspection, and execution control — all in one place.
            </p>
          </article>

          {/* ── Quickstart ── */}
          <article id="quickstart" className="docs-section">
            <h2>Quickstart</h2>
            <p>Get traces from your agent system to the dashboard in under 5 minutes.</p>
            <ol>
              <li>Install the SDK: <code>pip install agent-lighthouse</code></li>
              <li>Sign in to the dashboard and copy your API key.</li>
              <li>Set your API key as an environment variable: <code>export LIGHTHOUSE_API_KEY="lh_..."</code></li>
              <li>Add decorators to your agent functions and run your code.</li>
              <li>Open the dashboard — traces appear in real time.</li>
            </ol>
            <CodeBlock language="bash" code={`pip install agent-lighthouse
export LIGHTHOUSE_API_KEY="lh_your_key_here"`} />
          </article>

          {/* ── Installation ── */}
          <article id="installation" className="docs-section">
            <h2>Installation</h2>
            <p>The SDK is published on PyPI and supports Python 3.9+.</p>
            <CodeBlock language="bash" code={`pip install agent-lighthouse`} />
            <p style={{ marginTop: '12px' }}>
              The SDK defaults to the production backend (<code>https://agent-lighthouse.onrender.com</code>).
              For local development, override with:
            </p>
            <CodeBlock language="bash" code={`export LIGHTHOUSE_BASE_URL="http://localhost:8000"`} />
          </article>

          {/* ── SDK Usage ── */}
          <article id="sdk-usage" className="docs-section">
            <h2>SDK Usage</h2>
            <p>
              Use decorators to trace agents, tools, and LLM calls. The SDK automatically captures inputs,
              outputs, timing, and errors — and sends them to the dashboard.
            </p>
            <CodeBlock language="python" code={`from agent_lighthouse import get_tracer, trace_agent, trace_tool, trace_llm

tracer = get_tracer()

@trace_agent("Planner Agent")
def planner(goal: str):
    plan = llm.invoke(goal)
    return plan

@trace_tool("Web Search")
def search(query: str):
    return duckduckgo.search(query)

@trace_llm(model="gpt-4o")
def call_llm(prompt: str):
    return openai.chat(prompt)

# Wrap your workflow in a trace context
with tracer.trace("My Workflow", description="End-to-end pipeline"):
    result = planner("Explain observability")
    data = search(result)
    final = call_llm(data)`} />

            <h3>State Inspection</h3>
            <p>Push live state to the dashboard's State tab for real-time debugging:</p>
            <CodeBlock language="python" code={`tracer.update_state(
    memory={"goal": "Explain observability", "plan": plan},
    context={"current_step": "planning_complete"},
    variables={"plan_length": len(plan)},
)`} />
          </article>

          {/* ── Auto-Instrumentation ── */}
          <article id="auto-instrumentation" className="docs-section">
            <h2>Auto-Instrumentation</h2>
            <p>
              Import <code>agent_lighthouse.auto</code> at the top of your app to automatically
              capture OpenAI, Anthropic, and HTTP calls — zero code changes required.
            </p>
            <CodeBlock language="python" code={`import agent_lighthouse.auto  # Must be first import

# All OpenAI / Anthropic / httpx calls are now traced automatically
from openai import OpenAI
client = OpenAI()
response = client.chat.completions.create(model="gpt-4o", messages=[...])`} />
            <h3>Environment Variables</h3>
            <ul>
              <li><code>LIGHTHOUSE_AUTO_INSTRUMENT=1</code> — enable auto-instrumentation (default: on)</li>
              <li><code>LIGHTHOUSE_CAPTURE_CONTENT=true</code> — capture request/response payloads</li>
              <li><code>LIGHTHOUSE_LLM_HOSTS</code> — allowlist extra LLM API hosts</li>
            </ul>
          </article>

          {/* ── LangChain Adapter ── */}
          <article id="langchain-adapter" className="docs-section">
            <h2>LangChain / LangGraph</h2>
            <p>
              For LangChain and LangGraph projects, pass the callback handler to capture
              LLM calls, chain executions, tool invocations, and agent steps.
            </p>
            <CodeBlock language="python" code={`from agent_lighthouse.adapters.langchain import LighthouseLangChainCallbackHandler

handler = LighthouseLangChainCallbackHandler()

# Pass to any LangChain chain, agent, or graph invocation
chain.invoke({"goal": "..."}, config={"callbacks": [handler]})

# Or with LangGraph
graph.invoke(initial_state, config={"callbacks": [handler]})`} />
          </article>

          {/* ── Authentication ── */}
          <article id="authentication" className="docs-section">
            <h2>Authentication</h2>
            <p>
              Two authentication methods are supported: <strong>user (Bearer token)</strong> for the
              dashboard UI, and <strong>API key (X-API-Key)</strong> for SDK / machine access.
            </p>
            <h3>User Authentication</h3>
            <p>Register and log in via the dashboard. The frontend manages JWT tokens automatically.</p>
            <CodeBlock language="bash" code={`# Register
curl -X POST https://agent-lighthouse.onrender.com/api/auth/register \\
  -H "Content-Type: application/json" \\
  -d '{"username": "myuser", "password": "mypass"}'

# Login
curl -X POST https://agent-lighthouse.onrender.com/api/auth/login \\
  -H "Content-Type: application/json" \\
  -d '{"username": "myuser", "password": "mypass"}'`} />

            <h3>API Key Authentication</h3>
            <p>
              After signing in, click <strong>API Key</strong> in the dashboard header to get your key.
              Use it with the SDK or pass it as the <code>X-API-Key</code> header.
            </p>
            <CodeBlock language="bash" code={`export LIGHTHOUSE_API_KEY="lh_your_key_here"

# Or pass directly in requests
curl -H "X-API-Key: lh_your_key_here" \\
  https://agent-lighthouse.onrender.com/api/traces`} />
          </article>

          {/* ── API Reference ── */}
          <article id="api-reference" className="docs-section">
            <h2>API Reference</h2>
            <p>
              Base URL: <code>https://agent-lighthouse.onrender.com</code>. All endpoints require
              authentication via <code>Authorization: Bearer &lt;token&gt;</code> or <code>X-API-Key</code>.
            </p>

            <h3>Traces</h3>
            <div className="docs-endpoint-list">
              <EndpointRow method="GET" path="/api/traces" description="List traces with pagination, search, and filtering" />
              <EndpointRow method="POST" path="/api/traces" description="Create a new trace" />
              <EndpointRow method="GET" path="/api/traces/:id" description="Get trace details with all spans" />
              <EndpointRow method="DELETE" path="/api/traces/:id" description="Delete a trace" />
              <EndpointRow method="POST" path="/api/traces/:id/complete" description="Mark trace as complete" />
              <EndpointRow method="GET" path="/api/traces/:id/tree" description="Get trace as a hierarchical tree" />
              <EndpointRow method="GET" path="/api/traces/:id/export" description="Download trace as JSON" />
              <EndpointRow method="GET" path="/api/traces/:id/metrics" description="Get token/cost metrics summary" />
            </div>

            <h3>Spans</h3>
            <div className="docs-endpoint-list">
              <EndpointRow method="POST" path="/api/traces/:id/spans" description="Create a span within a trace" />
              <EndpointRow method="POST" path="/api/traces/:id/spans/batch" description="Batch create up to 100 spans" />
              <EndpointRow method="PATCH" path="/api/traces/:id/spans/:span_id" description="Update span status, output, tokens, errors" />
            </div>

            <h3>State Inspection</h3>
            <div className="docs-endpoint-list">
              <EndpointRow method="GET" path="/api/state/:id" description="Get current state for a trace" />
              <EndpointRow method="POST" path="/api/state/:id" description="Initialize state (memory, context, variables)" />
              <EndpointRow method="PATCH" path="/api/state/:id" description="Modify a specific state path" />
              <EndpointRow method="PUT" path="/api/state/:id/bulk" description="Bulk update state containers" />
            </div>

            <h3>Execution Control</h3>
            <div className="docs-endpoint-list">
              <EndpointRow method="POST" path="/api/state/:id/pause" description="Pause execution at current point" />
              <EndpointRow method="POST" path="/api/state/:id/resume" description="Resume paused execution" />
              <EndpointRow method="POST" path="/api/state/:id/step" description="Execute N steps then pause" />
              <EndpointRow method="GET" path="/api/state/:id/control" description="Get current execution control status" />
              <EndpointRow method="POST" path="/api/state/:id/breakpoints" description="Set breakpoints for debugging" />
              <EndpointRow method="GET" path="/api/state/:id/snapshots" description="List all state snapshots" />
              <EndpointRow method="POST" path="/api/state/:id/snapshots" description="Take a snapshot of current state" />
            </div>

            <h3>Agents</h3>
            <div className="docs-endpoint-list">
              <EndpointRow method="GET" path="/api/agents" description="List all registered agents" />
              <EndpointRow method="POST" path="/api/agents" description="Register a new agent" />
              <EndpointRow method="GET" path="/api/agents/:id" description="Get agent details" />
              <EndpointRow method="GET" path="/api/agents/:id/metrics" description="Get agent performance metrics" />
            </div>

            <h3>Authentication</h3>
            <div className="docs-endpoint-list">
              <EndpointRow method="POST" path="/api/auth/register" description="Create a new user account" />
              <EndpointRow method="POST" path="/api/auth/login" description="Authenticate with username & password" />
              <EndpointRow method="POST" path="/api/auth/refresh" description="Refresh an expired access token" />
              <EndpointRow method="GET" path="/api/auth/me" description="Get current user info" />
              <EndpointRow method="GET" path="/api/auth/api-key" description="Get or create your API key" />
            </div>
          </article>

          {/* ── Environment Variables ── */}
          <article id="environment" className="docs-section">
            <h2>Environment Variables</h2>
            <div className="docs-table-wrap">
              <table className="docs-table">
                <thead>
                  <tr>
                    <th>Variable</th>
                    <th>Description</th>
                    <th>Default</th>
                  </tr>
                </thead>
                <tbody>
                  <tr><td><code>LIGHTHOUSE_API_KEY</code></td><td>Your API key</td><td><em>None</em></td></tr>
                  <tr><td><code>LIGHTHOUSE_BASE_URL</code></td><td>Backend API URL</td><td><code>https://agent-lighthouse.onrender.com</code></td></tr>
                  <tr><td><code>LIGHTHOUSE_AUTO_INSTRUMENT</code></td><td>Enable auto-instrumentation</td><td><code>1</code></td></tr>
                  <tr><td><code>LIGHTHOUSE_CAPTURE_CONTENT</code></td><td>Capture request/response payloads</td><td><code>false</code></td></tr>
                  <tr><td><code>LIGHTHOUSE_LLM_HOSTS</code></td><td>Extra LLM hosts to instrument</td><td><em>None</em></td></tr>
                </tbody>
              </table>
            </div>
          </article>

          {/* ── Deployment ── */}
          <article id="deployment" className="docs-section">
            <h2>Deployment</h2>
            <p>
              A typical production setup uses the frontend on <strong>Vercel</strong> and
              backend on <strong>Render</strong>.
            </p>
            <h3>Vercel (Frontend)</h3>
            <CodeBlock language="bash" code={`VITE_API_URL=https://agent-lighthouse.onrender.com/api
VITE_SUPABASE_URL=https://<project-ref>.supabase.co
VITE_SUPABASE_ANON_KEY=<supabase-anon-key>`} />
            <h3>Render (Backend)</h3>
            <ul>
              <li>Set Redis URL, PostgreSQL URL, and Supabase JWT settings</li>
              <li>Configure CORS to include your exact Vercel domain</li>
              <li>Set machine API keys if needed for server-to-server access</li>
              <li>Use HTTPS endpoints only</li>
            </ul>
            <h3>Local Development</h3>
            <CodeBlock language="bash" code={`# Frontend
cd frontend && npm install && npm run dev

# Backend
cd backend && pip install -r requirements.txt
uvicorn main:app --reload

# Docker (all services)
docker compose up --build`} />
          </article>

          {/* ── Troubleshooting ── */}
          <article id="troubleshooting" className="docs-section">
            <h2>Troubleshooting</h2>
            <ul>
              <li><strong>Dashboard is empty:</strong> Verify <code>LIGHTHOUSE_API_KEY</code> is set and pointing to the correct backend URL. Decorators now auto-create traces — update to SDK v0.3.1+.</li>
              <li><strong>403 Forbidden on SDK calls:</strong> Ensure your API key starts with <code>lh_</code> and matches a key in the dashboard.</li>
              <li><strong>Tokens show as 0:</strong> For local models (Ollama, llama.cpp), pass the LangChain callback handler to capture token usage from the model response.</li>
              <li><strong>Auth fails on dashboard:</strong> Confirm the backend URL in <code>VITE_API_URL</code> is correct and CORS allows your frontend domain.</li>
              <li><strong>Auto-instrumentation not working:</strong> Ensure <code>import agent_lighthouse.auto</code> is the very first import in your application.</li>
            </ul>
          </article>

          {/* ── CTA ── */}
          <section className="docs-cta">
            <div>
              <h2>Ready to debug traces in real time?</h2>
              <p>Use the dashboard to inspect agent flow, monitor costs, and resolve failures faster.</p>
            </div>
            {isAuthenticated ? (
              <button type="button" className="btn btn-primary" onClick={() => navigate('/dashboard')}>
                Open Dashboard
              </button>
            ) : (
              <button type="button" className="btn btn-primary" onClick={onLoginClick}>
                Sign In
              </button>
            )}
          </section>
        </section>
      </main>
    </div>
  );
}
