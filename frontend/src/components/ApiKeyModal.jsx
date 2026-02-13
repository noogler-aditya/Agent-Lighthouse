import { useState } from 'react';
import { Hash } from './icons/AppIcons';

export function ApiKeyModal({ isOpen, apiKey, loading, error, onClose, onFetch }) {
  const [copyStatus, setCopyStatus] = useState('');

  const handleCopy = async () => {
    if (!apiKey) return;
    try {
      await navigator.clipboard.writeText(apiKey);
      setCopyStatus('Copied to clipboard');
    } catch {
      setCopyStatus('Copy failed');
    }
    setTimeout(() => setCopyStatus(''), 1800);
  };

  if (!isOpen) return null;

  return (
    <div className="api-key-overlay" onClick={onClose}>
      <div className="api-key-modal" onClick={(e) => e.stopPropagation()}>
        <div className="api-key-header">
          <div className="api-key-icon">
            <Hash className="ui-icon" />
          </div>
          <h2>Your API key</h2>
          <p>Use this key to authenticate agents that send traces to this workspace.</p>
        </div>

        <div className="api-key-body">
          {apiKey ? (
            <div className="api-key-row">
              <input type="text" value={apiKey} readOnly />
              <button className="btn btn-secondary btn-sm" onClick={handleCopy}>
                Copy
              </button>
            </div>
          ) : (
            <div className="api-key-empty">
              <p>No API key loaded yet.</p>
              <button className="btn btn-primary btn-sm" onClick={onFetch} disabled={loading}>
                {loading ? 'Fetching...' : 'Fetch API key'}
              </button>
            </div>
          )}

          {copyStatus && <div className="api-key-note">{copyStatus}</div>}
          {error && <div className="api-key-error">{error}</div>}
        </div>

        <div className="api-key-actions">
          <button className="btn btn-secondary" onClick={onClose}>
            Close
          </button>
          {!apiKey && (
            <button className="btn btn-primary" onClick={onFetch} disabled={loading}>
              {loading ? 'Fetching...' : 'Fetch API key'}
            </button>
          )}
        </div>
      </div>

      <style>{`
        .api-key-overlay {
          position: fixed;
          inset: 0;
          background: rgba(8, 12, 20, 0.5);
          backdrop-filter: blur(8px);
          display: flex;
          align-items: center;
          justify-content: center;
          z-index: 9999;
          animation: fade-in 0.2s ease-out;
        }

        .api-key-modal {
          width: min(520px, 92vw);
          background: var(--bg-primary);
          border: 1px solid var(--border-primary);
          border-radius: 20px;
          padding: 28px;
          box-shadow: var(--shadow-lg), 0 20px 40px rgba(0,0,0,0.2);
          animation: slide-up 0.3s var(--ease-emphasized);
        }

        .api-key-header {
          display: grid;
          gap: 10px;
          margin-bottom: 20px;
        }

        .api-key-icon {
          width: 48px;
          height: 48px;
          display: grid;
          place-items: center;
          border-radius: 14px;
          background: rgba(99, 102, 241, 0.15);
          color: #6366f1;
        }

        .api-key-body {
          display: grid;
          gap: 12px;
        }

        .api-key-row {
          display: grid;
          grid-template-columns: 1fr auto;
          gap: 10px;
        }

        .api-key-row input {
          width: 100%;
          padding: 10px 12px;
          border-radius: 12px;
          border: 1px solid var(--border-primary);
          background: var(--bg-secondary);
          color: var(--text-primary);
          font-family: 'SFMono-Regular', ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace;
          font-size: 12px;
        }

        .api-key-empty {
          display: grid;
          gap: 10px;
          padding: 14px;
          border-radius: 12px;
          border: 1px dashed var(--border-primary);
          color: var(--text-secondary);
        }

        .api-key-note {
          color: var(--text-secondary);
          font-size: 12px;
        }

        .api-key-error {
          color: var(--danger);
          font-size: 12px;
        }

        .api-key-actions {
          margin-top: 20px;
          display: flex;
          justify-content: flex-end;
          gap: 10px;
        }
      `}</style>
    </div>
  );
}
