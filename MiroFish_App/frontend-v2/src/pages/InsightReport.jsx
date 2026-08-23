import React, { useContext, useState, useEffect } from 'react';
import { AppContext } from '../App';
import { AgGridReact } from 'ag-grid-react';
import { Download, Sparkles, TrendingUp, AlertTriangle, ShieldCheck, Zap, Server } from 'lucide-react';
import { useLocation } from 'react-router-dom';
import { ModuleRegistry, AllCommunityModule, themeAlpine } from 'ag-grid-community';
import 'ag-grid-community/styles/ag-grid.css';

// Register AG Grid modules
ModuleRegistry.registerModules([AllCommunityModule]);

const API_BASE_URL = 'http://127.0.0.1:5001/api/simulation';

export default function InsightReport() {
  const { isAdvanced } = useContext(AppContext);
  const location = useLocation();
  const SIM_ID = location.state?.sim_id || 'thai_society';

  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [viewMode, setViewMode] = useState('executive'); // 'executive' or 'analyst'

  useEffect(() => {
    const fetchReport = async () => {
      try {
        setLoading(true);
        const res = await fetch(`${API_BASE_URL}/${SIM_ID}/report`);
        if (!res.ok) throw new Error('API Error or Data Not Found');
        const data = await res.json();
        setReport(data.report || data);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };
    
    fetchReport();
  }, [SIM_ID]);

  const columnDefs = [
    { field: 'timestamp', headerName: 'Timestamp', width: 160 },
    { field: 'agentId', headerName: 'Agent/Bot ID', width: 140 },
    { field: 'stance', headerName: 'Stance', width: 120, cellStyle: params => ({
      color: params.value === 'Opposing' ? 'var(--primary-red)' : params.value === 'Supporting' ? 'var(--green)' : 'var(--text-muted)',
      fontWeight: '600'
    })},
    { field: 'content', headerName: 'Trace Content', flex: 1 },
  ];

  if (loading) {
    return (
      <div className="flex-col gap-24 mt-24" style={{ alignItems: 'center', justifyContent: 'center', height: '60vh' }}>
        <div style={{ position: 'relative' }}>
           <Sparkles size={64} color="var(--primary-blue)" className="pulse-badge" style={{ animation: 'pulse 2s infinite' }} />
           <div style={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)', width: '120px', height: '120px', borderRadius: '50%', border: '2px solid rgba(30, 64, 175, 0.2)', borderTopColor: 'var(--primary-blue)', animation: 'spin 1s linear infinite' }}></div>
        </div>
        <h2 className="hero-gradient-text" style={{ marginTop: '24px' }}>AI Marketing Advisor is analyzing campaign data...</h2>
      </div>
    );
  }

  if (error || !report) {
    return (
      <div className="flex-col gap-24 mt-24" style={{ alignItems: 'center', justifyContent: 'center', height: '60vh' }}>
        <AlertTriangle size={64} color="var(--primary-red)" />
        <h2 className="glow-text-red">Report Not Found</h2>
        <p style={{ color: 'var(--text-muted)' }}>{error || "No data available for this simulation."}</p>
      </div>
    );
  }

  const getRiskClass = () => {
    if (report.risk_score >= 7) return 'high-risk';
    if (report.risk_score >= 4) return 'medium-risk';
    return 'low-risk';
  };

  const getRiskColor = () => {
    if (report.risk_score >= 7) return 'glow-text-red';
    if (report.risk_score >= 4) return 'glow-text-orange';
    return 'glow-text-green';
  };

  const renderExecutiveView = () => (
    <>
      <div className="grid-2">
        {/* Storytelling Section */}
        <div className="premium-card">
          <h2 style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '24px', color: 'var(--text)' }}>
            <TrendingUp size={24} color="var(--primary-yellow)" /> 
            Executive Summary
          </h2>
          <p style={{ fontSize: '15px', lineHeight: 1.8, color: 'var(--text)' }}>
            {report.summary}
          </p>
          
          <div style={{ marginTop: '32px' }}>
            <h3 style={{ color: 'var(--text-muted)', fontSize: '14px', textTransform: 'uppercase', letterSpacing: '1px' }}>Representative Sentiment Quotes</h3>
            
            <div className="premium-quote" style={{ borderLeft: '4px solid #ff4b4b' }}>
              <div style={{ fontSize: '15px', fontStyle: 'italic', color: 'var(--text)', marginBottom: '12px', lineHeight: 1.6 }}>
                "{report.quotes?.negative?.text}"
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--text-muted)', fontSize: '13px' }}>
                <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--primary-red)' }}></div>
                {report.quotes?.negative?.author}
              </div>
            </div>

            <div className="premium-quote" style={{ borderLeft: '4px solid #34d399' }}>
              <div style={{ fontSize: '15px', fontStyle: 'italic', color: 'var(--text)', marginBottom: '12px', lineHeight: 1.6 }}>
                "{report.quotes?.positive?.text}"
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--text-muted)', fontSize: '13px' }}>
                <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--green)' }}></div>
                {report.quotes?.positive?.author}
              </div>
            </div>
          </div>
        </div>

        {/* Dynamic Right Side: Stance + Next Best Actions */}
        <div className="flex-col gap-32">
          
          {/* Actionability: Next Best Actions */}
          <div className="premium-card" style={{ border: '1px solid rgba(59, 130, 246, 0.2)', background: 'linear-gradient(180deg, rgba(255,255,255,0.8) 0%, rgba(219, 234, 254, 0.4) 100%)' }}>
            <h2 style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '24px', color: 'var(--text)' }}>
              <Zap size={24} color="var(--primary-blue)" />
              AI Next Best Actions
            </h2>
            <div className="flex-col gap-16">
              {[
                "Deploy proactive clarification message addressing bot-driven misinformation immediately.",
                "Engage directly with Top 3 organic opposing KOLs to build authentic bridge narratives.",
                "Monitor 'Neutral' demographic closely; they currently show high susceptibility to astroturfing."
              ].map((action, i) => (
                <div key={i} style={{ display: 'flex', gap: '16px', background: 'rgba(0,0,0,0.02)', padding: '16px', borderRadius: '12px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', width: '28px', height: '28px', borderRadius: '50%', background: 'rgba(30, 64, 175, 0.2)', color: 'var(--primary-blue)', fontWeight: 'bold', fontSize: '12px', flexShrink: 0 }}>
                    {i+1}
                  </div>
                  <div style={{ color: 'var(--text)', fontSize: '14px', lineHeight: 1.5 }}>
                    {action}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Stance Breakdown */}
          <div className="premium-card">
            <h2 style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '32px', color: 'var(--text)' }}>
              <ShieldCheck size={24} color="#22D3EE" />
              Stance Breakdown
            </h2>
            <div className="flex-col gap-24">
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '12px', fontSize: '15px', fontWeight: 600 }}>
                  <span style={{ color: 'var(--primary-red)' }}>Opposing</span> 
                  <span className="glow-text-red">{report.stats.negative}%</span>
                </div>
                <div className="gradient-bar-bg">
                  <div className="gradient-bar-fill" style={{ width: `${report.stats.negative}%`, background: 'linear-gradient(90deg, #991b1b, #ef4444)' }}></div>
                </div>
              </div>
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '12px', fontSize: '15px', fontWeight: 600 }}>
                  <span style={{ color: 'var(--text-muted)' }}>Neutral</span> 
                  <span style={{ color: 'var(--text)' }}>{report.stats.neutral}%</span>
                </div>
                <div className="gradient-bar-bg">
                  <div className="gradient-bar-fill" style={{ width: `${report.stats.neutral}%`, background: 'linear-gradient(90deg, #475569, #94a3b8)' }}></div>
                </div>
              </div>
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '12px', fontSize: '15px', fontWeight: 600 }}>
                  <span style={{ color: 'var(--green)' }}>Supporting</span> 
                  <span className="glow-text-green">{report.stats.positive}%</span>
                </div>
                <div className="gradient-bar-bg">
                  <div className="gradient-bar-fill" style={{ width: `${report.stats.positive}%`, background: 'linear-gradient(90deg, #065f46, #10b981)' }}></div>
                </div>
              </div>
            </div>
          </div>

        </div>
      </div>
    </>
  );

  const renderAnalystView = () => (
    <div className="premium-card" style={{ height: '700px', display: 'flex', flexDirection: 'column', padding: '32px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <div>
          <h2 style={{ margin: 0, color: 'var(--text)', display: 'flex', alignItems: 'center', gap: '12px' }}>
            <Server size={24} color="var(--primary-blue)" />
            Audit Logs & Raw Trace Data
          </h2>
          <p style={{ color: 'var(--text-muted)', fontSize: '14px', marginTop: '4px' }}>High-density verifiable ground truth for Data Analysts.</p>
        </div>
        <button className="btn btn-outline" style={{ borderRadius: '20px' }}>
          <Download size={14} /> Export CSV
        </button>
      </div>
      
      {/* Dark theme override for AgGrid */}
      <div className="ag-theme-alpine" style={{ flex: 1, width: '100%', borderRadius: '12px', overflow: 'hidden' }}>
        <style>{`
          .ag-theme-alpine {
            font-size: 13px;
          }
        `}</style>
        <AgGridReact 
          theme={themeAlpine}
          rowData={report.trace_data || []} 
          columnDefs={columnDefs} 
          defaultColDef={{ resizable: true, filter: true, sortable: true }} 
          pagination={true} 
          paginationPageSize={20} 
          domLayout='normal'
        />
      </div>
    </div>
  );

  return (
    <div className="flex-col gap-32 mt-24" style={{ paddingBottom: '40px' }}>
      
      {/* Premium Header with Role Toggle */}
      <div className="premium-card" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '32px 40px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '8px' }}>
            <Sparkles size={24} color="var(--primary-blue)" />
            <h1 className="hero-gradient-text" style={{ margin: 0 }}>AI Marketing Advisor Insight</h1>
          </div>
          
          <div style={{ display: 'flex', gap: '16px', marginTop: '16px' }}>
            <button 
              onClick={() => setViewMode('executive')}
              style={{ background: viewMode === 'executive' ? 'rgba(30, 64, 175, 0.2)' : 'transparent', border: '1px solid', borderColor: viewMode === 'executive' ? 'var(--primary-blue)' : 'var(--border)', color: viewMode === 'executive' ? 'var(--primary-blue)' : 'var(--text-muted)', padding: '8px 16px', borderRadius: '20px', cursor: 'pointer', transition: 'all 0.2s', fontSize: '13px', fontWeight: 600 }}
            >
              Executive View
            </button>
            <button 
              onClick={() => setViewMode('analyst')}
              style={{ background: viewMode === 'analyst' ? 'rgba(30, 64, 175, 0.2)' : 'transparent', border: '1px solid', borderColor: viewMode === 'analyst' ? 'var(--primary-blue)' : 'var(--border)', color: viewMode === 'analyst' ? 'var(--primary-blue)' : 'var(--text-muted)', padding: '8px 16px', borderRadius: '20px', cursor: 'pointer', transition: 'all 0.2s', fontSize: '13px', fontWeight: 600 }}
            >
              Analyst View
            </button>
          </div>
        </div>
        
        <div style={{ display: 'flex', alignItems: 'center', gap: '24px' }}>
          <div style={{ textAlign: 'right' }}>
            <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-muted)', letterSpacing: '1px' }}>PR CRISIS RISK</div>
            <div className={getRiskColor()} style={{ fontSize: '24px', fontWeight: 700, marginTop: '4px' }}>
              {report.risk_label}
            </div>
          </div>
          <div className={`stat-circle ${getRiskClass()}`}>
            <div className={`stat-value ${getRiskColor()}`}>{report.risk_score}</div>
            <div className="stat-label">/ 10</div>
          </div>
        </div>
      </div>

      {viewMode === 'executive' ? renderExecutiveView() : renderAnalystView()}

    </div>
  );
}
