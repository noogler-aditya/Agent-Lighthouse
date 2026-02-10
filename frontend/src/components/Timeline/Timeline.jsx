import { useMemo } from 'react';
import './Timeline.css';

/**
 * Timeline/Waterfall view — shows spans as horizontal bars on a time axis.
 * Like Chrome DevTools Network tab, but for agent spans.
 */

const KIND_COLORS = {
    agent: { bg: 'rgba(99, 102, 241, 0.8)', border: '#6366f1', label: '#c7d2fe' },
    llm: { bg: 'rgba(139, 92, 246, 0.8)', border: '#8b5cf6', label: '#ddd6fe' },
    tool: { bg: 'rgba(16, 185, 129, 0.8)', border: '#10b981', label: '#a7f3d0' },
    chain: { bg: 'rgba(59, 130, 246, 0.8)', border: '#3b82f6', label: '#bfdbfe' },
    retriever: { bg: 'rgba(245, 158, 11, 0.8)', border: '#f59e0b', label: '#fde68a' },
    internal: { bg: 'rgba(100, 116, 139, 0.6)', border: '#64748b', label: '#cbd5e1' },
};

function formatDuration(ms) {
    if (!ms && ms !== 0) return '-';
    if (ms < 1) return '<1ms';
    if (ms < 1000) return `${ms.toFixed(0)}ms`;
    return `${(ms / 1000).toFixed(2)}s`;
}



export default function Timeline({ trace, onSpanClick }) {
    const { rows, totalDuration } = useMemo(() => {
        if (!trace?.spans?.length) {
            return { rows: [], totalDuration: 0, traceStart: 0 };
        }

        const spans = [...trace.spans];
        const startTimes = spans.map(s => new Date(s.start_time).getTime());
        const minStart = Math.min(...startTimes);

        // Sort by start time, then by depth
        const depthMap = new Map();
        const spanMap = new Map(spans.map(s => [s.span_id, s]));

        function getDepth(spanId) {
            if (depthMap.has(spanId)) return depthMap.get(spanId);
            const span = spanMap.get(spanId);
            if (!span || !span.parent_span_id) {
                depthMap.set(spanId, 0);
                return 0;
            }
            const d = getDepth(span.parent_span_id) + 1;
            depthMap.set(spanId, d);
            return d;
        }

        spans.forEach(s => getDepth(s.span_id));

        // Sort: by start time, then depth for visual nesting
        spans.sort((a, b) => {
            const startDiff = new Date(a.start_time).getTime() - new Date(b.start_time).getTime();
            if (startDiff !== 0) return startDiff;
            return (depthMap.get(a.span_id) || 0) - (depthMap.get(b.span_id) || 0);
        });

        // Calculate total duration
        let maxEnd = minStart;
        spans.forEach(s => {
            const end = s.end_time
                ? new Date(s.end_time).getTime()
                : new Date(s.start_time).getTime() + (s.duration_ms || 0);
            if (end > maxEnd) maxEnd = end;
        });

        const total = Math.max(maxEnd - minStart, 1);

        const rows = spans.map(span => {
            const start = new Date(span.start_time).getTime() - minStart;
            const duration = span.duration_ms || (span.end_time
                ? new Date(span.end_time).getTime() - new Date(span.start_time).getTime()
                : 0);
            const depth = depthMap.get(span.span_id) || 0;

            return {
                span,
                depth,
                offsetPct: (start / total) * 100,
                widthPct: Math.max((duration / total) * 100, 0.5), // min 0.5% for visibility
                duration,
            };
        });

        return { rows, totalDuration: total, traceStart: minStart };
    }, [trace]);

    if (!trace) {
        return (
            <div className="timeline-empty">
                <div className="timeline-empty-text">No trace selected</div>
                <div className="timeline-empty-hint">Select a trace to view the timeline</div>
            </div>
        );
    }

    if (!rows.length) {
        return (
            <div className="timeline-empty">
                <div className="timeline-empty-text">No spans in this trace</div>
            </div>
        );
    }

    // Time axis markers
    const markers = [];
    const markerCount = 5;
    for (let i = 0; i <= markerCount; i++) {
        const pct = (i / markerCount) * 100;
        const timeMs = (i / markerCount) * totalDuration;
        markers.push({ pct, label: formatDuration(timeMs) });
    }

    return (
        <div className="timeline-container">
            {/* Header */}
            <div className="timeline-header">
                <div className="timeline-header-label">Span</div>
                <div className="timeline-header-bar">
                    {markers.map((m, i) => (
                        <span
                            key={i}
                            className="timeline-marker"
                            style={{ left: `${m.pct}%` }}
                        >
                            {m.label}
                        </span>
                    ))}
                </div>
                <div className="timeline-header-duration">Duration</div>
            </div>

            {/* Rows */}
            <div className="timeline-rows">
                {rows.map(({ span, depth, offsetPct, widthPct, duration }) => {
                    const colors = KIND_COLORS[span.kind] || KIND_COLORS.internal;
                    const isError = span.status === 'error';

                    return (
                        <div
                            key={span.span_id}
                            className={`timeline-row ${isError ? 'error' : ''} ${span.status === 'running' ? 'running' : ''}`}
                            onClick={() => onSpanClick?.(span)}
                            title={`${span.name} (${span.kind}) — ${formatDuration(duration)}`}
                        >
                            {/* Label */}
                            <div className="timeline-row-label" style={{ paddingLeft: `${12 + depth * 16}px` }}>
                                <span
                                    className="timeline-kind-dot"
                                    style={{ background: colors.bg, borderColor: colors.border }}
                                />
                                <span className="timeline-span-name">{span.name}</span>
                                <span className="timeline-span-kind">{span.kind}</span>
                            </div>

                            {/* Bar */}
                            <div className="timeline-row-bar">
                                {/* Grid lines */}
                                {markers.map((m, i) => (
                                    <div
                                        key={i}
                                        className="timeline-grid-line"
                                        style={{ left: `${m.pct}%` }}
                                    />
                                ))}

                                <div
                                    className={`timeline-bar ${isError ? 'error' : ''} ${span.status === 'running' ? 'running' : ''}`}
                                    style={{
                                        left: `${offsetPct}%`,
                                        width: `${widthPct}%`,
                                        background: isError
                                            ? 'linear-gradient(90deg, rgba(239, 68, 68, 0.8), rgba(185, 28, 28, 0.8))'
                                            : `linear-gradient(90deg, ${colors.bg}, ${colors.border})`,
                                        borderColor: isError ? '#ef4444' : colors.border,
                                    }}
                                >
                                    {widthPct > 8 && (
                                        <span className="timeline-bar-label">{formatDuration(duration)}</span>
                                    )}
                                </div>
                            </div>

                            {/* Duration */}
                            <div className="timeline-row-duration">
                                {formatDuration(duration)}
                            </div>
                        </div>
                    );
                })}
            </div>

            {/* Summary */}
            <div className="timeline-summary">
                <span>Total: {formatDuration(totalDuration)}</span>
                <span>{rows.length} spans</span>
                <div className="timeline-legend">
                    {Object.entries(KIND_COLORS).slice(0, 4).map(([kind, colors]) => (
                        <span key={kind} className="timeline-legend-item">
                            <span className="timeline-legend-dot" style={{ background: colors.bg }} />
                            {kind}
                        </span>
                    ))}
                </div>
            </div>
        </div>
    );
}
