import React, { useState } from 'react';
import './index.css';
import SimulationWizard from './components/SimulationWizard';
import MatrixFeed from './components/MatrixFeed';
import AnalystReport from './components/AnalystReport';
import NetworkGraph from './components/NetworkGraph';

function App() {
  const [campaignId, setCampaignId] = useState(null);

  const handleSimulationStart = (id) => {
    setCampaignId(id);
  };

  return (
    <div className="dashboard-layout" style={{ display: 'grid', gridTemplateColumns: '400px 1fr', gap: '24px', padding: '24px', height: '100vh' }}>
      
      {/* Left Sidebar: Simulation Wizard */}
      <aside className="glass-panel input-section" style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
        <h1 className="glow-text" style={{ color: 'var(--accent-color)', fontSize: '2rem', margin: 0 }}>MarketFish</h1>
        <p style={{ color: 'var(--text-secondary)', margin: 0, paddingBottom: '10px', borderBottom: '1px solid rgba(255,255,255,0.1)' }}>Command Center</p>
        
        <SimulationWizard onSimulationStart={handleSimulationStart} />
      </aside>

      {/* Right Area: Output & Analytics */}
      <main style={{ display: 'flex', flexDirection: 'column', gap: '24px', overflowY: 'auto' }}>
        
        {/* Top: Scorecard & Report */}
        <section className="glass-panel" style={{ minHeight: '200px' }}>
           <AnalystReport campaignId={campaignId} />
        </section>

        {campaignId && (
          <section className="glass-panel" style={{ minHeight: '300px' }}>
             <NetworkGraph campaignId={campaignId} />
          </section>
        )}

        {/* Bottom: Matrix Feed */}
        <section className="glass-panel" style={{ flex: 1, minHeight: '300px', display: 'flex', flexDirection: 'column' }}>
           <MatrixFeed campaignId={campaignId} />
        </section>

      </main>

    </div>
  );
}

export default App;
