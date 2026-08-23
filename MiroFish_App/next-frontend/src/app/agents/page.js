'use client';
import { useState } from 'react';
import { useSimulation } from '../../context/SimulationContext';
import InterviewPanel from '../../components/InterviewPanel';

export default function AgentsPage() {
  const { state } = useSimulation();
  const [selectedAgent, setSelectedAgent] = useState(null);

  // Generate a mock list of agents based on the population size (or we could fetch the exact IDs)
  // Assuming agent IDs are Agent_0 to Agent_{population-1}
  const popCount = state.population || 200;
  const agentsList = Array.from({ length: popCount }, (_, i) => `Agent_${i}`);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', gap: '24px' }}>
      <header className="glass-panel" style={{ padding: '16px 24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h2 style={{ fontSize: '1.1rem', fontWeight: '600' }}>Agent Database</h2>
        <div style={{ color: 'var(--text-secondary)' }}>Total Population: {popCount}</div>
      </header>
      
      <main className="glass-panel" style={{ flex: 1, padding: '24px', overflowY: 'auto', minHeight: 0 }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(150px, 1fr))', gap: '16px' }}>
          {agentsList.map(agentId => (
            <button 
              key={agentId} 
              className="agent-card"
              onClick={() => setSelectedAgent(agentId)}
            >
              <div className="agent-avatar"></div>
              <span>{agentId}</span>
            </button>
          ))}
        </div>
      </main>

      {selectedAgent && (
        <InterviewPanel agentId={selectedAgent} onClose={() => setSelectedAgent(null)} />
      )}

      <style jsx>{`
        .agent-card {
          background: rgba(255, 255, 255, 0.02);
          border: 1px solid var(--border-color);
          border-radius: 12px;
          padding: 16px;
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 12px;
          cursor: pointer;
          color: var(--text-primary);
          transition: 0.2s;
        }
        .agent-card:hover {
          background: rgba(255, 255, 255, 0.05);
          border-color: rgba(255, 255, 255, 0.2);
          transform: translateY(-2px);
        }
        .agent-avatar {
          width: 48px;
          height: 48px;
          border-radius: 50%;
          background: radial-gradient(circle at top left, rgba(255,255,255,0.1), transparent);
          border: 1px solid rgba(255,255,255,0.05);
        }
      `}</style>
    </div>
  );
}
