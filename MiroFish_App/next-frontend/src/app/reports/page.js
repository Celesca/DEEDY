'use client';
import { useState } from 'react';
import { useSimulation } from '../../context/SimulationContext';

export default function ReportsPage() {
  const { state, feed } = useSimulation();
  const [generating, setGenerating] = useState(false);
  const [report, setReport] = useState(null);

  const generateReport = () => {
    if (feed.length === 0) {
      alert("Not enough simulation data to generate a report. Run the simulation first.");
      return;
    }
    
    setGenerating(true);
    setReport(null);
    
    // Simulate backend LLM generation delay
    setTimeout(() => {
      setReport({
        title: `MiroFish Trajectory Forecast - Round ${state.round}`,
        date: new Date().toLocaleString(),
        summary: "The injected narrative successfully penetrated the targeted demographic clusters but met unexpected resistance from institutional nodes. Falsification gaps have widened significantly in Region B.",
        risks: [
          "High probability of backlash if narrative frequency increases.",
          "Network topology suggests an emerging counter-narrative cluster."
        ],
        conclusion: "The current scenario trajectory leads to high societal polarization. Recommend pausing event injections and allowing natural diffusion."
      });
      setGenerating(false);
    }, 2500);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', gap: '24px' }}>
      <header className="glass-panel" style={{ padding: '16px 24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h2 style={{ fontSize: '1.1rem', fontWeight: '600' }}>AI Forecast Reports</h2>
        <button 
          className="generate-btn" 
          onClick={generateReport}
          disabled={generating}
        >
          {generating ? 'ANALYZING TRAJECTORIES...' : 'GENERATE FORECAST'}
        </button>
      </header>
      
      <main className="glass-panel" style={{ flex: 1, padding: '32px', overflowY: 'auto', minHeight: 0 }}>
        {!report && !generating && (
          <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-secondary)' }}>
            Click "Generate Forecast" to analyze the current simulation trajectory using GraphRAG.
          </div>
        )}
        
        {generating && (
          <div className="loading-state">
            <div className="spinner"></div>
            <p>Synthesizing agent interactions and extracting network topology...</p>
          </div>
        )}

        {report && (
          <div className="report-content">
            <h1 className="report-title">{report.title}</h1>
            <p className="report-date">{report.date}</p>
            
            <div className="report-section">
              <h3>EXECUTIVE SUMMARY</h3>
              <p>{report.summary}</p>
            </div>
            
            <div className="report-section">
              <h3>EMERGING RISKS</h3>
              <ul>
                {report.risks.map((r, i) => <li key={i}>{r}</li>)}
              </ul>
            </div>
            
            <div className="report-section">
              <h3>CONCLUSION</h3>
              <p>{report.conclusion}</p>
            </div>
          </div>
        )}
      </main>

      <style jsx>{`
        .generate-btn {
          background: var(--text-primary);
          color: var(--bg-color);
          border: none;
          padding: 8px 24px;
          border-radius: 8px;
          font-weight: 600;
          font-family: inherit;
          cursor: pointer;
          transition: 0.2s;
        }
        .generate-btn:hover:not(:disabled) {
          transform: translateY(-1px);
          box-shadow: 0 4px 12px rgba(255,255,255,0.2);
        }
        .generate-btn:disabled {
          background: rgba(255,255,255,0.1);
          color: var(--text-secondary);
          cursor: wait;
        }
        
        .loading-state {
          height: 100%;
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          gap: 16px;
          color: var(--text-secondary);
        }
        .spinner {
          width: 40px;
          height: 40px;
          border: 3px solid rgba(255,255,255,0.1);
          border-top-color: var(--accent-cyan);
          border-radius: 50%;
          animation: spin 1s linear infinite;
        }
        @keyframes spin { 100% { transform: rotate(360deg); } }
        
        .report-content {
          max-width: 800px;
          margin: 0 auto;
          animation: fadeUp 0.5s ease;
        }
        @keyframes fadeUp {
          from { opacity: 0; transform: translateY(10px); }
          to { opacity: 1; transform: translateY(0); }
        }
        .report-title {
          font-size: 1.8rem;
          color: var(--text-primary);
          margin-bottom: 8px;
        }
        .report-date {
          font-family: monospace;
          color: var(--text-secondary);
          margin-bottom: 40px;
          border-bottom: 1px solid var(--border-color);
          padding-bottom: 16px;
        }
        .report-section {
          margin-bottom: 32px;
        }
        .report-section h3 {
          font-size: 0.85rem;
          color: var(--accent-cyan);
          letter-spacing: 1px;
          margin-bottom: 12px;
        }
        .report-section p, .report-section li {
          color: var(--text-primary);
          line-height: 1.6;
          font-size: 1rem;
        }
        .report-section ul {
          padding-left: 20px;
        }
        .report-section li {
          margin-bottom: 8px;
        }
      `}</style>
    </div>
  );
}
