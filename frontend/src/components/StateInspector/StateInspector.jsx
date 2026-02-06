import { useState, useEffect } from 'react';
import Editor from '@monaco-editor/react';
import './StateInspector.css';

export default function StateInspector({
    traceId,
    state,
    controlStatus,
    onPause,
    onResume,
    onStep,
    onModifyState,
    loading
}) {
    const [activeTab, setActiveTab] = useState('memory');
    const [editMode, setEditMode] = useState(false);
    const [editedValue, setEditedValue] = useState('');

    const getContent = () => {
        if (!state) return null;
        switch (activeTab) {
            case 'memory': return state.memory;
            case 'context': return state.context;
            case 'variables': return state.variables;
            case 'messages': return state.messages;
            default: return null;
        }
    };

    const content = getContent();

    useEffect(() => {
        if (content && editMode) {
            setEditedValue(JSON.stringify(content, null, 2));
        }
    }, [content, editMode]);

    const handleSave = () => {
        try {
            const parsed = JSON.parse(editedValue);
            onModifyState?.({ [activeTab]: parsed });
            setEditMode(false);
        } catch (e) {
            alert('Invalid JSON');
        }
    };

    if (!traceId) {
        return (
            <div className="state-inspector empty">
                <div className="empty-text">Select a trace to inspect state</div>
            </div>
        );
    }

    return (
        <div className="state-inspector">
            {/* Execution Controls */}
            <div className="control-panel">
                <div className="control-status">
                    <span className={`status-badge ${controlStatus}`}>
                        {controlStatus === 'running' ? 'Running' :
                            controlStatus === 'paused' ? 'Paused' :
                                controlStatus === 'step' ? 'Stepping' : 'Unknown'}
                    </span>
                </div>
                <div className="control-buttons">
                    <button
                        className="btn btn-warning btn-icon"
                        onClick={onPause}
                        disabled={controlStatus === 'paused'}
                        title="Pause"
                    >
                        ⏸
                    </button>
                    <button
                        className="btn btn-success btn-icon"
                        onClick={onResume}
                        disabled={controlStatus === 'running'}
                        title="Resume"
                    >
                        ▶
                    </button>
                    <button
                        className="btn btn-secondary btn-icon"
                        onClick={() => onStep?.(1)}
                        title="Step"
                    >
                        ⏭
                    </button>
                </div>
            </div>

            {/* State Tabs */}
            <div className="state-tabs">
                <div className="tabs">
                    {['memory', 'context', 'variables', 'messages'].map(tab => (
                        <button
                            key={tab}
                            className={`tab ${activeTab === tab ? 'active' : ''}`}
                            onClick={() => {
                                setActiveTab(tab);
                                setEditMode(false);
                            }}
                        >
                            {tab.charAt(0).toUpperCase() + tab.slice(1)}
                        </button>
                    ))}
                </div>
            </div>

            {/* State Content */}
            <div className="state-content">
                {loading ? (
                    <div className="loading">Loading...</div>
                ) : !state ? (
                    <div className="no-state">
                        <p>No state available</p>
                        <p className="hint">State is captured when the agent is paused</p>
                    </div>
                ) : editMode ? (
                    <div className="editor-container">
                        <Editor
                            height="100%"
                            defaultLanguage="json"
                            value={editedValue}
                            onChange={setEditedValue}
                            theme="vs-dark"
                            options={{
                                minimap: { enabled: false },
                                fontSize: 12,
                                lineNumbers: 'off',
                                scrollBeyondLastLine: false,
                                wordWrap: 'on',
                                padding: { top: 8 },
                            }}
                        />
                    </div>
                ) : (
                    <div className="json-viewer">
                        <pre>{JSON.stringify(content, null, 2)}</pre>
                    </div>
                )}
            </div>

            {/* Edit Actions */}
            <div className="state-actions">
                {editMode ? (
                    <>
                        <button className="btn btn-secondary" onClick={() => setEditMode(false)}>
                            Cancel
                        </button>
                        <button className="btn btn-primary" onClick={handleSave}>
                            Save Changes
                        </button>
                    </>
                ) : (
                    <button
                        className="btn btn-secondary"
                        onClick={() => setEditMode(true)}
                        disabled={!state || controlStatus === 'running'}
                    >
                        ✏️ Edit State
                    </button>
                )}
            </div>

            {/* Snapshots */}
            {state?.snapshots?.length > 0 && (
                <div className="snapshots-section">
                    <h4 className="section-title">State Snapshots</h4>
                    <div className="snapshots-list">
                        {state.snapshots.map((snap, idx) => (
                            <div key={snap.snapshot_id} className="snapshot-item">
                                <span className="snapshot-index">#{idx + 1}</span>
                                <span className="snapshot-time">
                                    {new Date(snap.timestamp).toLocaleTimeString()}
                                </span>
                                {snap.description && (
                                    <span className="snapshot-desc">{snap.description}</span>
                                )}
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
}
