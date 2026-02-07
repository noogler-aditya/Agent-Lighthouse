import { memo } from 'react';
import { Handle, Position } from 'reactflow';
import { TriangleAlert, Wrench } from '../icons/AppIcons';
import './TraceGraph.css';

const ToolNode = memo(({ data }) => {
    const { name, status, error } = data;

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
                <Wrench className="ui-icon node-icon tool-icon" />
                <div className="node-title">{name}</div>
            </div>

            {error && (
                <div className="node-error">
                    <TriangleAlert className="ui-icon ui-icon-xs error-icon" />
                    <span className="error-text">{error}</span>
                </div>
            )}

            <Handle type="source" position={Position.Bottom} />
        </div>
    );
});

ToolNode.displayName = 'ToolNode';

export default ToolNode;
