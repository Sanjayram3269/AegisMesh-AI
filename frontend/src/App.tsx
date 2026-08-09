import React, { useState } from 'react';
import Header from './components/Header';
import RequestPanel from './components/RequestPanel';
import PipelineTimeline from './components/PipelineTimeline';
import RiskGauge from './components/RiskGauge';
import DecisionBanner from './components/DecisionBanner';
import TransformationView from './components/TransformationView';
import EvidencePanel from './components/EvidencePanel';
import AuditPanel from './components/AuditPanel';
import HumanReviewModal from './components/HumanReviewModal';

const App: React.FC = () => {
  const [scenario, setScenario] = useState<number>(0);

  const getDecision = () => {
    if (scenario === 1) return 'APPROVE';
    if (scenario === 2) return 'MODIFY';
    if (scenario === 3) return 'ESCALATE';
    if (scenario === 4) return 'REJECT';
    return null;
  };

  const getRiskScore = () => {
    if (scenario === 1) return 12;
    if (scenario === 2) return 45;
    if (scenario === 3) return 78;
    if (scenario === 4) return 95;
    return 0;
  };

  const decision = getDecision();
  const riskScore = getRiskScore();

  return (
    <div className="app-container">
      <Header />
      
      <main className="main-content">
        {/* Left Column - Inputs & Pipeline */}
        <div className="col">
          <RequestPanel onSubmit={setScenario} />
          {scenario > 0 && <PipelineTimeline />}
        </div>

        {/* Right Column - Results & Analysis */}
        <div className="col">
          {scenario === 0 ? (
            <div className="glass-panel" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', opacity: 0.5 }}>
              <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="var(--text-muted)" strokeWidth="1" style={{ marginBottom: '16px' }}>
                <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
              </svg>
              <p>Select a scenario to run governance evaluation</p>
            </div>
          ) : (
            <>
              {decision && <DecisionBanner decision={decision} />}
              
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px' }}>
                <RiskGauge score={riskScore} />
                <EvidencePanel />
              </div>

              {decision === 'MODIFY' && <TransformationView />}
              
              <AuditPanel />
            </>
          )}
        </div>
      </main>

      {/* Conditional Modals */}
      {decision === 'ESCALATE' && <HumanReviewModal />}
    </div>
  );
};

export default App;
