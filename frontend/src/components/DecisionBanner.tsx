import React from 'react';

interface DecisionBannerProps {
  decision: 'APPROVE' | 'MODIFY' | 'ESCALATE' | 'REJECT';
}

const DecisionBanner: React.FC<DecisionBannerProps> = ({ decision }) => {
  const config = {
    APPROVE: { color: 'var(--status-approve)', text: 'Action Approved', desc: 'No governance violations detected. Action is safe to execute.' },
    MODIFY: { color: 'var(--status-modify)', text: 'Action Modified', desc: 'Action violates data privacy policies. Safe transformations applied.' },
    ESCALATE: { color: 'var(--status-escalate)', text: 'Human Escalation Required', desc: 'High risk action detected. Requires manual review by compliance team.' },
    REJECT: { color: 'var(--status-reject)', text: 'Action Rejected', desc: 'Critical policy violation. Action blocked.' }
  };

  const current = config[decision];

  return (
    <div className="glass-panel animate-slide-in" style={{ 
      animationDelay: '0.3s',
      background: `linear-gradient(90deg, ${current.color}15, var(--bg-panel))`,
      borderLeft: `4px solid ${current.color}` 
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '8px' }}>
            <span className={`badge badge-${decision.toLowerCase()}`} style={{ fontSize: '0.85rem', padding: '6px 12px' }}>
              {decision}
            </span>
            <h2 style={{ margin: 0, fontSize: '1.25rem', color: current.color }}>{current.text}</h2>
          </div>
          <p style={{ margin: 0, color: 'var(--text-primary)', fontSize: '0.9rem' }}>{current.desc}</p>
        </div>
        
        {decision === 'ESCALATE' && (
          <button className="btn btn-primary" style={{ backgroundColor: current.color, boxShadow: `0 0 15px ${current.color}40` }}>
            Review Case
          </button>
        )}
      </div>
    </div>
  );
};

export default DecisionBanner;
