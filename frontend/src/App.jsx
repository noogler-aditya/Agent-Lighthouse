import { useState, useEffect, useCallback } from 'react';
import { useWebSocket, useTraces, useAgentState } from './hooks';
import { Sidebar } from './components/Sidebar';
import { TraceGraph } from './components/TraceGraph';
import { TokenMonitor } from './components/TokenMonitor';
import { StateInspector } from './components/StateInspector';
import './App.css';

function App() {
  const [activeRightTab, setActiveRightTab] = useState('tokens');
  const [selectedSpan, setSelectedSpan] = useState(null);

  // WebSocket connection
  const { isConnected, onMessage, subscribeToTrace } = useWebSocket();

  // Traces data
  const {
    traces,
    selectedTrace,
    loading,
    fetchTrace,
    fetchTraces,
    deleteTrace,
    setSelectedTrace,
    addSpanToTrace,
  } = useTraces();

  // Agent state
  const {
    state: agentState,
    controlStatus,
    fetchState,
    bulkModifyState,
    pause,
    resume,
    step,
  } = useAgentState(selectedTrace?.trace_id);

  // Handle trace selection
  const handleSelectTrace = useCallback(async (traceId) => {
    const trace = await fetchTrace(traceId);
    if (trace) {
      subscribeToTrace(traceId);
      fetchState();
    }
  }, [fetchTrace, subscribeToTrace, fetchState]);

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

    const unsubState = onMessage('state_change', (data) => {
      if (selectedTrace?.trace_id === data.trace_id) {
        fetchState();
      }
    });

    return () => {
      unsubSpan();
      unsubTrace();
      unsubState();
    };
  }, [onMessage, addSpanToTrace, fetchTraces, fetchState, selectedTrace]);

  return (
    <div className="app-container">
      {/* Sidebar */}
      <Sidebar
        traces={traces}
        selectedTraceId={selectedTrace?.trace_id}
        onSelectTrace={handleSelectTrace}
        onDeleteTrace={deleteTrace}
        loading={loading}
        isConnected={isConnected}
      />

      {/* Main Content */}
      <div className="main-content">
        {/* Header */}
        <header className="main-header">
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
          <div className="graph-panel">
            <TraceGraph
              trace={selectedTrace}
              onSpanClick={setSelectedSpan}
            />
          </div>

          {/* Right Panel */}
          <div className="right-panel">
            {/* Tabs */}
            <div className="right-panel-tabs">
              <div className="tabs">
                <button
                  className={`tab ${activeRightTab === 'tokens' ? 'active' : ''}`}
                  onClick={() => setActiveRightTab('tokens')}
                >
                  💰 Tokens
                </button>
                <button
                  className={`tab ${activeRightTab === 'state' ? 'active' : ''}`}
                  onClick={() => setActiveRightTab('state')}
                >
                  🔍 State
                </button>
              </div>
            </div>

            {/* Panel Content */}
            <div className="right-panel-content">
              {activeRightTab === 'tokens' ? (
                <TokenMonitor trace={selectedTrace} />
              ) : (
                <StateInspector
                  traceId={selectedTrace?.trace_id}
                  state={agentState}
                  controlStatus={controlStatus}
                  onPause={pause}
                  onResume={resume}
                  onStep={step}
                  onModifyState={bulkModifyState}
                />
              )}
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
