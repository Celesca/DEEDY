import React, { useEffect, useState } from 'react';
import { LineChart, Line, PieChart, Pie, Cell, ResponsiveContainer, XAxis, YAxis, Tooltip, CartesianGrid } from 'recharts';
import './AnalystReport.css';

const COLORS = ['#3b82f6', '#10b981', '#6366f1'];

const AnalystReport = ({ campaignId }) => {
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!campaignId) return;

    setLoading(true);
    
    const interval = setInterval(async () => {
      try {
        const response = await fetch(`http://localhost:8000/api/v1/report/${campaignId}`);
        const data = await response.json();
        
        if (data.status !== 'processing') {
          setReport(data);
          setLoading(false);
          clearInterval(interval);
        }
      } catch (err) {
        console.error("Failed to fetch report", err);
      }
    }, 2000); // poll every 2 seconds

    return () => clearInterval(interval);
  }, [campaignId]);

  if (!campaignId) {
    return (
      <div style={{ display: 'flex', height: '100%', alignItems: 'center', justifyContent: 'center' }}>
        <p style={{ color: 'var(--text-secondary)' }}>Launch a campaign to see the scorecard.</p>
      </div>
    );
  }

  if (loading || !report) {
    return (
      <div style={{ display: 'flex', height: '100%', alignItems: 'center', justifyContent: 'center', flexDirection: 'column' }}>
        <div style={{ color: 'var(--accent-color)', marginBottom: '8px' }}>Processing...</div>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>Gemini is analyzing the simulation data.</p>
      </div>
    );
  }

  return (
    <div className="report-container">
      <div className="scorecard">
        <div className="metric-box">
          <span className="metric-label">Viral Score</span>
          <span className="metric-value viral">{report.viral_score}</span>
        </div>
        <div className="metric-box">
          <span className="metric-label">Brand Sentiment</span>
          <span className="metric-value positive">{report.sentiment_shift}</span>
        </div>
      </div>
      
      <div style={{ display: 'flex', gap: '16px', marginTop: '20px', height: '180px' }}>
        <div style={{ flex: 2, background: 'rgba(255,255,255,0.02)', padding: '10px', borderRadius: '8px', border: '1px solid #1e293b' }}>
          <h4 style={{ fontSize: '0.75rem', color: '#94a3b8', marginBottom: '8px', fontWeight: '500' }}>SENTIMENT TIMELINE</h4>
          <ResponsiveContainer width="100%" height="85%">
            <LineChart data={report.sentiment_timeline?.map((val, idx) => ({ tick: idx+1, sentiment: val })) || []}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="tick" stroke="#64748b" fontSize={10} tickLine={false} axisLine={false} />
              <YAxis stroke="#64748b" fontSize={10} domain={[-1, 1]} tickLine={false} axisLine={false} />
              <Tooltip contentStyle={{ background: '#0f172a', border: '1px solid #334155', borderRadius: '6px' }} />
              <Line type="monotone" dataKey="sentiment" stroke="#10b981" strokeWidth={2} dot={{ r: 3, fill: '#10b981' }} />
            </LineChart>
          </ResponsiveContainer>
        </div>
        <div style={{ flex: 1, background: 'rgba(255,255,255,0.02)', padding: '10px', borderRadius: '8px', border: '1px solid #1e293b', display: 'flex', flexDirection: 'column' }}>
          <h4 style={{ fontSize: '0.75rem', color: '#94a3b8', marginBottom: '8px', fontWeight: '500' }}>ENGAGEMENT MIX</h4>
          <ResponsiveContainer width="100%" height="85%">
            <PieChart>
              <Pie
                data={[
                  { name: 'Likes', value: report.engagement_mix?.likes || 0 },
                  { name: 'Shares', value: report.engagement_mix?.shares || 0 },
                  { name: 'Comments', value: report.engagement_mix?.comments || 0 }
                ]}
                cx="50%" cy="50%" innerRadius={25} outerRadius={45} fill="#8884d8" paddingAngle={2} dataKey="value"
              >
                { [0, 1, 2].map((entry, index) => <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />) }
              </Pie>
              <Tooltip contentStyle={{ background: '#0f172a', border: '1px solid #334155', borderRadius: '6px' }} />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>
      
      <div className="analyst-summary" style={{ marginTop: '20px' }}>
        <div className="analyst-badge">Gemini-3.6-Flash Insights</div>
        <p>{report.analyst_summary}</p>
      </div>
    </div>
  );
};

export default AnalystReport;
