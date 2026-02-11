import { useMemo, useState } from 'react';
import { Bot, ChevronLeft, ChevronRight, Cpu, Download, Filter, Radar, RefreshCcw, Trash2, Wrench } from '../icons/AppIcons';
import './Sidebar.css';

const STATUS_OPTIONS = [
  { value: '', label: 'All Status' },
  { value: 'running', label: 'Running' },
  { value: 'success', label: 'Success' },
  { value: 'error', label: 'Error' },
  { value: 'cancelled', label: 'Cancelled' },
];

function dateGroupLabel(dateStr) {
  const date = new Date(dateStr);
  const today = new Date();
  const yesterday = new Date();
  yesterday.setDate(today.getDate() - 1);

  const isSameDay = (a, b) =>
    a.getFullYear() === b.getFullYear() &&
    a.getMonth() === b.getMonth() &&
    a.getDate() === b.getDate();

  if (isSameDay(date, today)) return 'Today';
  if (isSameDay(date, yesterday)) return 'Yesterday';
  return 'Earlier';
}

export default function Sidebar({
  traces,
  selectedTraceId,
  onSelectTrace,
  onDeleteTrace,
  onExportTrace,
  canDeleteTraces = false,
  loading,
  isConnected,
  errorCode,
  errorMessage,
  lastFetchAt,
  onRetry,
  density = 'comfortable',
  groupBy = 'date',
  defaultFiltersOpen = false,
  sidebarCollapsed = false,
  onToggleSidebar,
  onDensityChange,
}) {
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [showFilters, setShowFilters] = useState(defaultFiltersOpen);
  const [sortBy, setSortBy] = useState('newest');

  const filteredTraces = useMemo(() => {
    let result = traces;

    if (search) {
      const searchLower = search.toLowerCase();
      result = result.filter((trace) =>
        trace.name.toLowerCase().includes(searchLower) ||
        (trace.framework && trace.framework.toLowerCase().includes(searchLower))
      );
    }

    if (statusFilter) {
      result = result.filter((trace) => trace.status === statusFilter);
    }

    result = [...result].sort((a, b) => {
      switch (sortBy) {
        case 'oldest':
          return new Date(a.start_time) - new Date(b.start_time);
        case 'cost':
          return (b.total_cost_usd || 0) - (a.total_cost_usd || 0);
        case 'tokens':
          return (b.total_tokens || 0) - (a.total_tokens || 0);
        case 'newest':
        default:
          return new Date(b.start_time) - new Date(a.start_time);
      }
    });

    return result;
  }, [traces, search, statusFilter, sortBy]);

  const groupedTraces = useMemo(() => {
    if (groupBy !== 'date') {
      return [{ label: 'All traces', traces: filteredTraces }];
    }

    const buckets = new Map([
      ['Today', []],
      ['Yesterday', []],
      ['Earlier', []],
    ]);

    filteredTraces.forEach((trace) => {
      const label = dateGroupLabel(trace.start_time);
      buckets.get(label)?.push(trace);
    });

    return [...buckets.entries()]
      .filter(([, items]) => items.length > 0)
      .map(([label, grouped]) => ({ label, traces: grouped }));
  }, [filteredTraces, groupBy]);

  const stats = useMemo(() => {
    const running = traces.filter((t) => t.status === 'running').length;
    const errors = traces.filter((t) => t.status === 'error').length;
    const totalCost = traces.reduce((sum, t) => sum + (t.total_cost_usd || 0), 0);
    return { running, errors, totalCost };
  }, [traces]);

  const formatTime = (dateStr) => new Date(dateStr).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

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
    <div className={`sidebar sidebar--${density} ${sidebarCollapsed ? 'is-collapsed' : ''}`} data-animate="enter">
      <div className="sidebar-topbar" data-animate="enter" data-delay="1">
        <div className="logo">
          <Radar className="ui-icon logo-icon" />
          <span className="logo-text">Agent Lighthouse</span>
        </div>
        <div className="topbar-actions">
          <div className={`connection-status ${isConnected ? 'connected' : 'disconnected'}`}>
            <span className="status-dot" />
            <span className="status-text">{isConnected ? 'Live' : 'Offline'}</span>
          </div>
          <button className="rail-close" onClick={onToggleSidebar} aria-label={sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}>
            {sidebarCollapsed ? <ChevronRight className="ui-icon ui-icon-sm" /> : <ChevronLeft className="ui-icon ui-icon-sm" />}
          </button>
        </div>
      </div>

      <div className="sidebar-controls" data-animate="enter" data-delay="2">
        <div className="search-row">
          <input
            type="search"
            placeholder="Search traces or frameworks"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            id="sidebar-search-input"
          />
          <button
            className={`filter-toggle-btn ${showFilters ? 'active' : ''}`}
            onClick={() => setShowFilters((prev) => !prev)}
            title="Toggle filters"
            aria-label="Toggle filters"
          >
            <Filter className="ui-icon ui-icon-sm" />
            {statusFilter && <span className="filter-badge" />}
          </button>
        </div>

        {showFilters && (
          <div className="filter-panel" data-animate="enter">
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="filter-select"
              id="sidebar-status-filter"
            >
              {STATUS_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              className="filter-select"
              id="sidebar-sort-select"
            >
              <option value="newest">Newest First</option>
              <option value="oldest">Oldest First</option>
              <option value="cost">Highest Cost</option>
              <option value="tokens">Most Tokens</option>
            </select>
          </div>
        )}

        <div className="density-switch" role="group" aria-label="Sidebar density">
          <button
            className={`density-btn ${density === 'comfortable' ? 'active' : ''}`}
            onClick={() => onDensityChange?.('comfortable')}
            aria-pressed={density === 'comfortable'}
          >
            Comfortable
          </button>
          <button
            className={`density-btn ${density === 'compact' ? 'active' : ''}`}
            onClick={() => onDensityChange?.('compact')}
            aria-pressed={density === 'compact'}
          >
            Compact
          </button>
        </div>
      </div>

      {traces.length > 0 && (
        <div className="sidebar-stats-bar">
          <span className="sidebar-stat-pill">{traces.length} traces</span>
          {stats.running > 0 && <span className="sidebar-stat-pill running">{stats.running} running</span>}
          {stats.errors > 0 && <span className="sidebar-stat-pill error">{stats.errors} errors</span>}
          {stats.totalCost > 0 && <span className="sidebar-stat-pill cost">${stats.totalCost.toFixed(4)}</span>}
        </div>
      )}

      <div className="traces-list" role="list">
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
            {search || statusFilter ? 'No matching traces' : 'No traces yet'}
          </div>
        ) : (
          groupedTraces.map((group, groupIndex) => (
            <section className="trace-group" key={group.label} data-animate="enter" data-delay={String((groupIndex % 3) + 1)}>
              <header className="trace-group-title">{group.label}</header>
              <div className="trace-group-items">
                {group.traces.map((trace, index) => (
                  <div
                    key={trace.trace_id}
                    className={`trace-item ${selectedTraceId === trace.trace_id ? 'selected' : ''}`}
                    onClick={() => onSelectTrace(trace.trace_id)}
                    role="listitem"
                    data-animate="enter"
                    data-delay={String((index % 3) + 1)}
                  >
                    <div className="trace-header">
                      <span className="trace-name">{trace.name}</span>
                      <span className={`status-badge ${trace.status}`}>{trace.status}</span>
                    </div>
                    <div className="trace-meta">
                      <span className="trace-time">{formatTime(trace.start_time)}</span>
                      <span className="trace-duration">{formatDuration(trace.duration_ms)}</span>
                      <span className="trace-tokens">{(trace.total_tokens || 0).toLocaleString()} tokens</span>
                    </div>
                    <div className="trace-stats">
                      <span className="stat"><Bot className="ui-icon ui-icon-xs stat-icon" />{trace.agent_count}</span>
                      <span className="stat"><Wrench className="ui-icon ui-icon-xs stat-icon" />{trace.tool_calls}</span>
                      <span className="stat"><Cpu className="ui-icon ui-icon-xs stat-icon" />{trace.llm_calls}</span>
                      <span className="stat cost">${(trace.total_cost_usd || 0).toFixed(4)}</span>
                    </div>

                    <div className="trace-actions">
                      {onExportTrace && (
                        <button
                          className="action-btn export-btn"
                          onClick={(e) => {
                            e.stopPropagation();
                            onExportTrace(trace.trace_id, trace.name);
                          }}
                          title="Export trace as JSON"
                          aria-label="Export trace"
                        >
                          <Download className="ui-icon ui-icon-xs" />
                        </button>
                      )}
                      {onDeleteTrace && canDeleteTraces && (
                        <button
                          className="action-btn delete-btn"
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
                  </div>
                ))}
              </div>
            </section>
          ))
        )}
      </div>

      <div className="sidebar-footer">
        <span className="trace-count">
          {filteredTraces.length === traces.length
            ? `${traces.length} traces`
            : `${filteredTraces.length} of ${traces.length} traces`}
        </span>
      </div>
    </div>
  );
}
