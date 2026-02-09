import { lazy, Suspense, useState, useEffect, useCallback } from 'react';
import { Coins, SearchCode } from './components/icons/AppIcons';
import { AUTH_BOOTSTRAP_PASSWORD, AUTH_BOOTSTRAP_USERNAME } from './config';
import { bootstrapSession, clearSession, getAuthContext, loginWithPassword } from './auth/session';
import { useWebSocket, useTraces, useAgentState } from './hooks';
import { Sidebar } from './components/Sidebar';
import './App.css';

const TraceGraph = lazy(() => import('./components/TraceGraph/TraceGraph'));
const TokenMonitor = lazy(() => import('./components/TokenMonitor/TokenMonitor'));
const StateInspector = lazy(() => import('./components/StateInspector/StateInspector'));

function App() {
  const [activeRightTab, setActiveRightTab] = useState('tokens');
  const [selectedSpan, setSelectedSpan] = useState(null);
  const [authReady, setAuthReady] = useState(false);
  const [authContext, setAuthContext] = useState(getAuthContext());
  const [loginError, setLoginError] = useState('');
  const [username, setUsername] = useState(AUTH_BOOTSTRAP_USERNAME || 'viewer');
  const [password, setPassword] = useState(AUTH_BOOTSTRAP_PASSWORD || 'viewer');

  // WebSocket connection
  const { isConnected, onMessage, subscribeToTrace, unsubscribeFromTrace } = useWebSocket(authContext.isAuthenticated);

  // Traces data
  const {
    traces,
    selectedTrace,
    loading,
    errorCode,
    errorMessage,
    lastFetchAt,
    fetchTrace,
    fetchTraces,
    deleteTrace,
    addSpanToTrace,
    updateSpanInTrace,
  } = useTraces(authContext.isAuthenticated);

  // Agent state
  const {
    state: agentState,
    controlStatus,
    fetchState,
    bulkModifyState,
    pause,
    resume,
    step,
  } = useAgentState(selectedTrace?.trace_id, authContext.isAuthenticated);

  useEffect(() => {
    let active = true;
    const run = async () => {
      try {
        const session = await bootstrapSession();
        if (!active) return;
        setAuthContext(session);
      } catch {
        if (!active) return;
        setAuthContext(getAuthContext());
      } finally {
        if (active) setAuthReady(true);
      }
    };
    run();
    return () => {
      active = false;
    };
  }, []);

  const handleLogin = useCallback(async (e) => {
    e.preventDefault();
    setLoginError('');
    try {
      const ctx = await loginWithPassword(username, password);
      setAuthContext(ctx);
    } catch (err) {
      setLoginError(err.message || 'Login failed');
    }
  }, [password, username]);

  const handleLogout = useCallback(() => {
    clearSession();
    setAuthContext(getAuthContext());
    setSelectedSpan(null);
  }, []);

  // Handle trace selection
  const handleSelectTrace = useCallback(async (traceId) => {
    await fetchTrace(traceId);
  }, [fetchTrace]);

  useEffect(() => {
    if (!isConnected || !selectedTrace?.trace_id) return;
    subscribeToTrace(selectedTrace.trace_id);
    fetchState();
    return () => {
      unsubscribeFromTrace(selectedTrace.trace_id);
    };
  }, [isConnected, selectedTrace?.trace_id, subscribeToTrace, unsubscribeFromTrace, fetchState]);

  // Handle WebSocket messages
  useEffect(() => {
    const unsubSpan = onMessage('span_created', (data) => {
      if (data.data) {
        addSpanToTrace(data.data);
      }
    });

    const unsubTrace = onMessage('trace_updated', () => {
      fetchTraces();
    });

    const unsubSpanUpdated = onMessage('span_updated', (data) => {
      if (data.data) {
        updateSpanInTrace(data.data);
      }
    });

    const unsubState = onMessage('state_change', (data) => {
      if (selectedTrace?.trace_id === data.trace_id) {
        fetchState();
      }
    });

    return () => {
      unsubSpan();
      unsubSpanUpdated();
      unsubTrace();
      unsubState();
    };
  }, [onMessage, addSpanToTrace, updateSpanInTrace, fetchTraces, fetchState, selectedTrace?.trace_id]);

  if (!authReady) {
    return <div className="auth-loading">Loading session...</div>;
  }

  if (!authContext.isAuthenticated) {
    return (
      <div className="auth-gate">
        <form className="auth-card" onSubmit={handleLogin}>
          <h1>Agent Lighthouse</h1>
          <p>Sign in to access traces</p>
          <label>
            Username
            <input type="text" value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="username" />
          </label>
          <label>
            Password
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
            />
          </label>
          {loginError ? <div className="auth-error">{loginError}</div> : null}
          <button className="btn btn-primary" type="submit">Sign in</button>
        </form>
      </div>
    );
  }

  return (
    <div className="app-container">
      {/* Sidebar */}
      <Sidebar
        traces={traces}
        selectedTraceId={selectedTrace?.trace_id}
        onSelectTrace={handleSelectTrace}
        onDeleteTrace={deleteTrace}
        canDeleteTraces={authContext.role === 'operator' || authContext.role === 'admin'}
        loading={loading}
        isConnected={isConnected}
        errorCode={errorCode}
        errorMessage={errorMessage}
        lastFetchAt={lastFetchAt}
        onRetry={fetchTraces}
      />

      {/* Main Content */}
      <div className="main-content" data-animate="enter">
        {/* Header */}
        <header className="main-header" data-animate="enter" data-delay="1">
          <div className="header-left">
            {selectedTrace ? (
              <>
                <h1 className="trace-title">{selectedTrace.name}</h1>
                <span className={`status-badge ${selectedTrace.status}`}>
                  {selectedTrace.status}
                </span>
              </>
            ) : (
              <h1 className="trace-title">Select a trace to begin</h1>
            )}
          </div>
          <div className="header-right">
            <span className="session-pill" title={`Role: ${authContext.role}`}>
              {authContext.subject} ({authContext.role})
            </span>
            <button className="btn btn-secondary btn-sm" onClick={handleLogout}>Logout</button>
            {selectedTrace && (
              <div className="header-stats">
                <span className="header-stat">
                  <strong>{selectedTrace.total_tokens.toLocaleString()}</strong> tokens
                </span>
                <span className="header-stat">
                  <strong>${selectedTrace.total_cost_usd.toFixed(4)}</strong>
                </span>
                <span className="header-stat">
                  <strong>{selectedTrace.spans?.length || 0}</strong> spans
                </span>
              </div>
            )}
          </div>
        </header>

        {/* Body */}
        <div className="main-body">
          {/* Graph Panel */}
          <div className="graph-panel" data-animate="enter" data-delay="1">
            <Suspense fallback={<div className="panel-loading">Loading graph...</div>}>
              <TraceGraph
                trace={selectedTrace}
                onSpanClick={setSelectedSpan}
              />
            </Suspense>
          </div>

          {/* Right Panel */}
          <div className="right-panel" data-animate="enter" data-delay="2">
            {/* Tabs */}
            <div className="right-panel-tabs">
              <div className="tabs">
                <button
                  className={`tab ${activeRightTab === 'tokens' ? 'active' : ''}`}
                  onClick={() => setActiveRightTab('tokens')}
                >
                  <Coins className="ui-icon ui-icon-sm" />
                  Tokens
                </button>
                <button
                  className={`tab ${activeRightTab === 'state' ? 'active' : ''}`}
                  onClick={() => setActiveRightTab('state')}
                >
                  <SearchCode className="ui-icon ui-icon-sm" />
                  State
                </button>
              </div>
            </div>

            {/* Panel Content */}
            <div className="right-panel-content">
              <div className="panel-stage" key={activeRightTab} data-animate="enter" data-delay="1">
                {activeRightTab === 'tokens' ? (
                  <Suspense fallback={<div className="panel-loading">Loading metrics...</div>}>
                    <TokenMonitor trace={selectedTrace} />
                  </Suspense>
                ) : (
                  <Suspense fallback={<div className="panel-loading">Loading inspector...</div>}>
                    <StateInspector
                      traceId={selectedTrace?.trace_id}
                      state={agentState}
                      controlStatus={controlStatus}
                      onPause={pause}
                      onResume={resume}
                      onStep={step}
                      onModifyState={bulkModifyState}
                    />
                  </Suspense>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Selected Span Detail (Modal) */}
      {selectedSpan && (
        <div className="span-modal-overlay" onClick={() => setSelectedSpan(null)}>
          <div className="span-modal" onClick={(e) => e.stopPropagation()}>
            <div className="span-modal-header">
              <h3>{selectedSpan.name}</h3>
              <button className="close-btn" onClick={() => setSelectedSpan(null)}>×</button>
            </div>
            <div className="span-modal-content">
              <div className="span-detail-grid">
                <div className="span-detail">
                  <label>Status</label>
                  <span className={`status-badge ${selectedSpan.status}`}>
                    {selectedSpan.status}
                  </span>
                </div>
                <div className="span-detail">
                  <label>Type</label>
                  <span>{selectedSpan.kind}</span>
                </div>
                <div className="span-detail">
                  <label>Tokens</label>
                  <span>{selectedSpan.total_tokens?.toLocaleString() || 0}</span>
                </div>
                <div className="span-detail">
                  <label>Cost</label>
                  <span>${selectedSpan.cost_usd?.toFixed(4) || '0.00'}</span>
                </div>
                <div className="span-detail">
                  <label>Duration</label>
                  <span>{selectedSpan.duration_ms?.toFixed(0) || '-'}ms</span>
                </div>
                {selectedSpan.agent_name && (
                  <div className="span-detail">
                    <label>Agent</label>
                    <span>{selectedSpan.agent_name}</span>
                  </div>
                )}
              </div>

              {selectedSpan.input_data && (
                <div className="span-data-section">
                  <h4>Input</h4>
                  <pre>{JSON.stringify(selectedSpan.input_data, null, 2)}</pre>
                </div>
              )}

              {selectedSpan.output_data && (
                <div className="span-data-section">
                  <h4>Output</h4>
                  <pre>{JSON.stringify(selectedSpan.output_data, null, 2)}</pre>
                </div>
              )}

              {selectedSpan.error_message && (
                <div className="span-data-section error">
                  <h4>Error</h4>
                  <pre>{selectedSpan.error_message}</pre>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
