import React from 'react';
import '../index.css';

const Header: React.FC = () => {
  return (
    <header className="glass-panel" style={{ borderRadius: '0', borderTop: 'none', borderLeft: 'none', borderRight: 'none', padding: '16px 32px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
        <div style={{ 
          width: '32px', height: '32px', 
          background: 'linear-gradient(135deg, var(--accent-primary), #8b5cf6)', 
          borderRadius: '8px',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          boxShadow: '0 0 15px var(--accent-glow)'
        }}>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
          </svg>
        </div>
        <div>
          <h1 style={{ margin: 0, fontSize: '1.25rem', display: 'flex', alignItems: 'center', gap: '8px' }}>
            AegisMesh AI
            <span className="badge badge-neutral" style={{ fontSize: '0.65rem' }}>Demo Mode</span>
          </h1>
          <p style={{ margin: 0, fontSize: '0.75rem', color: 'var(--text-muted)' }}>Agentic AI Governance Control Plane</p>
        </div>
      </div>
      
      <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>Active Provider:</span>
          <span className="badge badge-neutral" style={{ background: 'rgba(99, 102, 241, 0.1)', color: 'var(--accent-primary)', borderColor: 'rgba(99, 102, 241, 0.2)' }}>
            IBM Granite
          </span>
        </div>
        <div style={{ width: '1px', height: '24px', background: 'var(--border-subtle)' }}></div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--status-approve)', boxShadow: '0 0 8px var(--status-approve)' }}></div>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>System Health: Optimal</span>
        </div>
      </div>
    </header>
  );
};

export default Header;
