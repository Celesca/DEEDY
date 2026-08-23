'use client';
import { useState } from 'react';
import { useSimulation } from '../context/SimulationContext';
import StatusPanel from '../components/StatusPanel';
import LiveFeed from '../components/LiveFeed';

export default function Dashboard() {
  const { state, feed, triggerEvent, isAutoRunning, setIsAutoRunning, loading, clearFeed, resetSimulation } = useSimulation();

  return (
    <div className="dashboard-layout">
      <header className="dashboard-header glass-panel">
        <h2 className="brand">Simulation Command Center</h2>
        
        <div className="god-mode-controls">
           <button 
             className={`ctrl-btn ${isAutoRunning ? 'active' : ''}`} 
             onClick={() => setIsAutoRunning(true)}
           >▶ AUTO-RUN</button>
           <button className="ctrl-btn" onClick={() => setIsAutoRunning(false)}>⏸ PAUSE</button>
           <button className="ctrl-btn danger" onClick={() => setIsAutoRunning(false)}>⏹ STOP</button>
           <button className="ctrl-btn danger" onClick={() => resetSimulation()} style={{ marginLeft: '12px' }}>⟲ RESET</button>
        </div>

        <div className="header-meta">
          <span className="glow-text-cyan">{isAutoRunning ? 'AUTO-RUNNING' : 'ACTIVE'}</span> | ROUND: {state.round || 0}
        </div>
      </header>
      
      <main className="dashboard-grid">
        <div className="column left-col">
           <StatusPanel state={state} onTrigger={triggerEvent} loading={loading} />
        </div>
        <div className="column right-col">
           <LiveFeed feed={feed} onAgentSelect={() => {}} onClearFeed={clearFeed} />
        </div>
      </main>

      <style jsx>{`
        .dashboard-layout {
          display: flex;
          flex-direction: column;
          height: 100%;
          gap: 16px;
        }
        .dashboard-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 16px 24px;
        }
        .brand {
          font-size: 1rem;
          font-weight: 600;
          color: var(--text-primary);
        }
        .god-mode-controls {
          display: flex;
          gap: 12px;
        }
        .ctrl-btn {
          background: rgba(255,255,255,0.05);
          border: 1px solid rgba(255,255,255,0.1);
          color: var(--text-primary);
          padding: 8px 16px;
          border-radius: 8px;
          cursor: pointer;
          font-family: inherit;
          font-size: 0.8rem;
          font-weight: 600;
          transition: all 0.2s ease;
        }
        .ctrl-btn:hover { 
          background: rgba(255,255,255,0.1); 
        }
        .ctrl-btn.active { 
          background: var(--text-primary); 
          color: var(--bg-color); 
          box-shadow: 0 0 10px rgba(255,255,255,0.2); 
        }
        .ctrl-btn.danger:hover { 
          background: var(--accent-magenta); 
          color: white; 
          box-shadow: 0 0 10px rgba(224, 177, 203, 0.4); 
          border-color: var(--accent-magenta); 
        }
        .header-meta {
          font-size: 0.85rem;
          color: var(--text-secondary);
        }
        .dashboard-grid {
          flex: 1;
          display: grid;
          grid-template-columns: 350px 1fr;
          gap: 24px;
          min-height: 0;
        }
        .column {
          display: flex;
          flex-direction: column;
          gap: 16px;
          height: 100%;
          min-height: 0;
        }
      `}</style>
    </div>
  )
}
