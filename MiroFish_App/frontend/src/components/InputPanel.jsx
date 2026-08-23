import React, { useState } from 'react';
import './InputPanel.css';

const InputPanel = ({ onSimulationStart }) => {
  const [companyDesc, setCompanyDesc] = useState('');
  const [content, setContent] = useState('');
  const [platforms, setPlatforms] = useState({ X: true, Facebook: false, TikTok: false, Instagram: false });
  const [agents, setAgents] = useState(1000);
  const [loading, setLoading] = useState(false);

  const availablePlatforms = ['X', 'Facebook', 'TikTok', 'Instagram'];

  const handlePlatformChange = (p) => {
    setPlatforms(prev => ({ ...prev, [p]: !prev[p] }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!content.trim() || !companyDesc.trim()) return;

    const selectedPlatforms = Object.keys(platforms).filter(k => platforms[k]);
    if (selectedPlatforms.length === 0) return; // Need at least one

    setLoading(true);
    try {
      const response = await fetch('http://localhost:8000/api/v1/simulate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          company_description: companyDesc,
          post_content: content,
          platforms: selectedPlatforms,
          agent_count: agents
        })
      });
      const data = await response.json();
      onSimulationStart(data.campaign_id);
    } catch (error) {
      console.error('Failed to start simulation:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <form className="input-form-container" onSubmit={handleSubmit}>
      
      <div className="input-group">
        <label className="input-label">Company / Brand Profile</label>
        <textarea 
          className="premium-input"
          placeholder="Briefly describe your company (e.g., A luxury skincare brand...)"
          value={companyDesc}
          onChange={(e) => setCompanyDesc(e.target.value)}
          required
          style={{ minHeight: '60px' }}
        />
      </div>

      <div className="input-group">
        <label className="input-label">The Campaign Post</label>
        <textarea 
          className="premium-input"
          placeholder="Type your caption here (e.g. New Product Launch! 🚀)"
          value={content}
          onChange={(e) => setContent(e.target.value)}
          required
        />
      </div>

      <div className="input-group">
        <label className="input-label">Target Platforms</label>
        <div className="checkbox-group">
          {availablePlatforms.map(p => (
            <label key={p} className="checkbox-label">
              <input 
                type="checkbox" 
                checked={platforms[p]} 
                onChange={() => handlePlatformChange(p)}
              />
              {p}
            </label>
          ))}
        </div>
      </div>

      <div className="input-group">
        <label className="input-label">Agent Reach Scale</label>
        <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
          <input 
            type="range" 
            min="100" 
            max="10000" 
            step="100"
            value={agents}
            onChange={(e) => setAgents(Number(e.target.value))}
            style={{ flex: 1, accentColor: 'var(--accent-color)' }}
          />
          <span style={{ color: 'var(--accent-color)', fontWeight: 600, width: '60px', textAlign: 'right' }}>
            {agents}
          </span>
        </div>
      </div>

      <button type="submit" className="btn-primary btn-launch" disabled={loading || !content.trim()}>
        {loading ? 'Initializing Engine...' : 'Launch Simulation'}
      </button>

    </form>
  );
};

export default InputPanel;
