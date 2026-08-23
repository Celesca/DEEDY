'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';

export default function SetupPage() {
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const router = useRouter();

  const handleUpload = async (e) => {
    e.preventDefault();
    if (!file) return;

    setLoading(true);
    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await fetch('http://localhost:8000/setup/upload', {
        method: 'POST',
        body: formData,
      });
      const data = await res.json();
      setMessage(data.message);
      
      // Navigate to dashboard after short delay
      setTimeout(() => {
        router.push('/');
      }, 1500);
      
    } catch (err) {
      setMessage('Upload failed. Is the backend running?');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="setup-container">
      <div className="glass-panel setup-panel">
        <h1 className="brand-title">MIROFISH <span className="glow-text-cyan">TH</span></h1>
        <p className="subtitle">Thai Society Simulator - Initial Configuration</p>
        
        <form onSubmit={handleUpload} className="upload-form">
          <div className="form-group">
            <label className="glow-text-magenta">1. Upload Knowledge Graph (PDF/MD)</label>
            <input 
              type="file" 
              accept=".pdf,.md,.txt" 
              onChange={(e) => setFile(e.target.files[0])} 
              className="file-input"
            />
          </div>
          
          <div className="form-group">
            <label className="glow-text-cyan">2. Configure Social Archetypes</label>
            <select className="archetype-select" defaultValue="nso_2023">
              <option value="nso_2023">NSO 2023 Demographics (Default)</option>
              <option value="gen_z_heavy">Gen Z Heavy (Twitter Mode)</option>
              <option value="boomer_heavy">Boomer Heavy (LINE Mode)</option>
            </select>
          </div>
          
          <button type="submit" disabled={!file || loading} className="launch-btn">
            {loading ? 'PROCESSING...' : 'INITIALIZE COMMAND CENTER'}
          </button>
        </form>
        
        {message && <div className="status-msg">{message}</div>}
      </div>

      <style jsx>{`
        .setup-container {
          display: flex;
          align-items: center;
          justify-content: center;
          height: 100vh;
          background: var(--bg-dark);
          color: var(--text-primary);
        }
        .setup-panel {
          width: 500px;
          padding: 40px;
          display: flex;
          flex-direction: column;
          gap: 24px;
          text-align: center;
        }
        .brand-title {
          font-size: 2.5rem;
          letter-spacing: 4px;
          margin: 0;
        }
        .subtitle {
          color: var(--text-secondary);
          font-size: 0.9rem;
          margin-bottom: 20px;
        }
        .upload-form {
          display: flex;
          flex-direction: column;
          gap: 20px;
          text-align: left;
        }
        .form-group {
          display: flex;
          flex-direction: column;
          gap: 8px;
        }
        .form-group label {
          font-size: 0.8rem;
          font-weight: bold;
          letter-spacing: 1px;
        }
        .file-input, .archetype-select {
          background: rgba(0,0,0,0.3);
          border: 1px solid rgba(255,255,255,0.1);
          color: white;
          padding: 10px;
          border-radius: 4px;
          font-family: inherit;
        }
        .launch-btn {
          margin-top: 20px;
          background: var(--accent-magenta);
          color: white;
          border: none;
          padding: 15px;
          font-weight: bold;
          letter-spacing: 2px;
          border-radius: 4px;
          cursor: pointer;
          transition: 0.3s;
        }
        .launch-btn:hover:not(:disabled) {
          box-shadow: 0 0 15px var(--accent-magenta);
        }
        .launch-btn:disabled {
          background: #444;
          color: #888;
          cursor: not-allowed;
        }
        .status-msg {
          margin-top: 15px;
          color: var(--accent-cyan);
          font-size: 0.85rem;
        }
      `}</style>
    </div>
  );
}
