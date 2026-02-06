import { useState } from 'react';
import './Sidebar.css';

export default function Sidebar({
    traces,
    selectedTraceId,
    onSelectTrace,
    onDeleteTrace,
    loading,
    isConnected,
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

    return (
        <div className="sidebar">
            {/* Header */}
            <div className="sidebar-header">
                <div className="logo">
                    <span className="logo-icon">🔦</span>
                    <span className="logo-text">Agent Lighthouse</span>
                </div>
                <div className={`connection-status ${isConnected ? 'connected' : 'disconnected'}`}>
                    <span className="status-dot"></span>
                    <span className="status-text">{isConnected ? 'Live' : 'Offline'}</span>
                </div>
            </div>

            {/* Search */}
            <div className="sidebar-search">
                <input
                    type="search"
                    placeholder="Search traces..."
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                />
            </div>

            {/* Traces List */}
            <div className="traces-list">
                {loading && filteredTraces.length === 0 ? (
                    <div className="list-empty">Loading traces...</div>
                ) : filteredTraces.length === 0 ? (
                    <div className="list-empty">
                        {search ? 'No matching traces' : 'No traces yet'}
                    </div>
                ) : (
                    filteredTraces.map(trace => (
                        <div
                            key={trace.trace_id}
                            className={`trace-item ${selectedTraceId === trace.trace_id ? 'selected' : ''}`}
                            onClick={() => onSelectTrace(trace.trace_id)}
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
                                    <span className="stat-icon">🤖</span>
                                    {trace.agent_count}
                                </span>
                                <span className="stat">
                                    <span className="stat-icon">🔧</span>
                                    {trace.tool_calls}
                                </span>
                                <span className="stat">
                                    <span className="stat-icon">🧠</span>
                                    {trace.llm_calls}
                                </span>
                                <span className="stat cost">
                                    ${trace.total_cost_usd.toFixed(4)}
                                </span>
                            </div>
                            {onDeleteTrace && (
                                <button
                                    className="delete-btn"
                                    onClick={(e) => {
                                        e.stopPropagation();
                                        onDeleteTrace(trace.trace_id);
                                    }}
                                    title="Delete trace"
                                >
                                    🗑️
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
