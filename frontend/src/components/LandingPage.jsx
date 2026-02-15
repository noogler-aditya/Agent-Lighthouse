import { Bot, Coins, Radar, SearchCode } from './icons/AppIcons';
import './LandingPage.css';

const DOCS_URL = 'https://github.com/noogler-aditya/Agent-Lighthouse/blob/main/docs/GETTING_STARTED.md';
const REPO_URL = 'https://github.com/noogler-aditya/Agent-Lighthouse';

const featureCards = [
  {
    title: 'Visual Tracing',
    description: 'Inspect agent calls and handoffs as a live graph to isolate slow paths and logic breaks faster.',
    icon: <Radar className="ui-icon" />,
    tone: 'primary',
  },
  {
    title: 'Token Monitor',
    description: 'Track token and cost usage across traces so optimization decisions are based on real workloads.',
    icon: <Coins className="ui-icon" />,
    tone: 'warning',
  },
  {
    title: 'State Inspector',
    description: 'Pause, inspect, and modify state transitions to debug agent behavior with minimal guesswork.',
    icon: <SearchCode className="ui-icon" />,
    tone: 'info',
  },
];

const workflowSteps = [
  {
    title: 'Instrument',
    description: 'Send traces from your agents using the project API key flow and trace endpoints.',
  },
  {
    title: 'Observe',
    description: 'Review spans, token usage, and state transitions in one dashboard with live updates.',
  },
  {
    title: 'Improve',
    description: 'Tune prompts, tools, and orchestration logic with clear feedback from production-like traces.',
  },
];

export function LandingPage({ onLoginClick }) {
  return (
    <div className="landing-page">
      <header className="landing-nav-wrap">
        <nav className="landing-nav" aria-label="Primary">
          <div className="landing-brand">
            <div className="landing-brand-logo" aria-hidden="true">
              <Bot className="ui-icon" />
            </div>
            <span className="landing-brand-name">Agent Lighthouse</span>
          </div>

          <div className="landing-nav-actions">
            <a href={REPO_URL} target="_blank" rel="noreferrer" className="landing-nav-link">GitHub</a>
            <a href={DOCS_URL} target="_blank" rel="noreferrer" className="landing-nav-link">Docs</a>
            <button type="button" className="btn btn-secondary btn-sm" onClick={onLoginClick}>Sign In</button>
          </div>
        </nav>
      </header>

      <main className="landing-main">
        <section className="landing-hero" aria-labelledby="landing-title">
          <div className="landing-hero-copy" data-animate="enter" data-delay="1">
            <p className="landing-eyebrow">Open-source agent observability</p>
            <h1 id="landing-title" className="landing-title">
              Debug AI agent systems with full execution visibility
            </h1>
            <p className="landing-subtitle">
              Agent Lighthouse helps teams trace calls, inspect state transitions, and monitor token usage
              so failures are diagnosable before they become incidents.
            </p>

            <div className="landing-hero-actions">
              <button type="button" className="btn btn-primary landing-btn-lg" onClick={onLoginClick}>
                Start Debugging
              </button>
              <a href={DOCS_URL} target="_blank" rel="noreferrer" className="btn btn-secondary landing-btn-lg">
                View Docs
              </a>
            </div>
          </div>

          <aside className="landing-hero-visual" aria-hidden="true" data-animate="enter" data-delay="2">
            <div className="landing-radar-shell">
              <Radar className="landing-radar-icon" />
              <div className="landing-radar-ring ring-one" />
              <div className="landing-radar-ring ring-two" />
              <div className="landing-radar-ring ring-three" />
            </div>
            <div className="landing-visual-stat">
              <span>Trace graph</span>
              <strong>Live span events</strong>
            </div>
          </aside>
        </section>

        <section className="landing-feature-section" aria-labelledby="features-title">
          <h2 id="features-title" className="landing-section-title">Core capabilities</h2>
          <div className="landing-feature-grid">
            {featureCards.map(({ title, description, icon, tone }) => (
              <article key={title} className="landing-feature-card" data-animate="enter" data-delay="2">
                <div className={`landing-feature-icon ${tone}`} aria-hidden="true">
                  {icon}
                </div>
                <h3>{title}</h3>
                <p>{description}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="landing-steps-section" aria-labelledby="steps-title">
          <h2 id="steps-title" className="landing-section-title">How it works</h2>
          <div className="landing-steps-grid">
            {workflowSteps.map((step, index) => (
              <article key={step.title} className="landing-step-card" data-animate="enter" data-delay="3">
                <span className="landing-step-index" aria-hidden="true">{index + 1}</span>
                <h3>{step.title}</h3>
                <p>{step.description}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="landing-cta-band" aria-labelledby="cta-title" data-animate="enter" data-delay="3">
          <div>
            <h2 id="cta-title">Ship reliable multi-agent workflows with clearer diagnostics</h2>
            <p>Use Agent Lighthouse to inspect behavior, reduce debugging time, and improve runtime confidence.</p>
          </div>
          <button type="button" className="btn btn-primary landing-btn-lg" onClick={onLoginClick}>
            Sign In to Continue
          </button>
        </section>
      </main>

      <footer className="landing-footer">
        <p>MIT licensed. Built for production debugging workflows.</p>
        <div className="landing-footer-links">
          <a href={REPO_URL} target="_blank" rel="noreferrer">Repository</a>
          <a href={DOCS_URL} target="_blank" rel="noreferrer">Documentation</a>
        </div>
      </footer>
    </div>
  );
}
