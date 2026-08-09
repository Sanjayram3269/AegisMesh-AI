import React from 'react';

const HumanReviewModal: React.FC = () => {
  return (
    <div style={{
      position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
      background: 'rgba(9, 13, 22, 0.8)',
      backdropFilter: 'blur(4px)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      zIndex: 1000
    }}>
      <div className="glass-panel animate-slide-in" style={{ width: '100%', maxWidth: '600px', border: '1px solid var(--status-escalate)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
          <h2 style={{ margin: 0, fontSize: '1.25rem', color: 'var(--status-escalate)', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
              <line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>
            </svg>
            Human Escalation Required
          </h2>
          <button style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}>
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
          </button>
        </div>

        <div style={{ background: 'var(--bg-panel-solid)', padding: '16px', borderRadius: '8px', marginBottom: '24px' }}>
          <p style={{ margin: 0, fontSize: '0.9rem', color: 'var(--text-primary)' }}>
            <strong>Action Details:</strong> User usr_9042a is attempting to export 500+ records to an external SaaS vendor (Vendor_ID: 1029). 
            This exceeds the automatic approval threshold and requires compliance team sign-off.
          </p>
        </div>

        <div className="input-group">
          <label className="input-label">Reviewer Comments</label>
          <textarea className="input-field" rows={4} placeholder="Enter justification for approval or rejection..." style={{ resize: 'vertical' }}></textarea>
        </div>

        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px', marginTop: '32px' }}>
          <button className="btn btn-secondary">Request Modification</button>
          <button className="btn btn-primary" style={{ backgroundColor: 'var(--status-reject)' }}>Reject Action</button>
          <button className="btn btn-primary" style={{ backgroundColor: 'var(--status-approve)' }}>Approve Override</button>
        </div>
      </div>
    </div>
  );
};

export default HumanReviewModal;
