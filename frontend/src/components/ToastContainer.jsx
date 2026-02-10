import './ToastContainer.css';

/**
 * Toast notification container — renders toast stack at bottom-right.
 */
export default function ToastContainer({ toasts, onDismiss }) {
    if (!toasts.length) return null;

    return (
        <div className="toast-container" role="alert" aria-live="polite">
            {toasts.map((toast) => (
                <div
                    key={toast.id}
                    className={`toast toast-${toast.type}`}
                    data-animate="enter"
                >
                    <span className="toast-icon">
                        {toast.type === 'success' && '✓'}
                        {toast.type === 'error' && '✕'}
                        {toast.type === 'warning' && '⚠'}
                        {toast.type === 'info' && 'ℹ'}
                    </span>
                    <span className="toast-message">{toast.message}</span>
                    <button
                        className="toast-dismiss"
                        onClick={() => onDismiss(toast.id)}
                        aria-label="Dismiss notification"
                    >
                        ×
                    </button>
                </div>
            ))}
        </div>
    );
}
