import { memo } from 'react';
import { Handle, Position } from 'reactflow';
import { Cpu } from '../icons/AppIcons';
import './TraceGraph.css';

const LLMNode = memo(({ data }) => {
    const { name, model, promptTokens, completionTokens, cost, status } = data;

    const getStatusClass = () => {
        switch (status) {
            case 'running': return 'status-running';
            case 'success': return 'status-success';
            case 'error': return 'status-error';
            default: return '';
        }
    };

    return (
        <div className={`llm-node ${getStatusClass()}`}>
            <Handle type="target" position={Position.Top} />

            <div className="node-header">
                <Cpu className="ui-icon node-icon llm-icon" />
                <div className="node-title">{name || 'LLM Call'}</div>
            </div>

            {model && (
                <div className="node-model">{model}</div>
            )}

            <div className="node-metrics">
                <div className="metric">
                    <span className="metric-label">In</span>
                    <span className="metric-value">{promptTokens?.toLocaleString() || 0}</span>
                </div>
                <div className="metric">
                    <span className="metric-label">Out</span>
                    <span className="metric-value">{completionTokens?.toLocaleString() || 0}</span>
                </div>
                <div className="metric">
                    <span className="metric-label">Cost</span>
                    <span className="metric-value">${cost?.toFixed(4) || '0.00'}</span>
                </div>
            </div>

            <Handle type="source" position={Position.Bottom} />
        </div>
    );
});

LLMNode.displayName = 'LLMNode';

export default LLMNode;
