import { useMemo, useState } from 'react';
import { Bot, SearchCode } from './icons/AppIcons';
import './OnboardingPanel.css';

const DOCS_URL = 'https://github.com/noogler-aditya/Agent-Lighthouse/blob/main/docs/GETTING_STARTED.md';

const SNIPPETS = {
  python: `from agent_lighthouse import get_tracer

tracer = get_tracer(
    base_url="https://your-lighthouse.example.com",
    api_key="lh_your_api_key"
)

trace = tracer.start_trace("my-first-trace")
trace.end(status="success")`,
  curl: `curl -X POST https://your-lighthouse.example.com/api/traces \\
  -H "X-API-Key: lh_your_api_key" \\
  -H "Content-Type: application/json" \\
  -d '{"name":"my-first-trace"}'`
};

export function OnboardingPanel() {
  const [activeTab, setActiveTab] = useState('python');
  const [copyStatus, setCopyStatus] = useState('');

  const snippet = useMemo(() => SNIPPETS[activeTab], [activeTab]);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(snippet);
      setCopyStatus('Copied');
    } catch {
      setCopyStatus('Copy failed');
    }
    setTimeout(() => setCopyStatus(''), 1800);
  };

  return (
    <div className="onboarding-panel" data-animate="enter" data-delay="1">
      <div className="onboarding-header">
        <div className="onboarding-badge">
          <span className="badge-dot"></span>
          Getting Started
        </div>
        <div className="onboarding-title">
          <div className="onboarding-icon">
            <Bot className="ui-icon" />
          </div>
          <h2>Connect your agent</h2>
        </div>
        <p>Use the API key from signup to start streaming traces.</p>
      </div>

      <div className="onboarding-steps">
        <div className="onboarding-step">
          <span className="step-index">1</span>
          <div className="step-body">
            <h4>Save your API key</h4>
            <p>You’ll only see this key once. Store it in a secure secret manager.</p>
          </div>
        </div>
        <div className="onboarding-step">
          <span className="step-index">2</span>
          <div className="step-body">
            <h4>Install the SDK</h4>
            <p>Use the API key in your agent runtime to send traces.</p>
          </div>
        </div>
        <div className="onboarding-step">
          <span className="step-index">3</span>
          <div className="step-body">
            <h4>Send your first trace</h4>
            <p>Run your agent and traces will appear here automatically.</p>
          </div>
        </div>
      </div>

      <div className="onboarding-snippets">
        <div className="snippet-tabs">
          <button
            className={`snippet-tab ${activeTab === 'python' ? 'active' : ''}`}
            onClick={() => setActiveTab('python')}
          >
            Python
          </button>
          <button
            className={`snippet-tab ${activeTab === 'curl' ? 'active' : ''}`}
            onClick={() => setActiveTab('curl')}
          >
            cURL
          </button>
        </div>
        <div className="snippet-card">
          <div className="snippet-header">
            <div className="snippet-title">
              <SearchCode className="ui-icon-sm" />
              Quick start
            </div>
            <button className="btn btn-secondary btn-sm" onClick={handleCopy}>
              {copyStatus || 'Copy'}
            </button>
          </div>
          <pre className="snippet-code">
            <code>{snippet}</code>
          </pre>
        </div>
      </div>

      <div className="onboarding-footer">
        <span>Run your agent to see traces appear here.</span>
        <a href={DOCS_URL} target="_blank" rel="noreferrer">Need help? Docs</a>
      </div>
    </div>
  );
}
