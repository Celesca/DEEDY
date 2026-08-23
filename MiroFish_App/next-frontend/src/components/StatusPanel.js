'use client';
import { useState } from 'react';

export default function StatusPanel({ state, onTrigger, loading }) {
  const [eventInput, setEventInput] = useState('');

  const handleTrigger = () => {
    if (eventInput.trim() && !loading) {
      onTrigger(eventInput);
      setEventInput('');
    }
  };

  return (
    <section className="glass-panel status-panel">
      <div className="panel-header">
        <span>SIMULATION HEALTH</span>
        <span>{loading ? 'PROCESSING...' : 'READY'}</span>
      </div>
      
      <div className="metrics">
        <div className="gauge">
          <div className="arc cyan"></div>
          <div className="val">{state.population > 0 ? '94%' : '0%'}</div>
          <div className="lbl">STABILITY</div>
        </div>
        <div className="gauge">
          <div className="arc magenta"></div>
          <div className="val">{loading ? '120ms' : '14ms'}</div>
          <div className="lbl">LATENCY</div>
        </div>
      </div>
      
      <div className="stats">
        <div className="stat-item">
          <div className="stat-label">POPULATION</div>
          <div className="stat-value glow-text-cyan">{state.population}</div>
        </div>
      </div>

      <div className="action-area">
        <input 
          type="text" 
          placeholder="Inject an event..." 
          value={eventInput}
          onChange={(e) => setEventInput(e.target.value)}
          disabled={loading}
          onKeyDown={(e) => e.key === 'Enter' && handleTrigger()}
        />
        <button onClick={handleTrigger} disabled={loading || !eventInput.trim()}>
          {loading ? 'BROADCASTING...' : 'TRIGGER EVENT'}
        </button>
      </div>

      <style jsx>{`
        .status-panel {
          display: flex;
          flex-direction: column;
          flex: 1;
        }
        .metrics {
          display: flex;
          justify-content: space-around;
          padding: 30px 10px;
          border-bottom: 1px solid var(--border-color);
        }
        .gauge {
          display: flex;
          flex-direction: column;
          align-items: center;
          position: relative;
        }
        .arc {
          width: 80px;
          height: 40px;
          border-top-left-radius: 90px;
          border-top-right-radius: 90px;
          border: 6px solid #333;
          border-bottom: 0;
          position: relative;
        }
        .arc.cyan { border-color: var(--accent-cyan); box-shadow: 0 0 10px var(--accent-cyan), inset 0 0 10px var(--accent-cyan); }
        .arc.magenta { border-color: var(--accent-magenta); box-shadow: 0 0 10px var(--accent-magenta), inset 0 0 10px var(--accent-magenta); }
        .val { font-size: 1.5rem; font-weight: bold; margin-top: 10px; }
        .lbl { font-size: 0.7rem; color: var(--text-secondary); letter-spacing: 1px; }
        
        .stats { padding: 20px; display: flex; flex-direction: column; gap: 15px; border-bottom: 1px solid var(--border-color); }
        .stat-item { display: flex; justify-content: space-between; align-items: center; }
        .stat-label { font-size: 0.8rem; color: var(--text-secondary); }
        .stat-value { font-size: 1.2rem; font-weight: 600; }
        
        .action-area {
          padding: 20px;
          display: flex;
          flex-direction: column;
          gap: 12px;
        }
        input {
          background: rgba(255,255,255,0.05);
          border: 1px solid var(--border-color);
          padding: 12px;
          color: white;
          border-radius: 4px;
          outline: none;
        }
        input:focus { border-color: var(--accent-cyan); }
        button {
          background: var(--accent-magenta);
          color: white;
          border: none;
          padding: 12px;
          font-weight: bold;
          border-radius: 4px;
          cursor: pointer;
          transition: all 0.2s;
        }
        button:hover:not(:disabled) {
          box-shadow: 0 0 15px var(--accent-magenta);
        }
        button:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }
      `}</style>
    </section>
  )
}
