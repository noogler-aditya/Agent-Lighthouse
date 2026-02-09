import { useState } from 'react';
import { Bot, Cpu, Radar, RefreshCcw, Trash2, Wrench } from '../icons/AppIcons';
import './Sidebar.css';

export default function Sidebar({
    traces,
    selectedTraceId,
    onSelectTrace,
    onDeleteTrace,
    canDeleteTraces = false,
    loading,
    isConnected,
    errorCode,
    errorMessage,
    lastFetchAt,
    onRetry,
}) {
    const [search, setSearch] = useState('');

    const filteredTraces = traces.filter(trace =>
        trace.name.toLowerCase().includes(search.toLowerCase())
    );

    const formatTime = (dateStr) => {
        const date = new Date(dateStr);
        return date.toLocaleTimeString();
    };

    const formatDuration = (ms) => {
        if (!ms) return '-';
        if (ms < 1000) return `${ms.toFixed(0)}ms`;
        return `${(ms / 1000).toFixed(1)}s`;
    };

    const getErrorHint = () => {
        if (errorCode === 401 || errorCode === 403) {
            return 'Session expired or unauthorized. Sign in again and verify backend auth settings.';
        }
        if (errorCode === 'NETWORK') {
            return 'Backend unreachable at configured VITE_API_URL';
        }
        return 'Unable to load traces from backend';
    };

    const formatLastFetch = () => {
        if (!lastFetchAt) return '';
        return new Date(lastFetchAt).toLocaleTimeString();
    };

    return (
        <div className="sidebar" data-animate="enter">
            {/* Header */}
            <div className="sidebar-header" data-animate="enter" data-delay="1">
                <div className="logo">
                    <Radar className="ui-icon logo-icon" />
                    <span className="logo-text">Agent Lighthouse</span>
                </div>
                <div className={`connection-status ${isConnected ? 'connected' : 'disconnected'}`}>
                    <span className="status-dot"></span>
                    <span className="status-text">{isConnected ? 'Live' : 'Offline'}</span>
                </div>
            </div>

            {/* Search */}
            <div className="sidebar-search" data-animate="enter" data-delay="2">
                <input
                    type="search"
                    placeholder="Search traces..."
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                />
            </div>

            {/* Traces List */}
            <div className="traces-list">
                {loading && filteredTraces.length === 0 && !errorMessage ? (
                    <div className="list-empty">Loading traces...</div>
                ) : errorMessage ? (
                    <div className="list-error" data-animate="enter" data-delay="1">
                        <div className="list-error-title">Could not load traces</div>
                        <div className="list-error-hint">{getErrorHint()}</div>
                        <div className="list-error-meta">
                            {errorCode ? `Code: ${errorCode}` : 'Code: unknown'}
                            {lastFetchAt ? ` • Last checked: ${formatLastFetch()}` : ''}
                        </div>
                        <button className="btn btn-secondary list-error-retry" onClick={onRetry}>
                            <RefreshCcw className="ui-icon ui-icon-sm" />
                            Retry
                        </button>
                    </div>
                ) : filteredTraces.length === 0 ? (
                    <div className="list-empty">
                        {search ? 'No matching traces' : 'No traces yet'}
                    </div>
                ) : (
                    filteredTraces.map((trace, index) => (
                        <div
                            key={trace.trace_id}
                            className={`trace-item ${selectedTraceId === trace.trace_id ? 'selected' : ''}`}
                            onClick={() => onSelectTrace(trace.trace_id)}
                            data-animate="enter"
                            data-delay={String((index % 3) + 1)}
                        >
                            <div className="trace-header">
                                <span className="trace-name">{trace.name}</span>
                                <span className={`status-badge ${trace.status}`}>
                                    {trace.status}
                                </span>
                            </div>
                            <div className="trace-meta">
                                <span className="trace-time">{formatTime(trace.start_time)}</span>
                                <span className="trace-duration">{formatDuration(trace.duration_ms)}</span>
                                <span className="trace-tokens">{trace.total_tokens.toLocaleString()} tokens</span>
                            </div>
                            <div className="trace-stats">
                                <span className="stat">
                                    <Bot className="ui-icon ui-icon-xs stat-icon" />
                                    {trace.agent_count}
                                </span>
                                <span className="stat">
                                    <Wrench className="ui-icon ui-icon-xs stat-icon" />
                                    {trace.tool_calls}
                                </span>
                                <span className="stat">
                                    <Cpu className="ui-icon ui-icon-xs stat-icon" />
                                    {trace.llm_calls}
                                </span>
                                <span className="stat cost">
                                    ${trace.total_cost_usd.toFixed(4)}
                                </span>
                            </div>
                            {onDeleteTrace && canDeleteTraces && (
                                <button
                                    className="delete-btn"
                                    onClick={(e) => {
                                        e.stopPropagation();
                                        onDeleteTrace(trace.trace_id);
                                    }}
                                    title="Delete trace"
                                    aria-label="Delete trace"
                                >
                                    <Trash2 className="ui-icon ui-icon-xs" />
                                </button>
                            )}
                        </div>
                    ))
                )}
            </div>

            {/* Footer */}
            <div className="sidebar-footer">
                <span className="trace-count">{traces.length} traces</span>
            </div>
        </div>
    );
}
