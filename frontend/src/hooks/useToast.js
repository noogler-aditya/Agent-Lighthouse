import { useState, useCallback, useRef, useEffect } from 'react';

/**
 * Toast notification hook — enterprise-grade notification system.
 * Supports success, error, warning, info types with auto-dismiss.
 */

let toastId = 0;

export function useToast() {
    const [toasts, setToasts] = useState([]);
    const timersRef = useRef(new Map());

    const removeToast = useCallback((id) => {
        setToasts(prev => prev.filter(t => t.id !== id));
        const timer = timersRef.current.get(id);
        if (timer) {
            clearTimeout(timer);
            timersRef.current.delete(id);
        }
    }, []);

    const addToast = useCallback((message, type = 'info', duration = 4000) => {
        const id = ++toastId;
        setToasts(prev => [...prev, { id, message, type, entering: true }]);

        // Auto-dismiss
        if (duration > 0) {
            const timer = setTimeout(() => removeToast(id), duration);
            timersRef.current.set(id, timer);
        }

        return id;
    }, [removeToast]);

    const success = useCallback((msg) => addToast(msg, 'success'), [addToast]);
    const error = useCallback((msg) => addToast(msg, 'error', 6000), [addToast]);
    const warning = useCallback((msg) => addToast(msg, 'warning', 5000), [addToast]);
    const info = useCallback((msg) => addToast(msg, 'info'), [addToast]);

    // Cleanup on unmount
    useEffect(() => {
        const currentTimers = timersRef.current;
        return () => {
            currentTimers.forEach(timer => clearTimeout(timer));
        };
    }, []);

    return { toasts, addToast, removeToast, success, error, warning, info };
}
