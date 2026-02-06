import { memo } from 'react';
import { Handle, Position } from 'reactflow';
import './TraceGraph.css';

const AgentNode = memo(({ data }) => {
    const { name, status, tokens, cost, duration } = data;

    const getStatusClass = () => {
        switch (status) {
            case 'running': return 'status-running';
            case 'success': return 'status-success';
            case 'error': return 'status-error';
            default: return '';
        }
    };

    return (
        <div className={`agent-node ${getStatusClass()}`}>
            <Handle type="target" position={Position.Top} />

            <div className="node-header">
                <div className="node-icon agent-icon">🤖</div>
                <div className="node-title">{name}</div>
            </div>

            <div className="node-metrics">
                <div className="metric">
                    <span className="metric-label">Tokens</span>
                    <span className="metric-value">{tokens?.toLocaleString() || 0}</span>
                </div>
                <div className="metric">
                    <span className="metric-label">Cost</span>
                    <span className="metric-value">${cost?.toFixed(4) || '0.00'}</span>
                </div>
                {duration && (
                    <div className="metric">
                        <span className="metric-label">Time</span>
                        <span className="metric-value">{duration.toFixed(0)}ms</span>
                    </div>
                )}
            </div>

            <Handle type="source" position={Position.Bottom} />
        </div>
    );
});

AgentNode.displayName = 'AgentNode';

export default AgentNode;
