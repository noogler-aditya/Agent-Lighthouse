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

export function OnboardingPanel({ apiKey = '', onRequestApiKey }) {
  const [activeTab, setActiveTab] = useState('python');
  const [copyStatus, setCopyStatus] = useState('');
  const [apiKeyStatus, setApiKeyStatus] = useState('');
  const [apiKeyLoading, setApiKeyLoading] = useState(false);

  const snippet = useMemo(() => {
    const base = SNIPPETS[activeTab];
    if (!apiKey) return base;
    return base.replace(/lh_your_api_key/g, apiKey);
  }, [activeTab, apiKey]);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(snippet);
      setCopyStatus('Copied');
    } catch {
      setCopyStatus('Copy failed');
    }
    setTimeout(() => setCopyStatus(''), 1800);
  };

  const handleApiKey = async () => {
    if (!onRequestApiKey) return;
    setApiKeyLoading(true);
    setApiKeyStatus('');
    try {
      const key = await onRequestApiKey();
      if (key) {
        setApiKeyStatus('API key ready');
      } else {
        setApiKeyStatus('No API key returned');
      }
    } catch {
      setApiKeyStatus('Failed to fetch API key');
    } finally {
      setApiKeyLoading(false);
      setTimeout(() => setApiKeyStatus(''), 2400);
    }
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
        <p>Use your API key to start streaming traces.</p>
      </div>

      <div className="onboarding-steps">
        <div className="onboarding-step">
          <span className="step-index">1</span>
          <div className="step-body">
            <h4>Save your API key</h4>
              <p>Generate or copy your API key to authenticate your agents.</p>
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
            <div className="snippet-actions">
              {!apiKey && (
                <button className="btn btn-secondary btn-sm" onClick={handleApiKey} disabled={apiKeyLoading}>
                  {apiKeyLoading ? 'Fetching...' : 'Get API key'}
                </button>
              )}
              <button className="btn btn-secondary btn-sm" onClick={handleCopy}>
                {copyStatus || 'Copy'}
              </button>
            </div>
          </div>
          {apiKeyStatus && <div className="snippet-status">{apiKeyStatus}</div>}
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
