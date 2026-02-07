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

    return (
        <div className="token-monitor">
            {/* Summary Cards */}
            <div className="metrics-summary">
                <div className="metric-card">
                    <Hash className="ui-icon metric-icon" />
                    <div className="metric-content">
                        <div className="metric-value">{metrics.totalTokens.toLocaleString()}</div>
                        <div className="metric-label">Total Tokens</div>
                    </div>
                </div>
                <div className="metric-card">
                    <Coins className="ui-icon metric-icon" />
                    <div className="metric-content">
                        <div className="metric-value">${metrics.totalCost.toFixed(4)}</div>
                        <div className="metric-label">Total Cost</div>
                    </div>
                </div>
                <div className="metric-card">
                    <Cpu className="ui-icon metric-icon" />
                    <div className="metric-content">
                        <div className="metric-value">{metrics.llmCalls}</div>
                        <div className="metric-label">LLM Calls</div>
                    </div>
                </div>
                <div className="metric-card">
                    <Wrench className="ui-icon metric-icon" />
                    <div className="metric-content">
                        <div className="metric-value">{metrics.toolCalls}</div>
                        <div className="metric-label">Tool Calls</div>
                    </div>
                </div>
            </div>

            {/* Agent Cost Breakdown */}
            {metrics.agentBreakdown.length > 0 && (
                <div className="chart-section">
                    <h3 className="section-title">Token Distribution by Agent</h3>
                    <div className="chart-container">
                        <ResponsiveContainer width="100%" height={200}>
                            <PieChart>
                                <Pie
                                    data={metrics.agentBreakdown}
                                    dataKey="tokens"
                                    nameKey="name"
                                    cx="50%"
                                    cy="50%"
                                    outerRadius={70}
                                    innerRadius={40}
                                    paddingAngle={2}
                                    label={({ name, percent }) => `${name} (${(percent * 100).toFixed(0)}%)`}
                                    labelLine={false}
                                >
                                    {metrics.agentBreakdown.map((entry, index) => (
                                        <Cell key={entry.name} fill={COLORS[index % COLORS.length]} />
                                    ))}
                                </Pie>
                                <Tooltip
                                    contentStyle={{
                                        background: '#1a1a26',
                                        border: '1px solid #2d2d3d',
                                        borderRadius: '8px',
                                    }}
                                    formatter={(value) => [value.toLocaleString(), 'Tokens']}
                                />
                            </PieChart>
                        </ResponsiveContainer>
                    </div>
                </div>
            )}

            {/* Cost Bar Chart */}
            {metrics.agentBreakdown.length > 0 && (
                <div className="chart-section">
                    <h3 className="section-title">Cost by Agent</h3>
                    <div className="chart-container">
                        <ResponsiveContainer width="100%" height={150}>
                            <BarChart data={metrics.agentBreakdown} layout="vertical">
                                <XAxis type="number" tickFormatter={(v) => `$${v.toFixed(3)}`} stroke="#64748b" />
                                <YAxis type="category" dataKey="name" width={80} stroke="#64748b" />
                                <Tooltip
                                    contentStyle={{
                                        background: '#1a1a26',
                                        border: '1px solid #2d2d3d',
                                        borderRadius: '8px',
                                    }}
                                    formatter={(value) => [`$${value.toFixed(4)}`, 'Cost']}
                                />
                                <Bar dataKey="cost" fill="#6366f1" radius={[0, 4, 4, 0]} />
                            </BarChart>
                        </ResponsiveContainer>
                    </div>
                </div>
            )}

            {/* Burn Rate Indicator */}
            {trace.duration_ms > 0 && (
                <div className="burn-rate">
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
