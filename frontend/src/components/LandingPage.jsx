import { useState } from 'react';
import { Radar, Coins, SearchCode, Bot } from './icons/AppIcons';

export function LandingPage({ onLoginClick }) {
    return (
        <div className="landing-page">
            <nav className="landing-nav">
                <div className="brand">
                    <div className="brand-logo">
                        <Bot className="ui-icon" />
                    </div>
                    <span className="brand-name">Agent Lighthouse</span>
                </div>
                <div className="nav-actions">
                    <a href="https://github.com/noogler-aditya/Agent-Lighthouse" target="_blank" rel="noreferrer" className="nav-link">GitHub</a>
                    <a href="https://github.com/noogler-aditya/Agent-Lighthouse/blob/main/docs/GETTING_STARTED.md" target="_blank" rel="noreferrer" className="nav-link">Docs</a>
                    <button className="btn btn-secondary btn-sm" onClick={onLoginClick}>Sign In</button>
                </div>
            </nav>

            <main className="landing-hero">
                <div className="hero-content">
                    <div className="badge-pill">
                        <span className="badge-dot"></span>
                        v0.2.0 Now Available
                    </div>

                    <h1 className="hero-title">
                        See Inside Your <br />
                        <span className="text-gradient">AI Agents</span>
                    </h1>

                    <p className="hero-subtitle">
                        The open-source visual debugger for multi-agent systems.
                        Trace execution, monitor costs, and inspect state in real-time.
                    </p>

                    <div className="hero-actions">
                        <button className="btn btn-primary btn-lg" onClick={onLoginClick}>
                            Start Debugging
                        </button>
                        <div className="hero-stats">
                            <span>Trusted by 500+ developers</span>
                        </div>
                    </div>
                </div>

                <div className="bento-grid">
                    <div className="bento-card card-visual">
                        <div className="card-icon-wrapper primary">
                            <Radar className="ui-icon-lg" />
                        </div>
                        <h3>Visual Tracing</h3>
                        <p>Watch your agents think in real-time. Debug complex loops and handoffs with an interactive graph.</p>
                        <div className="visual-preview"></div>
                    </div>

                    <div className="bento-col">
                        <div className="bento-card card-tokens">
                            <div className="card-icon-wrapper warning">
                                <Coins className="ui-icon-lg" />
                            </div>
                            <h3>Token Monitor</h3>
                            <p>Track burn rate per agent. Optimize costs before deployment.</p>
                        </div>

                        <div className="bento-card card-state">
                            <div className="card-icon-wrapper info">
                                <SearchCode className="ui-icon-lg" />
                            </div>
                            <h3>State Inspector</h3>
                            <p>Pause execution. Edit memory. Resume. Time-travel debugging for AI.</p>
                        </div>
                    </div>
                </div>
            </main>

            <footer className="landing-footer">
                <p>© 2026 Agent Lighthouse. Open Source under MIT License.</p>
            </footer>

            <style>{`
        .landing-page {
          min-height: 100vh;
          background: var(--bg-root);
          display: flex;
          flex-direction: column;
          font-family: 'Space Grotesk', sans-serif;
        }

        .landing-nav {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 24px 48px;
          max-width: 1280px;
          margin: 0 auto;
          width: 100%;
        }

        .brand {
          display: flex;
          align-items: center;
          gap: 12px;
          font-weight: 700;
          font-size: 18px;
          color: var(--text-primary);
        }

        .brand-logo {
          width: 36px;
          height: 36px;
          background: var(--gradient-primary);
          border-radius: 10px;
          display: flex;
          align-items: center;
          justify-content: center;
          color: white;
          box-shadow: var(--shadow-glow);
        }

        .nav-actions {
          display: flex;
          align-items: center;
          gap: 24px;
        }

        .nav-link {
          color: var(--text-secondary);
          text-decoration: none;
          font-size: 14px;
          font-weight: 500;
          transition: color 0.2s;
        }

        .nav-link:hover {
          color: var(--text-primary);
        }

        .landing-hero {
          flex: 1;
          display: flex;
          flex-direction: column;
          align-items: center;
          padding: 80px 24px;
          max-width: 1280px;
          margin: 0 auto;
          width: 100%;
          text-align: center;
        }

        .badge-pill {
          display: inline-flex;
          align-items: center;
          gap: 8px;
          padding: 6px 16px;
          background: var(--bg-primary);
          border: 1px solid var(--border-primary);
          border-radius: 100px;
          font-size: 13px;
          font-weight: 600;
          color: var(--text-secondary);
          margin-bottom: 24px;
          box-shadow: var(--shadow-sm);
        }

        .badge-dot {
          width: 8px;
          height: 8px;
          background: var(--accent-success);
          border-radius: 50%;
        }

        .hero-title {
          font-size: 64px;
          line-height: 1.1;
          font-weight: 800;
          color: var(--text-primary);
          margin-bottom: 24px;
          letter-spacing: -0.02em;
        }

        .text-gradient {
          background: var(--gradient-primary);
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
        }

        .hero-subtitle {
          font-size: 20px;
          line-height: 1.6;
          color: var(--text-secondary);
          max-width: 640px;
          margin-bottom: 40px;
        }

        .hero-actions {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 16px;
          margin-bottom: 80px;
        }

        .btn-lg {
          padding: 14px 32px;
          font-size: 16px;
          border-radius: 100px;
        }

        .hero-stats {
          font-size: 13px;
          color: var(--text-muted);
        }

        /* Bento Grid */
        .bento-grid {
          display: grid;
          grid-template-columns: 1.5fr 1fr;
          gap: 24px;
          width: 100%;
          max-width: 1000px;
        }

        .bento-card {
          background: var(--bg-primary);
          border: 1px solid var(--border-primary);
          border-radius: 24px;
          padding: 32px;
          text-align: left;
          position: relative;
          overflow: hidden;
          box-shadow: var(--shadow-lg);
          transition: transform 0.3s ease, box-shadow 0.3s ease;
        }

        .bento-card:hover {
          transform: translateY(-4px);
          box-shadow: var(--shadow-glow);
        }

        .bento-col {
          display: flex;
          flex-direction: column;
          gap: 24px;
        }

        .card-visual {
          grid-row: span 2;
          min-height: 400px;
        }

        .card-icon-wrapper {
          width: 48px;
          height: 48px;
          border-radius: 12px;
          display: flex;
          align-items: center;
          justify-content: center;
          margin-bottom: 20px;
        }

        .card-icon-wrapper.primary { background: rgba(249, 115, 22, 0.1); color: var(--accent-primary); }
        .card-icon-wrapper.warning { background: rgba(245, 158, 11, 0.1); color: var(--accent-warning); }
        .card-icon-wrapper.info { background: rgba(59, 130, 246, 0.1); color: var(--accent-info); }

        .ui-icon-lg {
          width: 24px;
          height: 24px;
        }

        .bento-card h3 {
          font-size: 20px;
          font-weight: 700;
          color: var(--text-primary);
          margin-bottom: 8px;
        }

        .bento-card p {
          font-size: 15px;
          color: var(--text-secondary);
          line-height: 1.5;
        }

        .landing-footer {
          padding: 40px;
          text-align: center;
          color: var(--text-muted);
          font-size: 13px;
          margin-top: auto;
          border-top: 1px solid var(--border-primary);
        }

        @media (max-width: 768px) {
          .hero-title { font-size: 40px; }
          .bento-grid { grid-template-columns: 1fr; }
          .landing-nav { padding: 16px 24px; }
        }
      `}</style>
        </div>
    );
}
