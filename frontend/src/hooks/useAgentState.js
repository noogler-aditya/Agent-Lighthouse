import { useState, useCallback } from 'react';
import { API_HEADERS, API_URL } from '../config';

export function useAgentState(traceId) {
    const [state, setState] = useState(null);
    const [controlStatus, setControlStatus] = useState('unknown');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    const fetchState = useCallback(async () => {
        if (!traceId) return;
        setLoading(true);
        try {
            const res = await fetch(`${API_URL}/state/${traceId}`, { headers: API_HEADERS });
            if (res.ok) {
                const data = await res.json();
                setState(data);
                setControlStatus(data.control?.status || 'unknown');
            } else if (res.status === 404) {
                setState(null);
                setControlStatus('unknown');
            } else {
                throw new Error('Failed to fetch state');
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
                headers: { ...API_HEADERS, 'Content-Type': 'application/json' },
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
                headers: { ...API_HEADERS, 'Content-Type': 'application/json' },
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
            const response = await fetch(`${API_URL}/state/${traceId}/pause`, {
                method: 'POST',
                headers: API_HEADERS,
            });
            if (!response.ok) throw new Error('Failed to pause execution');
            setControlStatus('paused');
        } catch (e) {
            setError(e.message);
        }
    }, [traceId]);

    const resume = useCallback(async () => {
        if (!traceId) return;
        try {
            const response = await fetch(`${API_URL}/state/${traceId}/resume`, {
                method: 'POST',
                headers: API_HEADERS,
            });
            if (!response.ok) throw new Error('Failed to resume execution');
            setControlStatus('running');
        } catch (e) {
            setError(e.message);
        }
    }, [traceId]);

    const step = useCallback(async (count = 1) => {
        if (!traceId) return;
        try {
            const response = await fetch(`${API_URL}/state/${traceId}/step`, {
                method: 'POST',
                headers: { ...API_HEADERS, 'Content-Type': 'application/json' },
                body: JSON.stringify({ count }),
            });
            if (!response.ok) throw new Error('Failed to step execution');
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
