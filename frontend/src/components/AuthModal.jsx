import { useEffect, useState } from 'react';
import { Bot } from './icons/AppIcons';

export function AuthModal({ isOpen, onClose, onLogin, onRegister }) {
    const [isRegister, setIsRegister] = useState(false);
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);
    const [registrationComplete, setRegistrationComplete] = useState(false);
    const [requiresVerification, setRequiresVerification] = useState(false);
    const [registeredApiKey, setRegisteredApiKey] = useState('');
    const [copyStatus, setCopyStatus] = useState('');

    useEffect(() => {
        if (!isOpen) return;
        setIsRegister(false);
        setUsername('');
        setPassword('');
        setConfirmPassword('');
        setError('');
        setLoading(false);
        setRegistrationComplete(false);
        setRequiresVerification(false);
        setRegisteredApiKey('');
        setCopyStatus('');
    }, [isOpen]);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        setLoading(true);

        // Simulate delay for "SaaS" feel
        await new Promise(r => setTimeout(r, 600));

        try {
            if (isRegister) {
                if (password !== confirmPassword) {
                    throw new Error('Passwords do not match');
                }
                if (!onRegister) {
                    throw new Error('Registration is unavailable');
                }
                const result = await onRegister(username, password);
                setRegisteredApiKey(result?.apiKey || '');
                setRequiresVerification(Boolean(result?.requiresVerification));
                setRegistrationComplete(true);
                setCopyStatus('');
            } else {
                await onLogin(username, password);
                onClose();
            }
        } catch (err) {
            setError(err.message || 'Authentication failed');
        } finally {
            setLoading(false);
        }
    };

    const handleCopyApiKey = async () => {
        if (!registeredApiKey) return;
        try {
            await navigator.clipboard.writeText(registeredApiKey);
            setCopyStatus('Copied to clipboard');
        } catch {
            setCopyStatus('Copy failed');
        }
    };

    if (!isOpen) return null;

    return (
        <div className="auth-overlay" onClick={onClose}>
            <div className="auth-modal" onClick={e => e.stopPropagation()}>
                <div className="auth-header">
                    <div className="auth-logo">
                        <Bot className="ui-icon" />
                    </div>
                    <h2>
                        {registrationComplete
                            ? 'Account created'
                            : (isRegister ? 'Create Account' : 'Welcome Back')}
                    </h2>
                    <p>
                        {registrationComplete
                            ? (registeredApiKey
                                ? 'Copy your API key now. You will not be able to view it again.'
                                : (requiresVerification
                                  ? 'Check your email to verify your account.'
                                  : 'Your account is ready. You can continue to the dashboard.'))
                            : (isRegister ? 'Start monitoring your agents today' : 'Sign in to Agent Lighthouse')}
                    </p>
                </div>

                {!registrationComplete && (
                    <div className="auth-tabs">
                        <button
                            className={`auth-tab ${!isRegister ? 'active' : ''}`}
                            onClick={() => setIsRegister(false)}
                        >
                            Sign In
                        </button>
                        <button
                            className={`auth-tab ${isRegister ? 'active' : ''}`}
                            onClick={() => setIsRegister(true)}
                        >
                            Register
                        </button>
                    </div>
                )}

                {registrationComplete ? (
                    <div className="auth-success">
                        {registeredApiKey ? (
                            <div className="form-group">
                                <label>Your API Key</label>
                                <div className="api-key-row">
                                    <input
                                        type="text"
                                        value={registeredApiKey || 'Unavailable'}
                                        readOnly
                                    />
                                    <button
                                        type="button"
                                        className="btn btn-secondary btn-sm"
                                        onClick={handleCopyApiKey}
                                        disabled={!registeredApiKey}
                                    >
                                        Copy
                                    </button>
                                </div>
                                {copyStatus && <div className="auth-note">{copyStatus}</div>}
                            </div>
                        ) : (
                            <div className="auth-note">
                                {requiresVerification
                                  ? 'We have sent a verification link to your email. Please verify to continue.'
                                  : 'Your account is active. You can continue to the dashboard.'}
                            </div>
                        )}

                        <button type="button" className="btn btn-primary btn-block" onClick={onClose}>
                            Continue
                        </button>
                    </div>
                ) : (
                    <form onSubmit={handleSubmit} className="auth-form">
                        <div className="form-group">
                            <label>Email</label>
                            <input
                                type="text"
                                value={username}
                                onChange={e => setUsername(e.target.value)}
                                placeholder="you@example.com"
                                autoFocus
                            />
                        </div>

                        <div className="form-group">
                            <label>Password</label>
                            <input
                                type="password"
                                value={password}
                                onChange={e => setPassword(e.target.value)}
                                placeholder="••••••••"
                            />
                        </div>

                        {isRegister && (
                            <div className="form-group">
                                <label>Confirm Password</label>
                                <input
                                    type="password"
                                    value={confirmPassword}
                                    onChange={e => setConfirmPassword(e.target.value)}
                                    placeholder="••••••••"
                                />
                            </div>
                        )}

                        {error && <div className="auth-error">{error}</div>}

                        <button type="submit" className="btn btn-primary btn-block" disabled={loading}>
                            {loading ? 'Processing...' : (isRegister ? 'Create Account' : 'Sign In')}
                        </button>
                    </form>
                )}

                <p className="auth-footer">
                    By continuing, you agree to our Terms of Service and Privacy Policy.
                </p>
            </div>

            <style>{`
        .auth-overlay {
          position: fixed;
          inset: 0;
          background: rgba(255, 255, 255, 0.4);
          backdrop-filter: blur(8px);
          display: flex;
          align-items: center;
          justify-content: center;
          z-index: 9999;
          animation: fade-in 0.2s ease-out;
        }

        .auth-modal {
          width: 100%;
          max-width: 400px;
          background: var(--bg-primary);
          border: 1px solid var(--border-primary);
          border-radius: 24px;
          padding: 32px;
          box-shadow: var(--shadow-lg), 0 20px 40px rgba(0,0,0,0.1);
          animation: slide-up 0.3s var(--ease-emphasized);
        }

        .auth-header {
          text-align: center;
          margin-bottom: 24px;
        }

        .auth-logo {
          width: 48px;
          height: 48px;
          background: var(--gradient-primary);
          border-radius: 12px;
          display: flex;
          align-items: center;
          justify-content: center;
          color: white;
          margin: 0 auto 16px;
          box-shadow: var(--shadow-glow);
        }

        .auth-header h2 {
          font-size: 24px;
          font-weight: 700;
          color: var(--text-primary);
          margin-bottom: 8px;
        }

        .auth-header p {
          font-size: 14px;
          color: var(--text-secondary);
        }

        .auth-tabs {
          display: flex;
          background: var(--bg-secondary);
          padding: 4px;
          border-radius: 12px;
          margin-bottom: 24px;
        }

        .auth-tab {
          flex: 1;
          padding: 8px;
          font-size: 13px;
          font-weight: 600;
          border: none;
          background: transparent;
          color: var(--text-muted);
          border-radius: 8px;
          cursor: pointer;
          transition: all 0.2s;
        }

        .auth-tab.active {
          background: white;
          color: var(--text-primary);
          box-shadow: var(--shadow-sm);
        }

        .form-group {
          margin-bottom: 16px;
        }

        .form-group label {
          display: block;
          font-size: 13px;
          font-weight: 500;
          color: var(--text-secondary);
          margin-bottom: 6px;
        }

        .form-group input {
          width: 100%;
          padding: 10px 12px;
          border-radius: 10px;
          border: 1px solid var(--border-primary);
          background: var(--bg-root);
          font-size: 14px;
          color: var(--text-primary);
          transition: border-color 0.2s;
        }

        .api-key-row {
          display: flex;
          gap: 8px;
          align-items: center;
        }

        .api-key-row input {
          flex: 1;
          font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
        }

        .form-group input:focus {
          border-color: var(--accent-primary);
          outline: none;
          background: white;
        }

        .btn-block {
          width: 100%;
          padding: 12px;
          font-size: 14px;
          margin-top: 8px;
        }

        .auth-error {
          color: var(--accent-error);
          font-size: 13px;
          text-align: center;
          margin-bottom: 16px;
          background: rgba(239, 68, 68, 0.1);
          padding: 8px;
          border-radius: 8px;
        }

        .auth-success {
          display: flex;
          flex-direction: column;
          gap: 12px;
        }

        .auth-note {
          margin-top: 8px;
          font-size: 12px;
          color: var(--text-muted);
          text-align: center;
        }

        .auth-footer {
          margin-top: 24px;
          font-size: 11px;
          color: var(--text-muted);
          text-align: center;
          line-height: 1.4;
        }

        @keyframes fade-in { from { opacity: 0; } to { opacity: 1; } }
        @keyframes slide-up { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }
      `}</style>
        </div>
    );
}
