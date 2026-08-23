'use client';
import { useSimulation } from '../../context/SimulationContext';
import AnalyticsPanel from '../../components/AnalyticsPanel';

export default function AnalyticsPage() {
  const { state } = useSimulation();

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', gap: '24px' }}>
      <header className="glass-panel" style={{ padding: '16px 24px', display: 'flex', justifyContent: 'space-between' }}>
        <h2 style={{ fontSize: '1.1rem', fontWeight: '600' }}>Deep Dive Analytics</h2>
        <div style={{ color: 'var(--text-secondary)' }}>Round: {state.round || 0}</div>
      </header>
      
      <main style={{ flex: 1, minHeight: 0, display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px' }}>
        <AnalyticsPanel 
          falsification={state.falsification} 
          clusters={state.clusters} 
          fearIndex={state.fear_index} 
        />
      </main>
    </div>
  );
}
