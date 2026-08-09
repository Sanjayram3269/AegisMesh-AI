import React, { useState } from 'react';

interface RequestPanelProps {
  onSubmit: (scenario: number) => void;
}

const RequestPanel: React.FC<RequestPanelProps> = ({ onSubmit }) => {
  const [userId, setUserId] = useState('usr_9042a');
  const [role, setRole] = useState('Data Scientist');
  const [action, setAction] = useState('Export Q2 financials to local CSV');
  const [target, setTarget] = useState('Local Desktop');

  const presets = [
    { id: 1, label: 'Safe Export', desc: 'Internal system read (APPROVE)', color: 'var(--status-approve)' },
    { id: 2, label: 'PII Export', desc: 'Contains SSN/Emails (MODIFY)', color: 'var(--status-modify)' },
    { id: 3, label: 'External Vendor', desc: 'SaaS API call (ESCALATE)', color: 'var(--status-escalate)' },
    { id: 4, label: 'Public Release', desc: 'Unauthorized sharing (REJECT)', color: 'var(--status-reject)' },
  ];

  return (
    <div className="glass-panel animate-slide-in">
      <h2 style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M12 20h9" /><path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z" />
        </svg>
        Action Proposal
      </h2>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '24px' }}>
        {presets.map(p => (
          <button 
            key={p.id}
            className="btn btn-secondary"
            style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start', padding: '12px', borderColor: p.color + '40' }}
            onClick={() => onSubmit(p.id)}
          >
            <span style={{ color: p.color, fontWeight: 600, fontSize: '0.85rem' }}>{p.label}</span>
            <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: '4px' }}>{p.desc}</span>
          </button>
        ))}
      </div>

      <div className="input-group" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
        <div>
          <label className="input-label">User ID</label>
          <input className="input-field" value={userId} onChange={e => setUserId(e.target.value)} />
        </div>
        <div>
          <label className="input-label">Role</label>
          <input className="input-field" value={role} onChange={e => setRole(e.target.value)} />
        </div>
      </div>
      
      <div className="input-group">
        <label className="input-label">Target System</label>
        <input className="input-field" value={target} onChange={e => setTarget(e.target.value)} />
      </div>

      <div className="input-group">
        <label className="input-label">Proposed Action</label>
        <textarea 
          className="input-field" 
          rows={3} 
          value={action} 
          onChange={e => setAction(e.target.value)}
          style={{ resize: 'vertical' }}
        />
      </div>

      <button className="btn btn-primary" style={{ width: '100%', padding: '12px', marginTop: '8px' }}>
        Evaluate Governance Pipeline
      </button>
    </div>
  );
};

export default RequestPanel;
