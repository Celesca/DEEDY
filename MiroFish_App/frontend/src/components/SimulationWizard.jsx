import React, { useState } from 'react';
import './InputPanel.css'; // Reuse existing styles

const SimulationWizard = ({ onSimulationStart }) => {
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);

  // Step 1 State
  const [objective, setObjective] = useState('Brand Awareness');
  const [brandVoice, setBrandVoice] = useState('Casual');
  const [companyDesc, setCompanyDesc] = useState('');

  // Step 2 State
  const [content, setContent] = useState('');
  const [platforms, setPlatforms] = useState({ X: true, Facebook: false, TikTok: false, Instagram: false });

  // Step 3 State
  const [genZ, setGenZ] = useState(50);
  const [genY, setGenY] = useState(30);
  const [genX, setGenX] = useState(20);
  const [preBias, setPreBias] = useState('Neutral');
  const [agents, setAgents] = useState(1000);
  const [useKol, setUseKol] = useState(false);
  const [ioMode, setIoMode] = useState('None');

  const handleDemoChange = (type, value) => {
    let z = genZ, y = genY, x = genX;
    if (type === 'Z') {
      z = value;
      const rem = 100 - z;
      const totalOther = y + x || 1;
      y = Math.round((y / totalOther) * rem);
      x = rem - y;
    } else if (type === 'Y') {
      y = value;
      const rem = 100 - y;
      const totalOther = z + x || 1;
      z = Math.round((z / totalOther) * rem);
      x = rem - z;
    } else if (type === 'X') {
      x = value;
      const rem = 100 - x;
      const totalOther = z + y || 1;
      z = Math.round((z / totalOther) * rem);
      y = rem - z;
    }
    setGenZ(z); setGenY(y); setGenX(x);
  };

  const availablePlatforms = ['X', 'Facebook', 'TikTok', 'Instagram'];
  const handlePlatformChange = (p) => setPlatforms(prev => ({ ...prev, [p]: !prev[p] }));

  const handleSubmit = async (e) => {
    e.preventDefault();
    const selectedPlatforms = Object.keys(platforms).filter(k => platforms[k]);
    if (selectedPlatforms.length === 0 || !content.trim() || !companyDesc.trim()) return;

    setLoading(true);
    try {
      const payload = {
        objective,
        brand_voice: brandVoice,
        company_description: companyDesc,
        post_content: content,
        platforms: selectedPlatforms,
        demographics: { "Gen Z": genZ, "Gen Y": genY, "Gen X": genX },
        pre_bias: preBias,
        agent_count: agents,
        use_kol: useKol,
        io_mode: ioMode
      };

      const response = await fetch('http://localhost:8000/api/v1/simulate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
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
    <div className="wizard-container" style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* Wizard Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '24px', fontSize: '0.9rem', fontWeight: 'bold' }}>
        <span style={{ color: step >= 1 ? 'var(--accent-color)' : 'var(--text-secondary)' }}>1. Brief</span>
        <span style={{ color: step >= 2 ? 'var(--accent-color)' : 'var(--text-secondary)' }}>2. Content</span>
        <span style={{ color: step >= 3 ? 'var(--accent-color)' : 'var(--text-secondary)' }}>3. Audience</span>
      </div>

      <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '20px', flex: 1 }}>
        
        {step === 1 && (
          <div className="wizard-step fade-in">
            <div className="input-group">
              <label className="input-label">Campaign Objective</label>
              <select className="premium-input premium-select" value={objective} onChange={e => setObjective(e.target.value)}>
                <option>Brand Awareness</option>
                <option>Sales Conversion</option>
                <option>Damage Control</option>
              </select>
            </div>
            <div className="input-group">
              <label className="input-label">Brand Voice</label>
              <select className="premium-input premium-select" value={brandVoice} onChange={e => setBrandVoice(e.target.value)}>
                <option>Formal / Corporate</option>
                <option>Casual / Friendly</option>
                <option>Teen / Slang (Gen Z)</option>
              </select>
            </div>
            <div className="input-group">
              <label className="input-label">Company Profile</label>
              <textarea 
                className="premium-input"
                placeholder="Describe your brand..."
                value={companyDesc}
                onChange={e => setCompanyDesc(e.target.value)}
                required
                style={{ minHeight: '100px' }}
              />
            </div>
          </div>
        )}

        {step === 2 && (
          <div className="wizard-step fade-in">
            <div className="input-group">
              <label className="input-label">Target Platforms</label>
              <div className="checkbox-group">
                {availablePlatforms.map(p => (
                  <label key={p} className="checkbox-label">
                    <input type="checkbox" checked={platforms[p]} onChange={() => handlePlatformChange(p)} />
                    {p}
                  </label>
                ))}
              </div>
            </div>
            <div className="input-group">
              <label className="input-label">Caption Box</label>
              <textarea 
                className="premium-input"
                placeholder="Type your caption..."
                value={content}
                onChange={e => setContent(e.target.value)}
                required
                style={{ minHeight: '120px' }}
              />
            </div>
          </div>
        )}

        {step === 3 && (
          <div className="wizard-step fade-in">
            <div className="input-group">
              <label className="input-label">Demographics Mix (Total: {genZ + genY + genX}%)</label>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginBottom: '16px' }}>
                <label style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Gen Z: {genZ}%</label>
                <input type="range" min="0" max="100" value={genZ} onChange={e => handleDemoChange('Z', Number(e.target.value))} />
                
                <label style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Gen Y: {genY}%</label>
                <input type="range" min="0" max="100" value={genY} onChange={e => handleDemoChange('Y', Number(e.target.value))} />
                
                <label style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Gen X/Boomer: {genX}%</label>
                <input type="range" min="0" max="100" value={genX} onChange={e => handleDemoChange('X', Number(e.target.value))} />
              </div>
            </div>
            
            <div className="input-group">
              <label className="input-label">Pre-Existing Bias</label>
              <select className="premium-input premium-select" value={preBias} onChange={e => setPreBias(e.target.value)}>
                <option>Neutral (Blank Slate)</option>
                <option>Active Crisis (Negative)</option>
                <option>Brand Love (Positive)</option>
              </select>
            </div>
            
            <div className="input-group">
              <label className="input-label">Astroturfing / IO (Bot Injection)</label>
              <select className="premium-input premium-select" value={ioMode} onChange={e => setIoMode(e.target.value)}>
                <option value="None">None (Organic only)</option>
                <option value="Positive IO">Positive IO (Praise bots)</option>
                <option value="Negative IO">Negative IO (Attack bots)</option>
              </select>
            </div>

            <div className="input-group">
              <label className="input-label">KOL Injection</label>
              <label className="checkbox-label" style={{ padding: '10px', border: '1px solid #334155', borderRadius: '8px' }}>
                <input type="checkbox" checked={useKol} onChange={e => setUseKol(e.target.checked)} />
                Seed directly to Top Influencers (Bypass FYP chance)
              </label>
            </div>
            
            <div className="input-group" style={{ marginTop: '16px' }}>
              <label className="input-label">Agent Scale: {agents}</label>
              <input type="range" min="100" max="10000" step="100" value={agents} onChange={e => setAgents(Number(e.target.value))} />
            </div>
          </div>
        )}

        <div style={{ marginTop: 'auto', paddingTop: '20px' }}></div>

        {/* Navigation Buttons */}
        <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '10px' }}>
          {step > 1 ? (
            <button type="button" className="btn-secondary" onClick={() => setStep(step - 1)} style={{ padding: '8px 16px', background: 'transparent', border: '1px solid var(--panel-border)', color: 'white', borderRadius: '6px', cursor: 'pointer' }}>
              Back
            </button>
          ) : <div></div>}

          {step < 3 ? (
            <button type="button" className="btn-primary" onClick={() => setStep(step + 1)} style={{ padding: '8px 16px', background: 'var(--accent-color)', color: 'black', border: 'none', borderRadius: '6px', cursor: 'pointer', fontWeight: 'bold' }}>
              Next Step
            </button>
          ) : (
            <button type="submit" className="btn-primary btn-launch" disabled={loading} style={{ padding: '8px 16px', background: 'linear-gradient(135deg, var(--accent-color), #0077ff)', color: 'white', border: 'none', borderRadius: '6px', cursor: 'pointer', fontWeight: 'bold' }}>
              {loading ? 'Initializing...' : 'Launch Simulation'}
            </button>
          )}
        </div>
      </form>
    </div>
  );
};

export default SimulationWizard;
