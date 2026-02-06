import { memo } from 'react';
import { Handle, Position } from 'reactflow';
import './TraceGraph.css';

const ToolNode = memo(({ data }) => {
    const { name, status, input, output, error } = data;

    const getStatusClass = () => {
        switch (status) {
            case 'running': return 'status-running';
            case 'success': return 'status-success';
            case 'error': return 'status-error';
            default: return '';
        }
    };

    return (
        <div className={`tool-node ${getStatusClass()}`}>
            <Handle type="target" position={Position.Top} />

            <div className="node-header">
                <div className="node-icon tool-icon">🔧</div>
                <div className="node-title">{name}</div>
            </div>

            {error && (
                <div className="node-error">
                    <span className="error-icon">⚠️</span>
                    <span className="error-text">{error}</span>
                </div>
            )}

            <Handle type="source" position={Position.Bottom} />
        </div>
    );
});

ToolNode.displayName = 'ToolNode';

export default ToolNode;
