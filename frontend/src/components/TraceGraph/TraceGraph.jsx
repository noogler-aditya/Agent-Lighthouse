import { useCallback, useMemo, useEffect, useState } from 'react';
import ReactFlow, {
    Background,
    Controls,
    MiniMap,
    useNodesState,
    useEdgesState,
} from 'reactflow';
import 'reactflow/dist/style.css';
import './TraceGraph.css';

import AgentNode from './AgentNode';
import ToolNode from './ToolNode';
import LLMNode from './LLMNode';

const nodeTypes = {
    agent: AgentNode,
    tool: ToolNode,
    llm: LLMNode,
};

// Convert spans to React Flow nodes and edges
function spansToGraph(spans) {
    if (!spans || spans.length === 0) return { nodes: [], edges: [] };

    const nodes = [];
    const edges = [];
    const positions = new Map();
    const levelCounts = new Map();

    // Calculate depth for each span
    const depths = new Map();
    const spanMap = new Map(spans.map(s => [s.span_id, s]));

    function getDepth(spanId) {
        if (depths.has(spanId)) return depths.get(spanId);
        const span = spanMap.get(spanId);
        if (!span || !span.parent_span_id) {
            depths.set(spanId, 0);
            return 0;
        }
        const parentDepth = getDepth(span.parent_span_id);
        depths.set(spanId, parentDepth + 1);
        return parentDepth + 1;
    }

    // Calculate depths
    spans.forEach(s => getDepth(s.span_id));

    // Group by depth for horizontal positioning
    spans.forEach(span => {
        const depth = depths.get(span.span_id);
        const count = levelCounts.get(depth) || 0;
        levelCounts.set(depth, count + 1);
        positions.set(span.span_id, { depth, index: count });
    });

    // Create nodes
    spans.forEach(span => {
        const pos = positions.get(span.span_id);
        const levelWidth = levelCounts.get(pos.depth);
        const xOffset = (pos.index - (levelWidth - 1) / 2) * 250;

        const nodeType = span.kind === 'agent' ? 'agent' :
            span.kind === 'llm' ? 'llm' : 'tool';

        nodes.push({
            id: span.span_id,
            type: nodeType,
            position: { x: 400 + xOffset, y: pos.depth * 180 + 50 },
            data: {
                name: span.name,
                status: span.status,
                tokens: span.total_tokens,
                promptTokens: span.prompt_tokens,
                completionTokens: span.completion_tokens,
                cost: span.cost_usd,
                duration: span.duration_ms,
                model: span.attributes?.model,
                error: span.error_message,
            },
        });

        // Create edge from parent
        if (span.parent_span_id) {
            edges.push({
                id: `${span.parent_span_id}-${span.span_id}`,
                source: span.parent_span_id,
                target: span.span_id,
                animated: span.status === 'running',
                style: {
                    stroke: span.status === 'error' ? '#ef4444' : undefined
                },
            });
        }
    });

    return { nodes, edges };
}

export default function TraceGraph({ trace, onSpanClick }) {
    const [nodes, setNodes, onNodesChange] = useNodesState([]);
    const [edges, setEdges, onEdgesChange] = useEdgesState([]);

    // Update graph when trace changes
    useEffect(() => {
        if (trace?.spans) {
            const { nodes: newNodes, edges: newEdges } = spansToGraph(trace.spans);
            setNodes(newNodes);
            setEdges(newEdges);
        } else {
            setNodes([]);
            setEdges([]);
        }
    }, [trace, setNodes, setEdges]);

    const onNodeClick = useCallback((event, node) => {
        if (onSpanClick) {
            const span = trace?.spans?.find(s => s.span_id === node.id);
            onSpanClick(span);
        }
    }, [trace, onSpanClick]);

    if (!trace) {
        return (
            <div className="trace-graph-empty">
                <div className="empty-icon">🔍</div>
                <div className="empty-text">No trace selected</div>
                <div className="empty-hint">Select a trace from the sidebar to visualize</div>
            </div>
        );
    }

    return (
        <div className="trace-graph-container">
            <ReactFlow
                nodes={nodes}
                edges={edges}
                onNodesChange={onNodesChange}
                onEdgesChange={onEdgesChange}
                onNodeClick={onNodeClick}
                nodeTypes={nodeTypes}
                fitView
                fitViewOptions={{ padding: 0.2 }}
                minZoom={0.1}
                maxZoom={2}
            >
                <Background color="#2d2d3d" gap={20} />
                <Controls />
                <MiniMap
                    nodeColor={(node) => {
                        switch (node.type) {
                            case 'agent': return '#6366f1';
                            case 'llm': return '#8b5cf6';
                            case 'tool': return '#10b981';
                            default: return '#64748b';
                        }
                    }}
                    maskColor="rgba(0, 0, 0, 0.7)"
                />
            </ReactFlow>
        </div>
    );
}
