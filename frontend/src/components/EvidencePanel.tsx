import React from 'react';

const EvidencePanel: React.FC = () => {
  const documents = [
    { id: 1, title: 'Data Transfer Policy V2.pdf', score: 98, excerpt: '...internal data must not be exported to external storage without explicit executive approval...' },
    { id: 2, title: 'PII Handling Guidelines.md', score: 85, excerpt: '...any extract containing user personally identifiable information must be masked or tokenized prior to export...' },
  ];

  return (
    <div className="glass-panel animate-slide-in" style={{ animationDelay: '0.5s' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
        <h3 style={{ margin: 0, fontSize: '1rem', color: 'var(--text-secondary)' }}>RAG Policy Evidence</h3>
        <span className="badge badge-neutral" style={{ background: 'var(--accent-glow)', color: 'var(--accent-primary)', borderColor: 'var(--accent-primary)' }}>
          2 Documents Retrieved
        </span>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
        {documents.map(doc => (
          <div key={doc.id} style={{ background: 'var(--bg-panel-solid)', padding: '16px', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--text-muted)" strokeWidth="2">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/>
                </svg>
                <span style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-primary)' }}>{doc.title}</span>
              </div>
              <span className="badge badge-neutral" style={{ fontSize: '0.7rem' }}>
                {doc.score}% Relevance
              </span>
            </div>
            
            <p style={{ margin: 0, fontSize: '0.8rem', color: 'var(--text-secondary)', fontStyle: 'italic', borderLeft: '2px solid var(--border-subtle)', paddingLeft: '8px' }}>
              "{doc.excerpt}"
            </p>
          </div>
        ))}
      </div>
    </div>
  );
};

export default EvidencePanel;
