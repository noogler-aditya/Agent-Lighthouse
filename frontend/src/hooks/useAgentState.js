import { useState, useCallback } from 'react';

const API_URL = 'http://localhost:8000/api';

export function useAgentState(traceId) {
    const [state, setState] = useState(null);
    const [controlStatus, setControlStatus] = useState('unknown');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    const fetchState = useCallback(async () => {
        if (!traceId) return;
        setLoading(true);
        try {
            const res = await fetch(`${API_URL}/state/${traceId}`);
            if (res.ok) {
                const data = await res.json();
                setState(data);
                setControlStatus(data.control?.status || 'unknown');
            }
            setError(null);
        } catch (e) {
            setError(e.message);
        } finally {
            setLoading(false);
        }
    }, [traceId]);

    const modifyState = useCallback(async (path, value) => {
        if (!traceId) return;
        try {
            const res = await fetch(`${API_URL}/state/${traceId}`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ path, value }),
            });
            if (!res.ok) throw new Error('Failed to modify state');
            await fetchState();
        } catch (e) {
            setError(e.message);
        }
    }, [traceId, fetchState]);

    const bulkModifyState = useCallback(async (updates) => {
        if (!traceId) return;
        try {
            const res = await fetch(`${API_URL}/state/${traceId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(updates),
            });
            if (!res.ok) throw new Error('Failed to update state');
            await fetchState();
        } catch (e) {
            setError(e.message);
        }
    }, [traceId, fetchState]);

    const pause = useCallback(async () => {
        if (!traceId) return;
        try {
            await fetch(`${API_URL}/state/${traceId}/pause`, { method: 'POST' });
            setControlStatus('paused');
        } catch (e) {
            setError(e.message);
        }
    }, [traceId]);

    const resume = useCallback(async () => {
        if (!traceId) return;
        try {
            await fetch(`${API_URL}/state/${traceId}/resume`, { method: 'POST' });
            setControlStatus('running');
        } catch (e) {
            setError(e.message);
        }
    }, [traceId]);

    const step = useCallback(async (count = 1) => {
        if (!traceId) return;
        try {
            await fetch(`${API_URL}/state/${traceId}/step`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ count }),
            });
            setControlStatus('step');
        } catch (e) {
            setError(e.message);
        }
    }, [traceId]);

    return {
        state,
        controlStatus,
        loading,
        error,
        fetchState,
        modifyState,
        bulkModifyState,
        pause,
        resume,
        step,
        setControlStatus,
    };
}
