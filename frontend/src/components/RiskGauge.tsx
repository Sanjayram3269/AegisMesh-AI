import React from 'react';

interface RiskGaugeProps {
  score: number; // 0 - 100
}

const RiskGauge: React.FC<RiskGaugeProps> = ({ score }) => {
  let level = 'LOW';
  let color = 'var(--status-approve)';
  if (score > 30) { level = 'MEDIUM'; color = 'var(--status-modify)'; }
  if (score > 60) { level = 'HIGH'; color = 'var(--status-escalate)'; }
  if (score > 85) { level = 'CRITICAL'; color = 'var(--status-reject)'; }

  const factors = [
    { name: 'Data Sensitivity', val: 'Medium', flag: false },
    { name: 'External Exposure', val: 'High', flag: true },
    { name: 'Authorization', val: 'Valid', flag: false },
    { name: 'Policy Violations', val: 'Detected', flag: true }
  ];

  return (
    <div className="glass-panel animate-slide-in" style={{ animationDelay: '0.2s' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <h3 style={{ margin: 0, fontSize: '1rem', color: 'var(--text-secondary)' }}>Risk Analysis</h3>
        <span className={`badge`} style={{ background: `${color}20`, color: color, borderColor: `${color}40` }}>
          {level} RISK
        </span>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '24px', marginBottom: '24px' }}>
        {/* Circular Gauge approximation */}
        <div style={{ 
          position: 'relative', width: '100px', height: '100px', 
          borderRadius: '50%', background: `conic-gradient(${color} ${score}%, var(--border-subtle) 0)` 
        }}>
          <div style={{ 
            position: 'absolute', inset: '8px', 
            borderRadius: '50%', background: 'var(--bg-panel-solid)',
            display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center'
          }}>
            <span style={{ fontSize: '1.75rem', fontWeight: 700, color: 'var(--text-primary)', fontFamily: 'var(--font-mono)', lineHeight: 1 }}>{score}</span>
            <span style={{ fontSize: '0.65rem', color: 'var(--text-muted)' }}>/ 100</span>
          </div>
        </div>

        <div style={{ flex: 1 }}>
          <h4 style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '8px', textTransform: 'uppercase' }}>Risk Factors</h4>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {factors.map((f, i) => (
              <div key={i} style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem' }}>
                <span style={{ color: 'var(--text-secondary)' }}>{f.name}</span>
                <span style={{ color: f.flag ? 'var(--status-reject)' : 'var(--text-primary)' }}>{f.val}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default RiskGauge;
