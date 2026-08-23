import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ShieldCheck, Lock, Activity, ArrowRight } from 'lucide-react';

export default function Login({ onLogin }) {
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleLogin = (e) => {
    e.preventDefault();
    setLoading(true);
    // Simulate enterprise SSO login delay
    setTimeout(() => {
      onLogin();
      navigate('/studio');
    }, 1200);
  };

  return (
    <div style={{
      height: '100vh',
      width: '100vw',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: 'radial-gradient(circle at center, #0f172a 0%, #020617 100%)',
      position: 'relative',
      overflow: 'hidden'
    }}>
      {/* Background Cyber-grid */}
      <div style={{
        position: 'absolute', top: 0, left: 0, width: '100%', height: '100%',
        backgroundImage: 'linear-gradient(rgba(255,255,255,0.02) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.02) 1px, transparent 1px)',
        backgroundSize: '40px 40px',
        zIndex: 0
      }}></div>

      <div className="premium-card" style={{ width: '100%', maxWidth: '440px', zIndex: 1, padding: '48px', backdropFilter: 'blur(30px)' }}>
        
        <div style={{ textAlign: 'center', marginBottom: '40px' }}>
          <div style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', width: '64px', height: '64px', borderRadius: '16px', background: 'linear-gradient(135deg, rgba(59, 130, 246, 0.2) 0%, rgba(37, 99, 235, 0.1) 100%)', border: '1px solid rgba(59, 130, 246, 0.3)', marginBottom: '24px' }}>
            <Activity size={32} color="#3B82F6" />
          </div>
          <h1 style={{ fontSize: '28px', color: 'white', marginBottom: '8px' }}>MiroFish Enterprise</h1>
          <p style={{ color: 'var(--text-muted)', fontSize: '15px' }}>Sign in via Corporate SSO</p>
        </div>

        <form onSubmit={handleLogin} style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          <div className="input-group">
            <label style={{ color: 'var(--text-muted)' }}>Corporate Email</label>
            <div style={{ position: 'relative' }}>
              <input 
                type="email" 
                className="premium-input" 
                placeholder="name@company.com" 
                value={email}
                onChange={e => setEmail(e.target.value)}
                required
                style={{ paddingLeft: '44px' }}
              />
              <Lock size={18} color="var(--text-muted)" style={{ position: 'absolute', left: '16px', top: '18px' }} />
            </div>
          </div>
          
          <button type="submit" className="premium-btn" style={{ marginTop: '12px' }} disabled={loading}>
            {loading ? (
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <div style={{ width: '16px', height: '16px', border: '2px solid rgba(255,255,255,0.3)', borderTopColor: 'white', borderRadius: '50%', animation: 'spin 1s linear infinite' }}></div>
                Authenticating...
              </div>
            ) : (
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                Continue with SSO <ArrowRight size={18} />
              </div>
            )}
          </button>
        </form>

        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px', marginTop: '32px', color: 'var(--text-muted)', fontSize: '13px' }}>
          <ShieldCheck size={16} color="#34d399" />
          Enterprise-Grade Security
        </div>
      </div>
    </div>
  );
}
