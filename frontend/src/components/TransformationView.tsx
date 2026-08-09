import React from 'react';

const TransformationView: React.FC = () => {
  return (
    <div className="glass-panel animate-slide-in" style={{ animationDelay: '0.4s' }}>
      <h3 style={{ marginBottom: '16px', fontSize: '1rem', color: 'var(--text-secondary)' }}>Applied Transformations</h3>
      
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '24px' }}>
        <div style={{ background: 'rgba(225, 29, 72, 0.05)', border: '1px solid rgba(225, 29, 72, 0.2)', padding: '12px', borderRadius: '8px' }}>
          <div style={{ fontSize: '0.75rem', color: 'var(--status-reject)', marginBottom: '8px', fontWeight: 600 }}>ORIGINAL ACTION</div>
          <pre style={{ margin: 0, fontFamily: 'var(--font-mono)', fontSize: '0.8rem', color: 'var(--text-primary)', whiteSpace: 'pre-wrap' }}>
            SELECT * FROM users WHERE active = true
          </pre>
        </div>
        
        <div style={{ background: 'rgba(16, 185, 129, 0.05)', border: '1px solid rgba(16, 185, 129, 0.2)', padding: '12px', borderRadius: '8px' }}>
          <div style={{ fontSize: '0.75rem', color: 'var(--status-approve)', marginBottom: '8px', fontWeight: 600 }}>TRANSFORMED ACTION</div>
          <pre style={{ margin: 0, fontFamily: 'var(--font-mono)', fontSize: '0.8rem', color: 'var(--text-primary)', whiteSpace: 'pre-wrap' }}>
            SELECT id, role, department FROM users WHERE active = true
          </pre>
        </div>
      </div>

      <div style={{ marginBottom: '24px' }}>
        <h4 style={{ fontSize: '0.85rem', color: 'var(--text-primary)', marginBottom: '8px' }}>Transformation Rules Applied:</h4>
        <ul style={{ listStyleType: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: '8px' }}>
          <li style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--status-modify)" strokeWidth="2"><path d="M20 6L9 17l-5-5"/></svg>
            Anonymized PII fields (email, phone, address)
          </li>
          <li style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--status-modify)" strokeWidth="2"><path d="M20 6L9 17l-5-5"/></svg>
            Applied filter view based on Data Scientist role
          </li>
        </ul>
      </div>

      <button className="btn btn-primary" style={{ width: '100%' }}>
        Re-evaluate Transformed Action
      </button>
    </div>
  );
};

export default TransformationView;
