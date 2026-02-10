import { useMemo } from 'react';
import { Coins, Cpu, Hash, Wrench } from '../icons/AppIcons';
import {
    PieChart,
    Pie,
    Cell,
    BarChart,
    Bar,
    XAxis,
    YAxis,
    Tooltip,
    ResponsiveContainer,
} from 'recharts';
import './TokenMonitor.css';

const COLORS = ['#6366f1', '#8b5cf6', '#10b981', '#3b82f6', '#f59e0b', '#ef4444'];

export default function TokenMonitor({ trace }) {
    const metrics = useMemo(() => {
        if (!trace?.spans) return null;

        const agentData = {};
        let totalTokens = 0;
        let totalCost = 0;
        let llmCalls = 0;
        let toolCalls = 0;

        trace.spans.forEach(span => {
            totalTokens += span.total_tokens || 0;
            totalCost += span.cost_usd || 0;

            if (span.kind === 'llm') llmCalls++;
            if (span.kind === 'tool') toolCalls++;

            const agentName = span.agent_name || 'Unknown';
            if (!agentData[agentName]) {
                agentData[agentName] = { name: agentName, tokens: 0, cost: 0, calls: 0 };
            }
            agentData[agentName].tokens += span.total_tokens || 0;
            agentData[agentName].cost += span.cost_usd || 0;
            agentData[agentName].calls += 1;
        });

        return {
            totalTokens,
            totalCost,
            llmCalls,
            toolCalls,
            agentBreakdown: Object.values(agentData),
        };
    }, [trace]);

    if (!trace || !metrics) {
        return (
            <div className="token-monitor empty">
                <div className="empty-text">No metrics available</div>
            </div>
        );
    }

    const formatPercent = (value) => {
        if (!metrics.totalTokens) return '0%';
        return `${((value / metrics.totalTokens) * 100).toFixed(0)}%`;
    };

    const renderTooltip = ({ active, payload, label }) => {
        if (!active || !payload || payload.length === 0) return null;
        const entry = payload[0];
        const name = entry?.payload?.name || label || entry.name;
        const value = Number(entry?.value || 0);
        const metricLabel = entry.name?.toLowerCase().includes('cost') ? 'Cost' : 'Tokens';
        return (
            <div className="token-tooltip" role="tooltip">
                <div className="token-tooltip-label">{name}</div>
                <div className="token-tooltip-value">
                    {metricLabel === 'Cost' ? `$${value.toFixed(4)}` : value.toLocaleString()} {metricLabel}
                </div>
            </div>
        );
    };

    return (
        <div className="token-monitor">
            {/* Summary Cards */}
            <div className="metrics-summary">
                <div className="metric-card" data-animate="enter" data-delay="1">
                    <Hash className="ui-icon metric-icon" />
                    <div className="metric-content">
                        <div className="metric-value">{metrics.totalTokens.toLocaleString()}</div>
                        <div className="metric-label">Total Tokens</div>
                    </div>
                </div>
                <div className="metric-card" data-animate="enter" data-delay="2">
                    <Coins className="ui-icon metric-icon" />
                    <div className="metric-content">
                        <div className="metric-value">${metrics.totalCost.toFixed(4)}</div>
                        <div className="metric-label">Total Cost</div>
                    </div>
                </div>
                <div className="metric-card" data-animate="enter" data-delay="3">
                    <Cpu className="ui-icon metric-icon" />
                    <div className="metric-content">
                        <div className="metric-value">{metrics.llmCalls}</div>
                        <div className="metric-label">LLM Calls</div>
                    </div>
                </div>
                <div className="metric-card" data-animate="enter" data-delay="1">
                    <Wrench className="ui-icon metric-icon" />
                    <div className="metric-content">
                        <div className="metric-value">{metrics.toolCalls}</div>
                        <div className="metric-label">Tool Calls</div>
                    </div>
                </div>
            </div>

            {/* Agent Cost Breakdown */}
            {metrics.agentBreakdown.length > 0 && (
                <div className="chart-section" data-animate="enter" data-delay="2">
                    <h3 className="section-title">Token Distribution by Agent</h3>
                    <div className="chart-container">
                        <ResponsiveContainer width="100%" height={220}>
                            <PieChart>
                                <Pie
                                    data={metrics.agentBreakdown}
                                    dataKey="tokens"
                                    nameKey="name"
                                    cx="50%"
                                    cy="48%"
                                    outerRadius={78}
                                    innerRadius={46}
                                    paddingAngle={3}
                                    labelLine={false}
                                >
                                    {metrics.agentBreakdown.map((entry, index) => (
                                        <Cell
                                            key={entry.name}
                                            fill={COLORS[index % COLORS.length]}
                                            stroke="#FDFCF8"
                                            strokeWidth={2}
                                        />
                                    ))}
                                </Pie>
                                <Tooltip
                                    content={renderTooltip}
                                    cursor={{ fill: 'rgba(249, 115, 22, 0.12)' }}
                                />
                            </PieChart>
                        </ResponsiveContainer>
                    </div>
                    <div className="chart-legend">
                        {metrics.agentBreakdown.map((entry, index) => (
                            <div key={entry.name} className="legend-item">
                                <span
                                    className="legend-dot"
                                    style={{ backgroundColor: COLORS[index % COLORS.length] }}
                                />
                                <span className="legend-name">{entry.name}</span>
                                <span className="legend-meta">
                                    {entry.tokens.toLocaleString()} tokens ({formatPercent(entry.tokens)})
                                </span>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Cost Bar Chart */}
            {metrics.agentBreakdown.length > 0 && (
                <div className="chart-section" data-animate="enter" data-delay="3">
                    <h3 className="section-title">Cost by Agent</h3>
                    <div className="chart-container">
                        <ResponsiveContainer width="100%" height={150}>
                            <BarChart
                                data={metrics.agentBreakdown}
                                layout="vertical"
                                margin={{ top: 8, right: 8, left: 0, bottom: 0 }}
                            >
                                <XAxis
                                    type="number"
                                    tickFormatter={(v) => `$${v.toFixed(3)}`}
                                    stroke="#64748b"
                                    tick={{ fill: '#94a3b8', fontSize: 11 }}
                                />
                                <YAxis
                                    type="category"
                                    dataKey="name"
                                    width={130}
                                    stroke="#64748b"
                                    tick={{ fill: '#cbd5e1', fontSize: 11 }}
                                />
                                <Tooltip
                                    content={renderTooltip}
                                />
                                <Bar dataKey="cost" fill="#F97316" radius={[0, 4, 4, 0]} />
                            </BarChart>
                        </ResponsiveContainer>
                    </div>
                </div>
            )}

            {/* Burn Rate Indicator */}
            {trace.duration_ms > 0 && (
                <div className="burn-rate" data-animate="enter" data-delay="2">
                    <div className="burn-rate-title">Burn Rate</div>
                    <div className="burn-rate-value">
                        {((metrics.totalTokens / (trace.duration_ms / 1000)) * 60).toFixed(0)} tokens/min
                    </div>
                    <div className="burn-rate-cost">
                        ${((metrics.totalCost / (trace.duration_ms / 1000)) * 60).toFixed(4)}/min
                    </div>
                </div>
            )}
        </div>
    );
}
