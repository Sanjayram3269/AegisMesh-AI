import React from 'react';

const AuditPanel: React.FC = () => {
  const logs = [
    { id: 'REQ-9921', time: '10:42:05', user: 'usr_9042a', action: 'Query DB', decision: 'APPROVE', risk: 12 },
    { id: 'REQ-9920', time: '10:38:22', user: 'usr_1192x', action: 'Export CSV', decision: 'MODIFY', risk: 45 },
    { id: 'REQ-9919', time: '10:15:11', user: 'usr_5521b', action: 'API Call SaaS', decision: 'ESCALATE', risk: 78 },
    { id: 'REQ-9918', time: '09:55:03', user: 'usr_9042a', action: 'Public Share', decision: 'REJECT', risk: 95 },
  ];

  return (
    <div className="glass-panel animate-slide-in" style={{ animationDelay: '0.6s' }}>
      <h3 style={{ marginBottom: '16px', fontSize: '1rem', color: 'var(--text-secondary)' }}>Audit Trail</h3>
      
      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid var(--border-subtle)', color: 'var(--text-muted)', textAlign: 'left' }}>
              <th style={{ padding: '12px 8px', fontWeight: 500 }}>Time</th>
              <th style={{ padding: '12px 8px', fontWeight: 500 }}>Req ID</th>
              <th style={{ padding: '12px 8px', fontWeight: 500 }}>User</th>
              <th style={{ padding: '12px 8px', fontWeight: 500 }}>Action</th>
              <th style={{ padding: '12px 8px', fontWeight: 500 }}>Decision</th>
            </tr>
          </thead>
          <tbody>
            {logs.map((log, i) => (
              <tr key={i} style={{ borderBottom: '1px solid rgba(30, 41, 59, 0.5)', transition: 'background 0.2s', cursor: 'pointer' }} 
                  onMouseEnter={e => e.currentTarget.style.backgroundColor = 'rgba(255,255,255,0.02)'}
                  onMouseLeave={e => e.currentTarget.style.backgroundColor = 'transparent'}>
                <td style={{ padding: '12px 8px', color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)' }}>{log.time}</td>
                <td style={{ padding: '12px 8px', color: 'var(--accent-primary)', fontFamily: 'var(--font-mono)' }}>{log.id}</td>
                <td style={{ padding: '12px 8px', color: 'var(--text-primary)' }}>{log.user}</td>
                <td style={{ padding: '12px 8px', color: 'var(--text-secondary)' }}>{log.action}</td>
                <td style={{ padding: '12px 8px' }}>
                  <span className={`badge badge-${log.decision.toLowerCase()}`} style={{ fontSize: '0.65rem' }}>
                    {log.decision}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default AuditPanel;
