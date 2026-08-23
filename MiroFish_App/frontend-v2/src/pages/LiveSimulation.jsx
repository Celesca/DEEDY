import React, { useState, useEffect, useContext } from 'react';
import { AppContext } from '../App';
import { Activity, ShieldAlert, Cpu, TrendingDown, TrendingUp, Eye, Users, Search, MessageSquare, AlertTriangle, Radio, Send, X } from 'lucide-react';
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, BarChart, Bar, Legend, PieChart, Pie, Cell } from 'recharts';
import { useLocation } from 'react-router-dom';

const API_BASE_URL = 'http://127.0.0.1:5001/api/simulation';

// Component for Flipping Agent Card
const AgentCard = ({ agent, onInterview }) => {
  const [isFlipped, setIsFlipped] = useState(false);

  return (
    <div className="agent-card-container" style={{ perspective: '1000px', height: '220px' }}>
      <div 
        className={`agent-card-inner ${isFlipped ? 'flipped' : ''}`}
        style={{ 
          position: 'relative', width: '100%', height: '100%', 
          transition: 'transform 0.6s', transformStyle: 'preserve-3d', cursor: 'pointer'
        }}
        onClick={() => setIsFlipped(!isFlipped)}
      >
        {/* Front of Card (Public Expression) */}
        <div className="agent-card-front" style={{
          position: 'absolute', width: '100%', height: '100%', backfaceVisibility: 'hidden',
          background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: '12px', padding: '16px',
          display: 'flex', flexDirection: 'column',
          borderTop: `4px solid ${agent.publicAction === 'BOT_ATTACK' ? 'var(--primary-yellow)' : 'var(--primary-blue)'}`
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '12px' }}>
            <h3 style={{ margin: 0, fontSize: '15px', display: 'flex', alignItems: 'center', gap: '6px' }}>
              {agent.user}
              {agent.isLLM && <span style={{ background: 'rgba(34, 211, 238, 0.1)', color: '#22D3EE', padding: '2px 6px', borderRadius: '4px', fontSize: '10px' }}>AI</span>}
            </h3>
            <span style={{ fontSize: '11px', color: 'var(--text-muted)', background: 'rgba(0,0,0,0.05)', padding: '2px 6px', borderRadius: '4px' }}>
              {agent.publicAction}
            </span>
          </div>
          <p style={{ fontSize: '13px', color: 'var(--text)', flex: 1, overflow: 'hidden', display: '-webkit-box', WebkitLineClamp: 4, WebkitBoxOrient: 'vertical' }}>
            {agent.publicAction === 'SILENT_SHIFT' ? '*(Remains Silent)*' : agent.text}
          </p>
          <div style={{ textAlign: 'center', fontSize: '11px', color: 'var(--text-light)', marginTop: '8px' }}>
            Click to reveal private stance ↺
          </div>
        </div>

        {/* Back of Card (Private Thoughts) */}
        <div className="agent-card-back" style={{
          position: 'absolute', width: '100%', height: '100%', backfaceVisibility: 'hidden',
          background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: '12px', padding: '16px',
          transform: 'rotateY(180deg)', display: 'flex', flexDirection: 'column'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px', borderBottom: '1px solid #e2e8f0', paddingBottom: '8px' }}>
            <span style={{ fontSize: '12px', fontWeight: 'bold', color: 'var(--text)' }}><Eye size={14} style={{verticalAlign:'middle', marginRight:'4px'}}/> True Stance</span>
            <span style={{ 
              fontSize: '11px', fontWeight: 'bold', padding: '2px 8px', borderRadius: '12px',
              background: agent.privateStance === 'opposing' ? '#fee2e2' : agent.privateStance === 'supporting' ? '#d1fae5' : '#f1f5f9',
              color: agent.privateStance === 'opposing' ? '#ef4444' : agent.privateStance === 'supporting' ? '#10b981' : '#64748b'
            }}>
              {agent.privateStance.toUpperCase()}
            </span>
          </div>
          <p style={{ fontSize: '13px', color: 'var(--text-muted)', fontStyle: 'italic', flex: 1, overflowY: 'auto' }}>
            "{agent.privateText}"
          </p>
          
          <button 
            onClick={(e) => { e.stopPropagation(); onInterview(agent.agent_id); }}
            className="hover-transition"
            style={{
              width: '100%', padding: '8px', background: 'var(--primary-blue)', color: 'white', border: 'none', borderRadius: '6px',
              fontSize: '12px', fontWeight: 'bold', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px',
              marginTop: '8px'
            }}
          >
            <MessageSquare size={14} /> Interview via IPC
          </button>
        </div>
      </div>
    </div>
  );
};

export default function LiveSimulation() {
  const { isAdvanced } = useContext(AppContext);
  const location = useLocation();
  const [SIM_ID, setSimId] = useState(() => {
    return location.state?.sim_id || localStorage.getItem('current_sim_id') || 'thai_society';
  });

  useEffect(() => {
    if (SIM_ID) {
      localStorage.setItem('current_sim_id', SIM_ID);
    }
  }, [SIM_ID]);

  const [pulseData, setPulseData] = useState([]);
  const [actions, setActions] = useState([]);
  const [falsificationData, setFalsificationData] = useState([
    { name: 'Supporting', True: 0, Expressed: 0 },
    { name: 'Neutral', True: 0, Expressed: 0 },
    { name: 'Opposing', True: 0, Expressed: 0 }
  ]);
  const [visibilityData, setVisibilityData] = useState([]);
  
  const [isLive, setIsLive] = useState(false);
  const [error, setError] = useState(null);
  const [viewMode, setViewMode] = useState('cards'); // 'cards' or 'stream'
  const [initLogs, setInitLogs] = useState(["Connecting to simulation engine..."]);
  const [currentRound, setCurrentRound] = useState(0);
  const [totalRounds, setTotalRounds] = useState(144);

  // Interview Modal States
  const [interviewAgentId, setInterviewAgentId] = useState(null);
  const [interviewChat, setInterviewChat] = useState([]);
  const [interviewInput, setInterviewInput] = useState('');
  const [isInterviewing, setIsInterviewing] = useState(false);

  // Poll for data
  useEffect(() => {
    let interval;
    const fetchData = async () => {
      try {
        const res = await fetch(`${API_BASE_URL}/${SIM_ID}/poll`);
        if (!res.ok) {
          if (res.status === 404) throw new Error(`Simulation '${SIM_ID}' not found or hasn't started yet.`);
          throw new Error(`Backend Connection Error: HTTP ${res.status}`);
        }
        const data = await res.json();
        
        setIsLive(true);
        setError(null);
        setCurrentRound(data.current_round || 0);
        setTotalRounds(data.total_rounds || 144);
        
        if (data.pulse_history && data.pulse_history.length > 0) {
           const mapped = data.pulse_history.map(p => ({
             time: p.time,
             positive: p.positive,
             negative: p.negative,
             bots: p.bots,
             expressed: p.expressed || 0,
             silent: p.silent || 0
           }));
           setPulseData(mapped);
        }
        
        if (data.recent_actions && data.recent_actions.length > 0) {
           const mapped = data.recent_actions.map(a => ({
             id: a.timestamp + a.agent_id,
             agent_id: a.agent_id,
             user: a.agent_name || `Agent ${a.agent_id}`,
             publicAction: a.action_type,
             text: a.action_args?.content || a.action_args?.post_text || a.action_args?.private_text || '',
             privateStance: a.action_args?.private_stance || 'neutral',
             privateText: a.action_args?.private_text || a.action_args?.content || 'No private thought recorded.',
             isLLM: a.action_args?.is_llm || false
           }));
           setActions(mapped);
        }

        if (data.falsification_stats) {
            setFalsificationData([
                { name: 'Supporting', True: data.falsification_stats.supporting.true, Expressed: data.falsification_stats.supporting.expressed },
                { name: 'Neutral', True: data.falsification_stats.neutral.true, Expressed: data.falsification_stats.neutral.expressed },
                { name: 'Opposing', True: data.falsification_stats.opposing.true, Expressed: data.falsification_stats.opposing.expressed }
            ]);
        } else {
            // If no data yet, fetch startup logs
            try {
              const logRes = await fetch(`${API_BASE_URL}/${SIM_ID}/logs`);
              if (logRes.ok) {
                const logData = await logRes.json();
                if (logData.logs && logData.logs.length > 0) {
                  setInitLogs(logData.logs);
                }
              }
            } catch (e) {}
        }

        if (data.visibility_stats) {
            if (data.visibility_stats.exposed_expressed !== undefined) {
               setVisibilityData([
                   { name: 'Expressed', value: data.visibility_stats.exposed_expressed },
                   { name: 'Silent', value: data.visibility_stats.exposed_silent },
                   { name: 'Unaware', value: data.visibility_stats.unaware }
               ]);
            } else {
               setVisibilityData([
                   { name: 'Exposed', value: data.visibility_stats.exposed },
                   { name: 'Unaware', value: data.visibility_stats.unaware }
               ]);
            }
        }
        
      } catch (err) {
        setIsLive(false);
        setError(err.message);
      }
    };

    fetchData();
    interval = setInterval(fetchData, 3000);
    return () => clearInterval(interval);
  }, [SIM_ID]);

  const handleInterview = (agentId) => {
    setInterviewAgentId(agentId);
    setInterviewChat([
      { role: 'system', text: `You are now interviewing Agent ${agentId} via IPC Server.` }
    ]);
  };

  const handleSendInterview = async () => {
    if (!interviewInput.trim() || !interviewAgentId || isInterviewing) return;
    const userMsg = interviewInput;
    setInterviewInput('');
    setInterviewChat(prev => [...prev, { role: 'user', text: userMsg }]);
    setIsInterviewing(true);

    try {
      const res = await fetch(`${API_BASE_URL}/interview`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          simulation_id: SIM_ID,
          agent_id: interviewAgentId,
          prompt: userMsg,
          timeout: 60
        })
      });
      const data = await res.json();
      if (res.ok && data.success) {
        // Handle dual-platform or single response
        const reply = data.data.result.response || (data.data.result.platforms && data.data.result.platforms.twitter?.response) || "Agent did not respond.";
        setInterviewChat(prev => [...prev, { role: 'agent', text: reply }]);
      } else {
        setInterviewChat(prev => [...prev, { role: 'system', text: `Error: ${data.error || 'Failed to get response'}` }]);
      }
    } catch (err) {
      setInterviewChat(prev => [...prev, { role: 'system', text: `Error: ${err.message}` }]);
    } finally {
      setIsInterviewing(false);
    }
  };

  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      return (
        <div className="premium-card" style={{ padding: '16px', borderRadius: '12px', minWidth: '200px' }}>
          <p style={{ color: 'var(--text)', fontWeight: 'bold', marginBottom: '12px' }}>Round {label}</p>
          {payload.map((entry, index) => (
            <div key={index} style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px', color: entry.color, fontWeight: 600 }}>
              <span>{entry.name}</span>
              <span>{entry.value}</span>
            </div>
          ))}
        </div>
      );
    }
    return null;
  };

  if (error) {
    return (
      <div className="flex-col" style={{ alignItems: 'center', justifyContent: 'center', minHeight: '60vh', marginTop: '64px' }}>
        <ShieldAlert size={48} color="#ff4b4b" style={{ marginBottom: '16px' }} />
        <h2 style={{ color: '#ff4b4b', fontSize: '24px', margin: '0 0 8px 0' }}>Simulation Engine Error</h2>
        <p style={{ color: 'var(--text-muted)', maxWidth: '500px', textAlign: 'center', lineHeight: '1.6' }}>{error}</p>
        <button onClick={() => window.location.reload()} className="premium-btn" style={{ marginTop: '24px' }}>Retry Connection</button>
      </div>
    );
  }

  if (pulseData.length === 0) {
    return (
      <div className="flex-col" style={{ alignItems: 'center', justifyContent: 'center', minHeight: '80vh', padding: '24px' }}>
        <div style={{ textAlign: 'center', marginBottom: '32px' }}>
          <h2 className="hero-gradient-text" style={{ fontSize: '28px', margin: '0 0 12px 0' }}>Initializing Simulation Engine...</h2>
          <p style={{ color: 'var(--text-muted)', margin: 0, fontSize: '16px' }}>Deploying AI agents and establishing network topology.</p>
          <div style={{ marginTop: '16px', display: 'inline-flex', alignItems: 'center', gap: '8px', padding: '6px 12px', background: 'var(--card)', borderRadius: '20px', border: '1px solid var(--border)' }}>
            <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#FACC15', animation: 'pulse 1.5s infinite' }}></div>
            <span style={{ fontSize: '13px', color: 'var(--text-muted)', fontFamily: 'monospace' }}>ID: {SIM_ID}</span>
          </div>
        </div>
        
        {/* Enterprise Dashboard Loader */}
        <div style={{ width: '100%', maxWidth: '900px', display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '16px' }}>
          
          {/* Status Card 1: Connection */}
          <div className="premium-card" style={{ padding: '24px', background: 'var(--card)', border: '1px solid var(--border)', borderRadius: '8px', boxShadow: 'var(--shadow)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <Cpu size={24} color="var(--primary-blue)" />
              <div style={{ display: 'flex', gap: '4px' }}>
                <div style={{ width: '6px', height: '6px', borderRadius: '50%', background: 'var(--primary-blue)', animation: 'pulse 1s infinite' }}></div>
              </div>
            </div>
            <h3 style={{ fontSize: '14px', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '1px', marginBottom: '8px' }}>Simulation Node</h3>
            <p style={{ fontSize: '18px', color: 'var(--text)', fontWeight: 700, margin: 0 }}>Connecting...</p>
          </div>

          {/* Status Card 2: Agents */}
          <div className="premium-card" style={{ padding: '24px', background: 'var(--card)', border: '1px solid var(--border)', borderRadius: '8px', boxShadow: 'var(--shadow)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <Users size={24} color="var(--primary-yellow)" />
              <div style={{ width: '16px', height: '16px', border: '2px solid var(--primary-yellow)', borderTopColor: 'transparent', borderRadius: '50%', animation: 'spin 1s linear infinite' }}></div>
            </div>
            <h3 style={{ fontSize: '14px', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '1px', marginBottom: '8px' }}>Agent Deployment</h3>
            <p style={{ fontSize: '18px', color: 'var(--text)', fontWeight: 700, margin: 0 }}>Provisioning AI</p>
          </div>

          {/* Status Card 3: Network */}
          <div className="premium-card" style={{ padding: '24px', background: 'var(--card)', border: '1px solid var(--border)', borderRadius: '8px', boxShadow: 'var(--shadow)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <Activity size={24} color="var(--text-light)" />
              <div style={{ fontSize: '12px', color: 'var(--text-light)', fontWeight: 600 }}>STANDBY</div>
            </div>
            <h3 style={{ fontSize: '14px', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '1px', marginBottom: '8px' }}>Social Graph</h3>
            <p style={{ fontSize: '18px', color: 'var(--text-light)', fontWeight: 700, margin: 0 }}>Awaiting Start</p>
          </div>
          
        </div>

        {/* Console Logs Table (Enterprise Style) */}
        <div className="premium-card" style={{ width: '100%', maxWidth: '900px', padding: '0', background: 'var(--card)', border: '1px solid var(--border)', borderRadius: '8px', marginTop: '24px', overflow: 'hidden' }}>
          <div style={{ padding: '12px 16px', borderBottom: '1px solid var(--border)', background: '#F8FAFC', fontSize: '12px', fontWeight: 600, color: 'var(--text-muted)', display: 'flex', justifyContent: 'space-between' }}>
            <span>SYSTEM LOGS</span>
            <span style={{ fontFamily: 'var(--font-code)' }}>{SIM_ID}</span>
          </div>
          <div style={{ padding: '16px', height: '200px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {initLogs.map((log, i) => (
              <div key={i} style={{ display: 'flex', gap: '16px', fontSize: '13px', fontFamily: 'var(--font-code)', borderBottom: '1px solid rgba(0,0,0,0.02)', paddingBottom: '8px' }}>
                <span style={{ color: 'var(--text-light)', width: '80px', flexShrink: 0 }}>{new Date().toLocaleTimeString()}</span>
                <span style={{ color: log.includes('ERROR') ? 'var(--primary-red)' : log.includes('WARN') ? 'var(--primary-yellow)' : 'var(--text)', wordBreak: 'break-all' }}>
                  {log}
                </span>
              </div>
            ))}
            <div ref={(el) => el && el.scrollIntoView({ behavior: 'smooth' })} />
          </div>
        </div>

        <style>{`
          @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
          @keyframes pulse { 0% { opacity: 0.4; } 50% { opacity: 1; } 100% { opacity: 0.4; } }
          div::-webkit-scrollbar { width: 6px; }
          div::-webkit-scrollbar-track { background: transparent; }
          div::-webkit-scrollbar-thumb { background: var(--border); border-radius: 4px; }
        `}</style>
      </div>
    );
  }

  return (
    <div className="flex-col gap-32 mt-24">
      
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <h1 className="hero-gradient-text" style={{ display: 'flex', alignItems: 'center', gap: '12px', margin: 0, fontSize: '36px' }}>
            <Activity size={32} color="var(--primary-blue)" /> 
            Live Matrix Arena
          </h1>
          <p style={{ color: 'var(--text-muted)', marginTop: '8px', fontSize: '16px' }}>
            Real-time monitoring of societal pulse and agent interactions.
          </p>
        </div>
        
        <div className="premium-card" style={{ padding: '12px 24px', borderRadius: '30px', display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div className="pulse-badge hot" style={{ background: isLive ? 'rgba(52, 211, 153, 0.2)' : 'rgba(255, 75, 75, 0.2)', color: isLive ? '#34d399' : '#ff4b4b', border: `1px solid ${isLive ? 'rgba(52, 211, 153, 0.5)' : 'rgba(255, 75, 75, 0.5)'}` }}>
            {isLive ? <><div style={{width:'8px', height:'8px', borderRadius:'50%', background:'#34d399', animation: 'pulse 1.5s infinite'}}></div> ONLINE</> : 'OFFLINE'}
          </div>
          <span style={{ fontSize: '13px', color: 'var(--text-muted)', fontWeight: 600, fontFamily: 'monospace' }}>
            ID: {SIM_ID}
          </span>
        </div>
      </div>

      {/* Enterprise KPI Ribbon */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '16px', marginTop: '16px' }}>
        <div className="premium-card" style={{ padding: '16px', background: 'var(--card)', border: '1px solid var(--border)', borderRadius: '8px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
          <span style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase' }}>Active Agents</span>
          <div style={{ display: 'flex', alignItems: 'flex-end', gap: '8px' }}>
            <span style={{ fontSize: '28px', fontWeight: 800, lineHeight: 1, color: 'var(--text)' }}>16</span>
            <span style={{ fontSize: '13px', color: 'var(--green)', fontWeight: 600, paddingBottom: '4px' }}>+100% ONLINE</span>
          </div>
        </div>
        <div className="premium-card" style={{ padding: '16px', background: 'var(--card)', border: '1px solid var(--border)', borderRadius: '8px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
          <span style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase' }}>Simulation Round</span>
          <div style={{ display: 'flex', alignItems: 'flex-end', gap: '8px' }}>
            <span style={{ fontSize: '28px', fontWeight: 800, lineHeight: 1, color: 'var(--text)' }}>{currentRound || pulseData.length}</span>
            <span style={{ fontSize: '13px', color: 'var(--text-muted)', fontWeight: 600, paddingBottom: '4px' }}>/ {totalRounds}</span>
          </div>
        </div>
        <div className="premium-card" style={{ padding: '16px', background: 'var(--card)', border: '1px solid var(--border)', borderRadius: '8px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
          <span style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase' }}>Falsification Gap</span>
          <div style={{ display: 'flex', alignItems: 'flex-end', gap: '8px' }}>
            <span style={{ fontSize: '28px', fontWeight: 800, lineHeight: 1, color: 'var(--primary-red)' }}>
              {falsificationData[0]?.True !== undefined ? Math.abs(falsificationData[0].True - falsificationData[0].Expressed) : 0}
            </span>
            <span style={{ fontSize: '13px', color: 'var(--text-muted)', fontWeight: 600, paddingBottom: '4px' }}>Deviation</span>
          </div>
        </div>
        <div className="premium-card" style={{ padding: '16px', background: 'var(--card)', border: '1px solid var(--border)', borderRadius: '8px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
          <span style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase' }}>Bot Influence</span>
          <div style={{ display: 'flex', alignItems: 'flex-end', gap: '8px' }}>
            <span style={{ fontSize: '28px', fontWeight: 800, lineHeight: 1, color: 'var(--primary-yellow)' }}>
              {pulseData.length > 0 ? pulseData[pulseData.length - 1].bots : 0}
            </span>
            <span style={{ fontSize: '13px', color: 'var(--text-muted)', fontWeight: 600, paddingBottom: '4px' }}>Attacks / Round</span>
          </div>
        </div>
      </div>

      {/* Aggregate Views (Bento Grid) */}
      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '16px' }}>
        
        {/* Real-time Pulse Chart */}
        <div className="premium-card" style={{ padding: '16px', background: 'var(--card)', border: '1px solid var(--border)', borderRadius: '8px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '16px' }}>
            <h2 style={{ color: 'var(--text)', fontSize: '16px', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '1px' }}>Societal Pulse</h2>
            <div style={{ display: 'flex', gap: '16px', fontSize: '12px', fontWeight: 600 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--green)' }}><TrendingUp size={14}/> Organic Supporting</div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--primary-red)' }}><TrendingDown size={14}/> Organic Opposing</div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--primary-yellow)' }}><ShieldAlert size={14}/> Bot Attacks</div>
            </div>
          </div>
          
          <div style={{ height: '220px', width: '100%' }}>
            {pulseData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={pulseData} margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
                  <defs>
                    <linearGradient id="colorPos" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="var(--green)" stopOpacity={0.4}/>
                      <stop offset="95%" stopColor="var(--green)" stopOpacity={0}/>
                    </linearGradient>
                    <linearGradient id="colorNeg" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="var(--primary-red)" stopOpacity={0.4}/>
                      <stop offset="95%" stopColor="var(--primary-red)" stopOpacity={0}/>
                    </linearGradient>
                    <linearGradient id="colorBots" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="var(--primary-yellow)" stopOpacity={0.4}/>
                      <stop offset="95%" stopColor="var(--primary-yellow)" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
                  <XAxis dataKey="time" stroke="var(--text-light)" tick={{ fill: 'var(--text-muted)', fontSize: 11 }} />
                  <YAxis stroke="var(--text-light)" tick={{ fill: 'var(--text-muted)', fontSize: 11 }} />
                  <Tooltip content={<CustomTooltip />} />
                  <Area type="monotone" name="Supporting" dataKey="positive" stroke="var(--green)" strokeWidth={2} fillOpacity={1} fill="url(#colorPos)" />
                  <Area type="monotone" name="Opposing" dataKey="negative" stroke="var(--primary-red)" strokeWidth={2} fillOpacity={1} fill="url(#colorNeg)" />
                  <Area type="monotone" name="Bots" dataKey="bots" stroke="var(--primary-yellow)" strokeWidth={2} fillOpacity={1} fill="url(#colorBots)" />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div style={{ display: 'flex', height: '100%', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)' }}>
                Waiting for data...
              </div>
            )}
          </div>
        </div>

        {/* Visibility / Reach Chart */}
        <div className="premium-card" style={{ padding: '16px', background: 'var(--card)', border: '1px solid var(--border)', borderRadius: '8px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '16px' }}>
            <h2 style={{ color: 'var(--text)', fontSize: '16px', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '1px', display: 'flex', alignItems: 'center', gap: '8px' }}>
               <Radio size={16} color="var(--primary-blue)"/> Visibility Share
            </h2>
          </div>
          
          <div style={{ height: '220px', width: '100%' }}>
            {visibilityData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={visibilityData}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={80}
                    paddingAngle={2}
                    dataKey="value"
                    label={({name, percent}) => `${name} ${(percent * 100).toFixed(0)}%`}
                    labelLine={false}
                  >
                    {visibilityData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.name === 'Expressed' ? 'var(--primary-blue)' : entry.name === 'Silent' ? '#64748B' : '#E2E8F0'} />
                    ))}
                  </Pie>
                  <Tooltip cursor={{fill: 'rgba(0,0,0,0.02)'}} />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div style={{ display: 'flex', height: '100%', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)' }}>
                Waiting for data...
              </div>
            )}
          </div>
        </div>

        {/* Campaign Reach Over Time (Expressed vs Silent) */}
        <div className="premium-card" style={{ padding: '16px', background: 'var(--card)', border: '1px solid var(--border)', borderRadius: '8px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '16px' }}>
            <h2 style={{ color: 'var(--text)', fontSize: '16px', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '1px', display: 'flex', alignItems: 'center', gap: '8px' }}>
               <TrendingDown size={16} color="var(--green)"/> Reach Dynamics
            </h2>
            <div style={{ display: 'flex', gap: '16px', fontSize: '12px', fontWeight: 600 }}>
              <span style={{ display: 'flex', alignItems: 'center', gap: '4px', color: 'var(--primary-blue)' }}>Expressed</span>
              <span style={{ display: 'flex', alignItems: 'center', gap: '4px', color: 'var(--text-muted)' }}>Silent</span>
            </div>
          </div>
          
          <div style={{ height: '200px', width: '100%' }}>
            {pulseData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={pulseData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <defs>
                    <linearGradient id="colorExpr" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="var(--primary-blue)" stopOpacity={0.4}/>
                      <stop offset="95%" stopColor="var(--primary-blue)" stopOpacity={0}/>
                    </linearGradient>
                    <linearGradient id="colorSilent" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#64748B" stopOpacity={0.2}/>
                      <stop offset="95%" stopColor="#64748B" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
                  <XAxis dataKey="time" stroke="var(--text-light)" tick={{ fill: 'var(--text-muted)', fontSize: 11 }} />
                  <YAxis stroke="var(--text-light)" tick={{ fill: 'var(--text-muted)', fontSize: 11 }} />
                  <Tooltip content={<CustomTooltip />} />
                  <Area type="monotone" name="Expressed" dataKey="expressed" stroke="var(--primary-blue)" strokeWidth={2} fillOpacity={1} fill="url(#colorExpr)" />
                  <Area type="monotone" name="Silent" dataKey="silent" stroke="#64748B" strokeWidth={2} fillOpacity={1} fill="url(#colorSilent)" />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div style={{ display: 'flex', height: '100%', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)' }}>
                Waiting for data...
              </div>
            )}
          </div>
        </div>

        {/* Preference Falsification Gap Chart */}
        <div className="premium-card" style={{ padding: '16px', background: 'var(--card)', border: '1px solid var(--border)', borderRadius: '8px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '16px' }}>
            <h2 style={{ color: 'var(--text)', fontSize: '16px', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '1px', display: 'flex', alignItems: 'center', gap: '8px' }}>
               <AlertTriangle size={16} color="var(--primary-red)"/> Falsification
            </h2>
          </div>
          
          <div style={{ height: '200px', width: '100%' }}>
            {actions.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={falsificationData} margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
                  <XAxis dataKey="name" stroke="var(--text-light)" tick={{ fill: 'var(--text-muted)', fontSize: 11 }} />
                  <YAxis stroke="var(--text-light)" tick={{ fill: 'var(--text-muted)', fontSize: 11 }} />
                  <Tooltip cursor={{fill: 'rgba(0,0,0,0.02)'}} />
                  <Legend wrapperStyle={{fontSize: '12px'}} verticalAlign="bottom" height={24}/>
                  <Bar dataKey="True" name="True Private Stance" fill="var(--text-muted)" radius={[2,2,0,0]} />
                  <Bar dataKey="Expressed" name="Publicly Expressed" fill="var(--primary-blue)" radius={[2,2,0,0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div style={{ display: 'flex', height: '100%', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)' }}>
                Waiting for data...
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Drill-down View (Bottom Section) */}
      <div className="premium-card" style={{ padding: '0', display: 'flex', flexDirection: 'column' }}>
        <div style={{ padding: '16px 24px', borderBottom: '1px solid rgba(0,0,0,0.05)', background: 'rgba(0,0,0,0.02)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h2 style={{ color: 'var(--text)', display: 'flex', alignItems: 'center', gap: '8px', margin: 0, fontSize: '18px' }}>
            <Users size={20} color="#8b5cf6" /> Agent Population
          </h2>
          
          <div style={{ display: 'flex', background: 'rgba(0,0,0,0.05)', borderRadius: '8px', padding: '4px' }}>
            <button 
              onClick={() => setViewMode('cards')}
              style={{ padding: '6px 12px', border: 'none', borderRadius: '4px', background: viewMode === 'cards' ? 'var(--card)' : 'transparent', color: viewMode === 'cards' ? 'var(--text)' : 'var(--text-muted)', fontWeight: 600, cursor: 'pointer', boxShadow: viewMode === 'cards' ? '0 1px 3px rgba(0,0,0,0.1)' : 'none' }}
            >
              Cards Grid
            </button>
            <button 
              onClick={() => setViewMode('stream')}
              style={{ padding: '6px 12px', border: 'none', borderRadius: '4px', background: viewMode === 'stream' ? 'var(--card)' : 'transparent', color: viewMode === 'stream' ? 'var(--text)' : 'var(--text-muted)', fontWeight: 600, cursor: 'pointer', boxShadow: viewMode === 'stream' ? '0 1px 3px rgba(0,0,0,0.1)' : 'none' }}
            >
              Terminal Stream
            </button>
          </div>
        </div>
        
        <div style={{ padding: '24px', minHeight: '400px' }}>
          {actions.length === 0 && (
            <div style={{ color: 'var(--text-muted)', textAlign: 'center', marginTop: '40px' }}>No actions recorded yet.</div>
          )}

          {viewMode === 'cards' ? (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '20px' }}>
              {actions.slice(0, 16).map((act, i) => (
                <AgentCard key={i} agent={act} onInterview={handleInterview} />
              ))}
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              {actions.slice(0, 20).map((act, i) => (
                <div key={i} className="stream-item" style={{
                  background: 'rgba(0,0,0,0.02)',
                  border: '1px solid rgba(0,0,0,0.05)',
                  borderLeft: `3px solid ${act.publicAction === 'BOT_ATTACK' ? 'var(--primary-yellow)' : act.privateStance === 'opposing' ? 'var(--primary-red)' : act.privateStance === 'supporting' ? 'var(--green)' : 'var(--primary-blue)'}`,
                  borderRadius: '12px', padding: '16px', position: 'relative'
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                    <div style={{ fontSize: '12px', fontWeight: 700, color: 'var(--text)', display: 'flex', alignItems: 'center', gap: '8px' }}>
                      {act.user} {act.isLLM && <span style={{ background: 'rgba(34, 211, 238, 0.2)', color: '#22D3EE', padding: '2px 6px', borderRadius: '4px', fontSize: '10px' }}>AI KOL</span>}
                    </div>
                    <div style={{ fontSize: '10px', textTransform: 'uppercase', color: 'var(--text-muted)' }}>
                      {act.publicAction.replace('_', ' ')}
                    </div>
                  </div>
                  
                  {act.text && (
                    <div style={{ fontSize: '14px', color: 'var(--text-muted)', lineHeight: 1.5 }}>
                      {act.text}
                    </div>
                  )}

                  {isAdvanced && (
                    <div style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', background: 'rgba(0,0,0,0.05)', padding: '4px 8px', borderRadius: '4px', marginTop: '12px', fontSize: '11px', color: 'var(--text-light)' }}>
                      <Eye size={12} /> True Stance: <span style={{ color: act.privateStance === 'opposing' ? '#ff4b4b' : act.privateStance === 'supporting' ? '#34d399' : 'var(--text-muted)', fontWeight: 600 }}>{act.privateStance.toUpperCase()}</span>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      <style>{`
        .stream-item {
          animation: slideInRight 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }
        .flipped {
          transform: rotateY(180deg);
        }
        @keyframes slideInRight {
          from { opacity: 0; transform: translateX(20px); }
          to { opacity: 1; transform: translateX(0); }
        }
        @keyframes pulse {
          0% { transform: scale(1); opacity: 1; }
          50% { transform: scale(1.1); opacity: 0.7; }
          100% { transform: scale(1); opacity: 1; }
        }
      `}</style>

      {/* Interview Modal Overlay */}
      {interviewAgentId !== null && (
        <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.5)', zIndex: 9999, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <div className="premium-card slide-in" style={{ width: '450px', height: '600px', display: 'flex', flexDirection: 'column', padding: 0, overflow: 'hidden' }}>
            {/* Header */}
            <div style={{ padding: '16px', background: 'var(--primary-blue)', color: 'white', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h3 style={{ margin: 0, fontSize: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <MessageSquare size={18} /> Interviewing Agent {interviewAgentId}
              </h3>
              <button 
                onClick={() => setInterviewAgentId(null)}
                style={{ background: 'transparent', border: 'none', color: 'white', cursor: 'pointer' }}
              >
                <X size={20} />
              </button>
            </div>
            
            {/* Chat History */}
            <div style={{ flex: 1, padding: '16px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '12px', background: 'var(--bg)' }}>
              {interviewChat.map((msg, i) => (
                <div key={i} style={{ 
                  alignSelf: msg.role === 'user' ? 'flex-end' : msg.role === 'system' ? 'center' : 'flex-start',
                  background: msg.role === 'user' ? 'var(--primary-blue)' : msg.role === 'system' ? 'transparent' : 'var(--card)',
                  color: msg.role === 'user' ? 'white' : msg.role === 'system' ? 'var(--text-muted)' : 'var(--text)',
                  padding: msg.role === 'system' ? '4px 12px' : '10px 14px',
                  borderRadius: '16px',
                  borderBottomRightRadius: msg.role === 'user' ? '4px' : '16px',
                  borderBottomLeftRadius: msg.role === 'agent' ? '4px' : '16px',
                  maxWidth: '85%',
                  fontSize: msg.role === 'system' ? '12px' : '14px',
                  border: msg.role === 'agent' ? '1px solid var(--border)' : 'none',
                  boxShadow: msg.role !== 'system' ? '0 2px 4px rgba(0,0,0,0.05)' : 'none',
                  fontStyle: msg.role === 'system' ? 'italic' : 'normal'
                }}>
                  {msg.text}
                </div>
              ))}
              {isInterviewing && (
                <div style={{ alignSelf: 'flex-start', background: 'var(--card)', padding: '10px 16px', borderRadius: '16px', borderBottomLeftRadius: '4px', border: '1px solid var(--border)' }}>
                  <span className="typing-indicator" style={{ display: 'inline-flex', gap: '4px' }}>
                    <span style={{ width: '6px', height: '6px', background: 'var(--text-muted)', borderRadius: '50%', animation: 'pulse 1.5s infinite' }}></span>
                    <span style={{ width: '6px', height: '6px', background: 'var(--text-muted)', borderRadius: '50%', animation: 'pulse 1.5s infinite 0.2s' }}></span>
                    <span style={{ width: '6px', height: '6px', background: 'var(--text-muted)', borderRadius: '50%', animation: 'pulse 1.5s infinite 0.4s' }}></span>
                  </span>
                </div>
              )}
            </div>
            
            {/* Input Area */}
            <div style={{ padding: '16px', borderTop: '1px solid var(--border)', background: 'var(--card)', display: 'flex', gap: '12px' }}>
              <input 
                type="text" 
                value={interviewInput}
                onChange={(e) => setInterviewInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSendInterview()}
                placeholder="Ask agent a question..."
                disabled={isInterviewing}
                style={{ flex: 1, padding: '10px 16px', borderRadius: '24px', border: '1px solid var(--border)', outline: 'none', background: 'var(--bg)', color: 'var(--text)' }}
              />
              <button 
                onClick={handleSendInterview}
                disabled={isInterviewing || !interviewInput.trim()}
                style={{ background: 'var(--primary-blue)', color: 'white', border: 'none', borderRadius: '50%', width: '40px', height: '40px', display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer', opacity: isInterviewing || !interviewInput.trim() ? 0.5 : 1 }}
              >
                <Send size={18} style={{ marginLeft: '2px' }} />
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
