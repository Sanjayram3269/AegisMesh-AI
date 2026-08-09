import React from 'react';

interface AgentNode {
  id: string;
  name: string;
  status: 'completed' | 'running' | 'pending';
  duration?: number;
  desc: string;
}

const PipelineTimeline: React.FC = () => {
  const agents: AgentNode[] = [
    { id: '1', name: 'Intent Analysis', status: 'completed', duration: 120, desc: 'Parses user intent' },
    { id: '2', name: 'Identity Context', status: 'completed', duration: 45, desc: 'Checks RBAC & clearance' },
    { id: '3', name: 'Policy RAG', status: 'completed', duration: 310, desc: 'Retrieves governance docs' },
    { id: '4', name: 'Granite Reasoning', status: 'running', duration: 850, desc: 'Evaluates action vs policy' },
    { id: '5', name: 'Risk Scoring', status: 'pending', desc: 'Calculates overall risk' },
    { id: '6', name: 'Decision Engine', status: 'pending', desc: 'Final verdict generation' }
  ];

  return (
    <div className="glass-panel animate-slide-in" style={{ animationDelay: '0.1s' }}>
      <h3 style={{ marginBottom: '20px', fontSize: '1rem', color: 'var(--text-secondary)' }}>Live Evaluation Pipeline</h3>
      
      <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', position: 'relative' }}>
        {/* Connecting line */}
        <div style={{ position: 'absolute', left: '15px', top: '20px', bottom: '20px', width: '2px', background: 'var(--border-subtle)', zIndex: 0 }}></div>
        
        {agents.map((agent, index) => {
          let color = 'var(--border-subtle)';
          let icon = <circle cx="12" cy="12" r="5" fill="var(--text-muted)" />;
          
          if (agent.status === 'completed') {
            color = 'var(--status-approve)';
            icon = <path d="M20 6L9 17l-5-5" stroke="var(--status-approve)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />;
          } else if (agent.status === 'running') {
            color = 'var(--accent-primary)';
            icon = <circle cx="12" cy="12" r="5" fill="var(--accent-primary)" style={{ animation: 'pulseGlow 2s infinite' }} />;
          }

          return (
            <div key={agent.id} style={{ display: 'flex', gap: '16px', position: 'relative', zIndex: 1, opacity: agent.status === 'pending' ? 0.5 : 1 }}>
              <div style={{ 
                width: '32px', height: '32px', 
                borderRadius: '50%', background: 'var(--bg-panel-solid)', 
                border: `2px solid ${color}`,
                display: 'flex', alignItems: 'center', justifyContent: 'center'
              }}>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                  {icon}
                </svg>
              </div>
              <div style={{ flex: 1, paddingBottom: '16px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
                  <span style={{ fontWeight: 600, color: agent.status === 'running' ? 'var(--accent-primary)' : 'var(--text-primary)' }}>
                    {agent.name}
                  </span>
                  {agent.duration && <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>{agent.duration}ms</span>}
                </div>
                <p style={{ margin: 0, fontSize: '0.8rem', color: 'var(--text-secondary)' }}>{agent.desc}</p>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default PipelineTimeline;
