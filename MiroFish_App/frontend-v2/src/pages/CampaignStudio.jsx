import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Rocket, Target, Users, ShieldAlert, Sparkles, AlertTriangle, Database, UserPlus, Loader2 } from 'lucide-react';

export default function CampaignStudio() {
  const navigate = useNavigate();
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [generatedPersonas, setGeneratedPersonas] = useState([]);
  
  const [config, setConfig] = useState({
    name: '',
    businessType: '',
    description: '',
    kolRatio: 5,
    botProbability: 5,
    targetAudience: 'genz',
    totalPopulation: 1000,
    targetPlatforms: ['twitter', 'tiktok', 'facebook', 'instagram'],
  });
  const [maxArchetypes, setMaxArchetypes] = useState(4);

  const handleNext = () => {
    if (step < 4) setStep(step + 1);
  };

  const handleGeneratePersonas = async () => {
    setIsGenerating(true);
    try {
      const res = await fetch('http://127.0.0.1:5001/api/simulation/personas/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...config, max_personas: maxArchetypes })
      });
      const data = await res.json();
      if (res.ok && data.personas && data.personas.length > 0) {
        setGeneratedPersonas(data.personas);
      } else {
        alert(data.error || "Failed to generate personas or received empty data.");
      }
    } catch (e) {
      console.error(e);
      alert("Error calling generator.");
    } finally {
      setIsGenerating(false);
    }
  };

  const handleDeploy = async () => {
    setLoading(true);
    try {
      const payload = { 
        ...config, 
        custom_personas: generatedPersonas,
        total_population: config.totalPopulation
      };
      const res = await fetch('http://127.0.0.1:5001/api/simulation/marketfish/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (res.ok) {
        // Wait 1 second for visual effect, then go to Live Arena
        setTimeout(() => {
          navigate('/live', { state: { sim_id: data.sim_id } });
        }, 1000);
      } else {
        alert("Failed to start simulation");
        setLoading(false);
      }
    } catch (e) {
      console.error(e);
      alert("Error starting simulation. Is backend running?");
      setLoading(false);
    }
  };

  return (
    <div className="flex-col gap-32 mt-24" style={{ maxWidth: '900px', margin: '40px auto' }}>
      
      {/* Studio Header */}
      <div style={{ textAlign: 'center', marginBottom: '16px' }}>
        <h1 className="hero-gradient-text" style={{ fontSize: '42px', marginBottom: '16px' }}>Campaign Studio</h1>
        <p style={{ color: 'var(--text-muted)', fontSize: '18px' }}>
          Configure your social media campaign and inject AI-driven agent swarms.
        </p>
      </div>

      {/* Progress Steps */}
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '24px', position: 'relative' }}>
        <div style={{ position: 'absolute', top: '50%', left: '0', right: '0', height: '2px', background: 'rgba(0,0,0,0.1)', zIndex: 0 }}></div>
        {[1, 2, 3, 4].map(num => (
          <div key={num} style={{
            width: '40px', height: '40px', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center',
            background: step >= num ? 'var(--primary-blue)' : 'var(--bg)',
            color: step >= num ? 'white' : 'var(--text-muted)',
            fontWeight: 'bold', zIndex: 1, border: '2px solid',
            borderColor: step >= num ? 'var(--primary-blue)' : 'var(--border)',
            boxShadow: step >= num ? '0 0 15px rgba(30, 64, 175, 0.5)' : 'none',
            transition: 'all 0.3s'
          }}>
            {num}
          </div>
        ))}
      </div>

      {/* Main Wizard Card */}
      <div className="premium-card">
        
        {step === 1 && (
          <div className="flex-col gap-24 slide-in" style={{ padding: '12px 8px' }}>
            <h2 style={{ display: 'flex', alignItems: 'center', gap: '12px', color: 'var(--text)', fontWeight: '700' }}><UserPlus color="#8b5cf6" /> Target Audience & Personas</h2>
            
            <p style={{ color: 'var(--text-muted)', lineHeight: '1.6' }}>
              Seed your simulation population using real data extracted from Thai social media scraping (DEEDY Dataset).
            </p>
            
            <div style={{ display: 'flex', alignItems: 'center', gap: '16px', marginTop: '12px', marginBottom: '12px' }}>
              <span style={{ fontSize: '14px', fontWeight: 500 }}>Number of Archetypes to extract:</span>
              <select 
                className="premium-input" 
                style={{ width: '100px', padding: '8px 12px' }}
                value={maxArchetypes}
                onChange={e => setMaxArchetypes(parseInt(e.target.value))}
              >
                <option value={4}>4 (Fast)</option>
                <option value={8}>8 (Balanced)</option>
                <option value={12}>12 (Comprehensive)</option>
                <option value={16}>16 (Deep)</option>
              </select>
            </div>
            
            <button 
              className="premium-btn" 
              onClick={handleGeneratePersonas} 
              disabled={isGenerating}
              style={{ width: '100%', background: 'linear-gradient(135deg, #8b5cf6 0%, #6d28d9 100%)', display: 'flex', justifyContent: 'center', gap: '8px' }}
            >
              {isGenerating ? <><Loader2 className="spin" size={18} /> Analyzing Thai Social Data...</> : <><Database size={18} /> Generate Audience from Real Data (DEEDY)</>}
            </button>

            {generatedPersonas.length > 0 && (
              <div style={{ marginTop: '24px', background: 'rgba(0,0,0,0.02)', padding: '24px', borderRadius: '16px', border: '1px solid rgba(0,0,0,0.05)' }}>
                <h3 style={{ marginTop: 0, fontSize: '16px', color: 'var(--text)', marginBottom: '16px' }}>{generatedPersonas.length} Archetypes Generated</h3>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                  {generatedPersonas.map((p, i) => (
                    <div key={i} style={{ background: 'var(--card)', padding: '12px', borderRadius: '8px', border: '1px solid var(--border)', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                      <span style={{ fontWeight: 'bold', color: 'var(--text)' }}>{p.name} <span style={{ fontSize: '12px', color: 'var(--text-muted)', fontWeight: 'normal' }}>({p.age}, {p.occupation})</span></span>
                      <span style={{ fontSize: '12px', color: '#3b82f6' }}>ID: {p.agent_id}</span>
                      <span style={{ fontSize: '13px', color: 'var(--text-muted)', marginTop: '4px', fontStyle: 'italic' }}>"{p.base_personality}"</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {step === 2 && (
          <div className="flex-col gap-24 slide-in" style={{ padding: '12px 8px' }}>
            <h2 style={{ display: 'flex', alignItems: 'center', gap: '12px', color: 'var(--text)', fontWeight: '700' }}><Target color="var(--primary-blue)" /> Define Campaign</h2>
            
            <div className="input-group">
              <label>Campaign Name</label>
              <input 
                type="text" 
                className="premium-input"
                placeholder="e.g. 50% Off Summer Sale" 
                value={config.name}
                onChange={e => setConfig({...config, name: e.target.value})}
              />
            </div>

            <div className="input-group">
              <label>Business Type / Industry</label>
              <input 
                type="text" 
                className="premium-input"
                placeholder="e.g. Tech Startup, Fashion Retail, Fast Food" 
                value={config.businessType}
                onChange={e => setConfig({...config, businessType: e.target.value})}
              />
            </div>

            <div className="input-group">
              <label>Core Message / Post Content</label>
              <textarea 
                className="premium-input"
                placeholder="What is the main text being seeded into the network?"
                value={config.description}
                onChange={e => setConfig({...config, description: e.target.value})}
                style={{ resize: 'none', height: '120px' }}
              />
            </div>

            <div className="input-group mt-12">
              <label>Target Platforms</label>
              <p style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '8px', marginTop: '-4px' }}>
                Select the platforms where agents are allowed to interact. If multiple are selected, agents will choose organically.
              </p>
              <div style={{ display: 'flex', gap: '16px', flexWrap: 'wrap' }}>
                {['twitter', 'tiktok', 'facebook', 'instagram'].map(platform => (
                  <label key={platform} style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '12px 16px', border: '1px solid var(--border)', borderRadius: '8px', cursor: 'pointer', background: 'var(--card)' }}>
                    <input 
                      type="checkbox" 
                      checked={config.targetPlatforms.includes(platform)}
                      onChange={(e) => {
                        const newPlatforms = e.target.checked 
                          ? [...config.targetPlatforms, platform]
                          : config.targetPlatforms.filter(p => p !== platform);
                        setConfig({...config, targetPlatforms: newPlatforms});
                      }}
                      style={{ accentColor: 'var(--primary-blue)', transform: 'scale(1.2)' }}
                    />
                    <span style={{ textTransform: 'capitalize', fontWeight: 600, color: 'var(--text)' }}>
                      {platform === 'tiktok' ? 'TikTok' : platform === 'instagram' ? 'Instagram' : platform}
                    </span>
                  </label>
                ))}
              </div>
            </div>
          </div>
        )}

        {step === 3 && (
          <div className="flex-col gap-24 slide-in" style={{ padding: '12px 8px' }}>
            <h2 style={{ display: 'flex', alignItems: 'center', gap: '12px', color: 'var(--text)', fontWeight: '700' }}><Users color="var(--primary-yellow)" /> Swarm Configuration</h2>
            
            <div className="slider-group">
              <div className="slider-label">
                <span>Total Population Size (ประชากรทั้งหมด)</span>
                <span className="glow-text-orange" style={{ fontWeight: 700 }}>{config.totalPopulation} Agents</span>
              </div>
              <input 
                type="range" 
                min="10" max="500" step="10"
                value={config.totalPopulation}
                onChange={e => setConfig({...config, totalPopulation: parseInt(e.target.value)})}
                style={{ accentColor: 'var(--primary-blue)' }}
              />
              <p style={{ fontSize: '12px', color: 'var(--text-muted)' }}>The number of agents to clone from the generated archetypes.</p>
            </div>

            <div className="slider-group mt-24">
              <div className="slider-label">
                <span>Generative AI KOL Ratio (%)</span>
                <span className="glow-text-orange" style={{ fontWeight: 700 }}>{config.kolRatio}%</span>
              </div>
              <input 
                type="range" 
                min="0" max="100" 
                value={config.kolRatio}
                onChange={e => setConfig({...config, kolRatio: parseInt(e.target.value)})}
                style={{ accentColor: 'var(--primary-yellow)' }}
              />
              <p style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Higher ratio = More complex language generation but slower simulation.</p>
            </div>

            <div className="slider-group mt-24">
              <div className="slider-label">
                <span>Astroturfing / Bot Attack Probability (%)</span>
                <span className="glow-text-red" style={{ fontWeight: 700 }}>{config.botProbability}%</span>
              </div>
              <input 
                type="range" 
                min="0" max="50" 
                value={config.botProbability}
                onChange={e => setConfig({...config, botProbability: parseInt(e.target.value)})}
                style={{ accentColor: '#ff4b4b' }}
              />
              <p style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Simulates automated bot farms generating opposing sentiment to stress test PR.</p>
            </div>
          </div>
        )}

        {step === 4 && (
          <div className="flex-col gap-24 slide-in" style={{ padding: '12px 8px' }}>
            <h2 style={{ display: 'flex', alignItems: 'center', gap: '12px', color: 'var(--text)', fontWeight: '700' }}><ShieldAlert color="#ff4b4b" /> Pre-Flight Checklist</h2>
            
            <div style={{ background: 'rgba(0,0,0,0.02)', padding: '24px', borderRadius: '16px', border: '1px solid rgba(0,0,0,0.05)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '12px' }}>
                <span style={{ color: 'var(--text-muted)' }}>Custom Personas:</span>
                <span style={{ fontWeight: 600, color: '#8b5cf6' }}>{generatedPersonas.length > 0 ? `${generatedPersonas.length} Archetypes loaded` : 'Default Population'}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '12px' }}>
                <span style={{ color: 'var(--text-muted)' }}>Campaign Name:</span>
                <span style={{ fontWeight: 600, color: 'var(--text)' }}>{config.name || 'Untitled Campaign'}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '12px' }}>
                <span style={{ color: 'var(--text-muted)' }}>Business Type:</span>
                <span style={{ fontWeight: 600, color: '#22D3EE' }}>{config.businessType || 'Not specified'}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '12px' }}>
                <span style={{ color: 'var(--text-muted)' }}>Target Platforms:</span>
                <span style={{ fontWeight: 600, color: '#3b82f6', textTransform: 'capitalize' }}>
                  {config.targetPlatforms.length > 0 ? config.targetPlatforms.join(', ') : 'None (Agents cannot post)'}
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '12px' }}>
                <span style={{ color: 'var(--text-muted)' }}>KOL Network:</span>
                <span style={{ fontWeight: 600, color: 'var(--primary-yellow)' }}>{config.kolRatio}% Active</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-muted)' }}>Threat Level:</span>
                <span style={{ fontWeight: 600, color: config.botProbability > 20 ? '#ff4b4b' : '#34d399' }}>
                  {config.botProbability}% Bot Probability
                </span>
              </div>
            </div>

            <div style={{ display: 'flex', gap: '12px', alignItems: 'center', color: 'var(--text-muted)', fontSize: '13px' }}>
              <AlertTriangle size={16} color="#FACC15" />
              Once deployed, you will be redirected to the Live Matrix Arena.
            </div>
          </div>
        )}

        {/* Navigation Buttons */}
        <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '40px', paddingTop: '24px', borderTop: '1px solid rgba(0,0,0,0.05)' }}>
          {step > 1 ? (
            <button className="btn btn-outline" style={{ borderRadius: '20px' }} onClick={() => setStep(step - 1)}>
              Back
            </button>
          ) : <div></div>}

          {step < 4 ? (
            <button 
              className="premium-btn" 
              style={{ 
                width: 'auto', 
                padding: '12px 32px',
                opacity: (step === 1 && generatedPersonas.length === 0) ? 0.5 : 1,
                cursor: (step === 1 && generatedPersonas.length === 0) ? 'not-allowed' : 'pointer'
              }} 
              onClick={handleNext}
              disabled={step === 1 && generatedPersonas.length === 0}
            >
              Next Step
            </button>
          ) : (
            <button className="premium-btn" style={{ width: 'auto', padding: '12px 32px', background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)' }} onClick={handleDeploy} disabled={loading}>
              {loading ? (
                <>Deploying... <Sparkles size={16} className="pulse-badge" /></>
              ) : (
                <><Rocket size={18} /> Deploy Simulation</>
              )}
            </button>
          )}
        </div>
        
      </div>
      
      <style>{`
        .slide-in {
          animation: slideUp 0.5s cubic-bezier(0.16, 1, 0.3, 1) forwards;
          opacity: 0;
        }
        @keyframes slideUp {
          from { opacity: 0; transform: translateY(15px) scale(0.98); }
          to { opacity: 1; transform: translateY(0) scale(1); }
        }
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
        .spin {
          animation: spin 1s linear infinite;
        }
      `}</style>

    </div>
  );
}
