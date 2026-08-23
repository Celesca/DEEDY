'use client';
import dynamic from 'next/dynamic';

const KnowledgeGraphMap = dynamic(() => import('./KnowledgeGraphMap'), {
  ssr: false,
  loading: () => <div style={{ color: 'var(--text-secondary)' }}>Loading Engine...</div>
});

export default function AnalyticsPanel({ falsification = [], clusters = [], fearIndex = [] }) {
  return (
    <>
      <section className="glass-panel analytics-panel">
        <div className="panel-header">
          <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>GLOBAL SENTIMENT</span>
          <span>LIVE</span>
        </div>
        
        <div className="content-padding">
          <h3 className="section-title">FALSIFICATION GAP</h3>
          <p className="subtitle">True vs Expressed Opinion</p>
          
          <div className="charts-container">
            {falsification.length === 0 && <div className="subtitle" style={{ textAlign: 'center', margin: '20px 0' }}>Awaiting data...</div>}
            {falsification.map((data, i) => (
              <div key={i} className="chart-row">
                <div className="topic-name">{data.topic}</div>
                <div className="bar-container">
                  <div className="bar-track">
                    <div className="bar-fill true-fill" style={{ width: `${data.true}%` }}></div>
                  </div>
                  <div className="bar-track">
                    <div className="bar-fill expr-fill" style={{ width: `${data.expr}%` }}></div>
                  </div>
                </div>
                <div className="gap-value">
                  <span style={{ color: Math.abs(data.true - data.expr) > 30 ? 'var(--accent-magenta)' : 'var(--text-secondary)'}}>
                    Δ {Math.abs(data.true - data.expr)}
                  </span>
                </div>
              </div>
            ))}
          </div>
          
          <h3 className="section-title mt-30">FEAR INDEX HEATMAP</h3>
          <p className="subtitle">Social Pressure by Region</p>
          <div className="heatmap-container">
            {fearIndex.length === 0 && <div className="subtitle" style={{ textAlign: 'center', margin: '20px 0' }}>Awaiting data...</div>}
            {fearIndex.map((f, i) => (
              <div key={i} className="heat-row">
                 <span className="heat-label">{f.region}</span>
                 <div className="heat-track">
                   <div className="heat-fill" style={{ 
                     width: `${f.fear}%`, 
                     background: f.fear > 50 ? 'var(--accent-magenta)' : 'var(--accent-cyan)',
                     boxShadow: f.fear > 50 ? '0 0 10px rgba(224, 177, 203, 0.4)' : '0 0 10px rgba(160, 196, 255, 0.4)'
                   }}></div>
                 </div>
                 <span className="heat-val">{f.fear}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Knowledge Graph / Network Map Column */}
      <section className="glass-panel analytics-panel">
        <div className="panel-header">
          <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>KNOWLEDGE GRAPH</span>
          <span>MAPPING</span>
        </div>
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '24px', minHeight: '400px' }}>
          <KnowledgeGraphMap width={500} height={400} />
          <p className="subtitle" style={{ marginTop: '20px', textAlign: 'center' }}>
            GraphRAG entity relationships extracted from seed document.
          </p>
        </div>
      </section>

      <style jsx>{`
        .analytics-panel {
          display: flex;
          flex-direction: column;
          height: 100%;
          overflow: hidden;
        }
        .panel-header {
          padding: 16px 20px;
          border-bottom: 1px solid var(--border-color);
          display: flex;
          justify-content: space-between;
          font-size: 0.85rem;
          color: var(--text-secondary);
        }
        .content-padding {
          padding: 24px 20px;
          overflow-y: auto;
          flex: 1;
        }
        .section-title {
          font-size: 0.9rem;
          color: var(--text-primary);
          letter-spacing: 0.5px;
          margin-bottom: 4px;
        }
        .subtitle {
          font-size: 0.75rem;
          color: var(--text-secondary);
          margin-bottom: 24px;
        }
        .mt-30 { margin-top: 30px; }
        
        .charts-container {
          display: flex;
          flex-direction: column;
          gap: 16px;
        }
        .chart-row {
          display: grid;
          grid-template-columns: 90px 1fr 40px;
          align-items: center;
          gap: 16px;
        }
        .topic-name {
          font-size: 0.8rem;
          color: var(--text-secondary);
        }
        .bar-container {
          display: flex;
          flex-direction: column;
          gap: 6px;
        }
        .bar-track {
          width: 100%;
          height: 6px;
          background: rgba(255,255,255,0.05);
          border-radius: 3px;
          overflow: hidden;
        }
        .bar-fill {
          height: 100%;
          border-radius: 3px;
          transition: width 1s ease-in-out;
        }
        .true-fill { background: var(--text-primary); }
        .expr-fill { background: var(--text-secondary); opacity: 0.7; }
        
        .gap-value {
          font-size: 0.8rem;
          font-family: monospace;
          text-align: right;
        }
        
        .heatmap-container {
          display: flex;
          flex-direction: column;
          gap: 12px;
        }
        .heat-row {
          display: flex;
          align-items: center;
          gap: 16px;
        }
        .heat-label {
          width: 90px;
          font-size: 0.8rem;
          color: var(--text-secondary);
        }
        .heat-track {
          flex: 1;
          height: 8px;
          background: rgba(255,255,255,0.05);
          border-radius: 4px;
          overflow: hidden;
        }
        .heat-fill {
          height: 100%;
          border-radius: 4px;
          transition: width 0.5s ease;
        }
        .heat-val {
          width: 30px;
          font-family: monospace;
          font-size: 0.8rem;
          text-align: right;
          color: var(--text-secondary);
        }
        .mock-node {
          position: absolute;
          width: 8px;
          height: 8px;
          border-radius: 50%;
          background: var(--text-primary);
          box-shadow: 0 0 10px rgba(255,255,255,0.5);
        }
      `}</style>
    </>
  )
}
