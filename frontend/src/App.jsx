import { lazy, Suspense, useState, useEffect, useCallback } from 'react';
import { Clock, Coins, SearchCode } from './components/icons/AppIcons';
import { API_URL } from './config';
import { bootstrapSession, clearSession, getAuthContext, loginWithPassword, registerWithPassword, authFetch } from './auth/session';
import { useWebSocket, useTraces, useAgentState, useToast } from './hooks';
import { Sidebar } from './components/Sidebar';
import { LandingPage } from './components/LandingPage';
import { AuthModal } from './components/AuthModal';
import { OnboardingPanel } from './components/OnboardingPanel';
import ToastContainer from './components/ToastContainer';
import './App.css';

const TraceGraph = lazy(() => import('./components/TraceGraph/TraceGraph'));
const TokenMonitor = lazy(() => import('./components/TokenMonitor/TokenMonitor'));
const StateInspector = lazy(() => import('./components/StateInspector/StateInspector'));
const Timeline = lazy(() => import('./components/Timeline/Timeline'));

function App() {
  const [activeRightTab, setActiveRightTab] = useState('tokens');
  const [selectedSpan, setSelectedSpan] = useState(null);
  const [authReady, setAuthReady] = useState(false);
  const [authContext, setAuthContext] = useState(getAuthContext());
  const [sidebarDensity, setSidebarDensity] = useState('comfortable');
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [inspectorCollapsed, setInspectorCollapsed] = useState(false);

  // Modal State
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);

  // Toast notifications
  const { toasts, removeToast, success, error: showError, warning, info } = useToast();

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

  const hasTraces = traces.length > 0;
  const showOnboarding = authContext.isAuthenticated && !hasTraces;

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

  const handleLogin = useCallback(async (username, password) => {
    const ctx = await loginWithPassword(username, password);
    setAuthContext(ctx);
    setIsAuthModalOpen(false);
    success('Signed in successfully');
  }, [success]);

  const handleRegister = useCallback(async (username, password) => {
    const result = await registerWithPassword(username, password);
    success('Account created');
    return { apiKey: result.apiKey };
  }, [success]);

  const handleAuthModalClose = useCallback(() => {
    setIsAuthModalOpen(false);
    setAuthContext(getAuthContext());
  }, []);

  const handleLogout = useCallback(() => {
    clearSession();
    setAuthContext(getAuthContext());
    setSelectedSpan(null);
    info('Signed out');
  }, [info]);

  // Handle trace selection
  const handleSelectTrace = useCallback(async (traceId) => {
    await fetchTrace(traceId);
    if (window.matchMedia('(max-width: 768px)').matches) {
      setSidebarCollapsed(true);
    }
  }, [fetchTrace]);

  // Handle trace deletion with toast feedback
  const handleDeleteTrace = useCallback(async (traceId) => {
    try {
      await deleteTrace(traceId);
      success('Trace deleted');
    } catch {
      showError('Failed to delete trace');
    }
  }, [deleteTrace, success, showError]);

  // Handle trace export
  const handleExportTrace = useCallback(async (traceId, traceName) => {
    try {
      const res = await authFetch(`${API_URL}/traces/${traceId}/export`);
      if (!res.ok) {
        showError('Failed to export trace');
        return;
      }
      const data = await res.json();
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `trace-${traceId.slice(0, 8)}-${(traceName || 'export').replace(/\s+/g, '_').slice(0, 30)}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      success('Trace exported successfully');
    } catch {
      showError('Failed to export trace');
    }
  }, [success, showError]);

  // Handle pause/resume/step with toast feedback
  const handlePause = useCallback(async () => {
    await pause();
    warning('Execution paused');
  }, [pause, warning]);

  const handleResume = useCallback(async () => {
    await resume();
    success('Execution resumed');
  }, [resume, success]);

  const handleStep = useCallback(async () => {
    await step();
    info('Stepping one step');
  }, [step, info]);

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

  // Not Authenticated -> Show Landing Page
  if (!authContext.isAuthenticated) {
    return (
      <>
        <LandingPage onLoginClick={() => setIsAuthModalOpen(true)} />
        <AuthModal
          isOpen={isAuthModalOpen}
          onClose={handleAuthModalClose}
          onLogin={handleLogin}
          onRegister={handleRegister}
        />
        <ToastContainer toasts={toasts} onDismiss={removeToast} />
      </>
    );
  }

  // Authenticated -> Show Dashboard
  return (
    <div className="app-container">
      <aside className={`left-rail ${sidebarCollapsed ? 'collapsed' : ''}`}>
        <Sidebar
          traces={traces}
          selectedTraceId={selectedTrace?.trace_id}
          onSelectTrace={handleSelectTrace}
          onDeleteTrace={handleDeleteTrace}
          onExportTrace={handleExportTrace}
          canDeleteTraces={authContext.isAuthenticated}
          loading={loading}
          isConnected={isConnected}
          errorCode={errorCode}
          errorMessage={errorMessage}
          lastFetchAt={lastFetchAt}
          onRetry={fetchTraces}
          density={sidebarDensity}
          groupBy="date"
          defaultFiltersOpen={false}
          sidebarCollapsed={sidebarCollapsed}
          onToggleSidebar={() => setSidebarCollapsed((prev) => !prev)}
          onDensityChange={setSidebarDensity}
        />
      </aside>

      <div className="main-shell" data-animate="enter">
        {/* Header */}
        <header className="main-header" data-animate="enter" data-delay="1">
          <div className="header-left">
            <button
              className="btn btn-secondary btn-sm sidebar-toggle"
              onClick={() => setSidebarCollapsed((prev) => !prev)}
              aria-label={sidebarCollapsed ? 'Show sidebar' : 'Hide sidebar'}
              title={sidebarCollapsed ? 'Show sidebar' : 'Hide sidebar'}
            >
              {sidebarCollapsed ? 'Show' : 'Hide'}
            </button>
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
            <button
              className="btn btn-secondary btn-sm medium-only"
              onClick={() => setInspectorCollapsed((prev) => !prev)}
              aria-label="Toggle inspector panel"
            >
              {inspectorCollapsed ? 'Show panel' : 'Hide panel'}
            </button>
            <span className="session-pill" title="Signed in">
              {authContext.subject}
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
          <section className="workspace" data-animate="enter" data-delay="1">
            <div className="graph-panel">
              <Suspense fallback={<div className="panel-loading">Loading graph...</div>}>
                {showOnboarding && !selectedTrace ? (
                  <OnboardingPanel />
                ) : (
                  <TraceGraph
                    trace={selectedTrace}
                    onSpanClick={setSelectedSpan}
                  />
                )}
              </Suspense>
            </div>
          </section>

          <aside className={`inspector ${inspectorCollapsed ? 'collapsed' : ''}`} data-animate="enter" data-delay="2">
            <div className="right-panel">
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
                    className={`tab ${activeRightTab === 'timeline' ? 'active' : ''}`}
                    onClick={() => setActiveRightTab('timeline')}
                  >
                    <Clock className="ui-icon ui-icon-sm" />
                    Timeline
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

              <div className="right-panel-content">
                <div className="panel-stage" key={activeRightTab} data-animate="enter" data-delay="1">
                  {activeRightTab === 'tokens' ? (
                    <Suspense fallback={<div className="panel-loading">Loading metrics...</div>}>
                      <TokenMonitor trace={selectedTrace} />
                    </Suspense>
                  ) : activeRightTab === 'timeline' ? (
                    <Suspense fallback={<div className="panel-loading">Loading timeline...</div>}>
                      <Timeline
                        trace={selectedTrace}
                        onSpanClick={setSelectedSpan}
                      />
                    </Suspense>
                  ) : (
                    <Suspense fallback={<div className="panel-loading">Loading inspector...</div>}>
                      <StateInspector
                        traceId={selectedTrace?.trace_id}
                        state={agentState}
                        controlStatus={controlStatus}
                        onPause={handlePause}
                        onResume={handleResume}
                        onStep={handleStep}
                        onModifyState={bulkModifyState}
                      />
                    </Suspense>
                  )}
                </div>
              </div>
            </div>
          </aside>
        </div>
      </div>
      {sidebarCollapsed && <button className="mobile-sidebar-scrim" aria-label="Close sidebar" onClick={() => setSidebarCollapsed(false)} />}

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

      {/* Toast Notifications */}
      <ToastContainer toasts={toasts} onDismiss={removeToast} />
    </div>
  );
}

export default App;
