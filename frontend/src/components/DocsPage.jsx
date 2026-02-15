import { Link, useNavigate } from 'react-router-dom';
import { Bot } from './icons/AppIcons';
import './DocsPage.css';

const REPO_URL = 'https://github.com/noogler-aditya/Agent-Lighthouse';

const sections = [
  { id: 'quickstart', title: 'Quickstart' },
  { id: 'authentication', title: 'Authentication' },
  { id: 'api-endpoints', title: 'API Endpoints' },
  { id: 'sdk-usage', title: 'SDK Usage' },
  { id: 'deployment', title: 'Deployment (Vercel + Render)' },
  { id: 'troubleshooting', title: 'Troubleshooting' },
];

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
          <article className="docs-section docs-intro">
            <p className="docs-kicker">Documentation</p>
            <h1>Build and operate agent tracing with confidence</h1>
            <p>
              Agent Lighthouse gives engineering teams a practical debugging surface for multi-agent systems:
              trace flow, token metrics, and runtime state in one place.
            </p>
          </article>

          <article id="quickstart" className="docs-section">
            <h2>Quickstart</h2>
            <p>Follow these steps to run the full stack locally and validate the core tracing workflow.</p>
            <ol>
              <li>Set frontend and backend environment variables.</li>
              <li>Start Redis, backend, and frontend with Docker Compose or local dev commands.</li>
              <li>Register a user, sign in, and open the dashboard.</li>
              <li>Create a trace and verify spans appear in graph, timeline, and token monitor.</li>
            </ol>
            <pre className="docs-code"><code>{`# frontend
cd frontend
npm install
npm run dev

# backend
cd backend
pip install -r requirements.txt
uvicorn main:app --reload`}</code></pre>
          </article>

          <article id="authentication" className="docs-section">
            <h2>Authentication</h2>
            <p>
              The application uses Supabase for user authentication. Frontend session state is derived from the
              Supabase auth client and attached to API requests as a bearer token.
            </p>
            <pre className="docs-code"><code>{`VITE_SUPABASE_URL=https://<project-ref>.supabase.co
VITE_SUPABASE_ANON_KEY=<supabase-anon-key>
VITE_API_URL=https://<backend-url>/api`}</code></pre>
            <p>
              For production, configure redirect URLs and allowed origins in Supabase and match them with your
              deployed frontend domain.
            </p>
          </article>

          <article id="api-endpoints" className="docs-section">
            <h2>API Endpoints</h2>
            <p>Core endpoints used by the UI and SDK:</p>
            <ul>
              <li><code>GET /api/health</code> - service health status.</li>
              <li><code>POST /api/traces</code> - create a trace.</li>
              <li><code>GET /api/traces</code> - list traces for dashboard.</li>
              <li><code>GET /api/traces/:trace_id</code> - trace details.</li>
              <li><code>POST /api/auth/api-key</code> - issue user-scoped API key.</li>
            </ul>
            <pre className="docs-code"><code>{`curl -X POST "$API_URL/traces" \\
  -H "Authorization: Bearer <access-token>" \\
  -H "Content-Type: application/json" \\
  -d '{"name":"checkout-agent-trace"}'`}</code></pre>
          </article>

          <article id="sdk-usage" className="docs-section">
            <h2>SDK Usage</h2>
            <p>
              Use the SDK for trace ingestion from worker processes and service runtimes where browser auth is not
              available.
            </p>
            <pre className="docs-code"><code>{`from sdk.client import AgentLighthouseClient

client = AgentLighthouseClient(
    base_url="https://<backend-url>/api",
    api_key="<machine-or-user-api-key>",
)

trace = client.create_trace(name="support-agent")
client.create_span(trace_id=trace["trace_id"], name="retrieve-context", kind="tool")`}</code></pre>
          </article>

          <article id="deployment" className="docs-section">
            <h2>Deployment (Vercel + Render)</h2>
            <p>
              A common production setup is frontend on Vercel and backend on Render. Keep environment values aligned
              across both services.
            </p>
            <ul>
              <li>Vercel: set <code>VITE_API_URL</code>, <code>VITE_SUPABASE_URL</code>, <code>VITE_SUPABASE_ANON_KEY</code>.</li>
              <li>Render backend: set Redis URL, Supabase JWT settings, CORS origins, and machine API keys if used.</li>
              <li>Use HTTPS endpoints only and verify CORS includes exact frontend domains.</li>
            </ul>
          </article>

          <article id="troubleshooting" className="docs-section">
            <h2>Troubleshooting</h2>
            <ul>
              <li>If dashboard is empty, verify traces are being written to the same backend environment.</li>
              <li>If auth fails, confirm Supabase project URL/anon key and allowed redirect/origin settings.</li>
              <li>If Docker frontend can’t resolve packages, reinstall dependencies in container node_modules volume.</li>
              <li>If CI checks stay pending, ensure PR branch has no unresolved merge conflicts.</li>
            </ul>
          </article>

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
