import React, { useEffect, useState, useRef } from 'react';
import './MatrixFeed.css';

const MatrixFeed = ({ campaignId }) => {
  const [messages, setMessages] = useState([]);
  const [stats, setStats] = useState({ total: 0, reached: 0, engaged: 0 });
  const [currentTick, setCurrentTick] = useState(0);
  const wsRef = useRef(null);
  const streamEndRef = useRef(null);

  useEffect(() => {
    if (!campaignId) return;

    // Connect WebSocket
    const ws = new WebSocket(`ws://localhost:8000/api/v1/stream/${campaignId}`);
    wsRef.current = ws;

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.event === "agent_action") {
          setMessages((prev) => [...prev, data.content]);
        } else if (data.event === "stats_update") {
          setStats({ total: data.total_agents, reached: data.reached, engaged: data.engaged });
        } else if (data.event === "tick_start") {
          setCurrentTick(data.tick);
          setMessages((prev) => [...prev, `\n--- ⏳ DAY ${data.tick} ---`]);
        }
      } catch (err) {
        console.error("Failed to parse websocket message", err);
      }
    };

    return () => {
      ws.close();
    };
  }, [campaignId]);

  useEffect(() => {
    // Auto-scroll to bottom
    streamEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  if (!campaignId) {
    return (
      <div style={{ display: 'flex', height: '100%', alignItems: 'center', justifyContent: 'center' }}>
        <p style={{ color: 'var(--text-secondary)' }}>Awaiting simulation launch...</p>
      </div>
    );
  }

  return (
    <div className="matrix-feed-container">
      <div className="feed-header" style={{ flexDirection: 'column', alignItems: 'flex-start' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', width: '100%', alignItems: 'center' }}>
          <h2 style={{ fontSize: '1.2rem', color: '#fff' }}>Live Matrix Feed {currentTick > 0 && `(Day ${currentTick})`}</h2>
          <div className="status-indicator">
            <div className="status-dot"></div>
            Simulation Running
          </div>
        </div>
        <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginTop: '8px' }}>
          Agents: {stats.total} | Reached: {stats.reached} | Engaged: {stats.engaged}
        </div>
      </div>
      
      <div className="feed-stream">
        {messages.map((msg, idx) => (
          <div key={idx} className="agent-message" style={msg.startsWith('---') ? {color: '#8b5cf6', fontWeight: 'bold', marginTop: '10px'} : {}}>
            {!msg.startsWith('---') && <span style={{ color: 'var(--accent-color)', marginRight: '8px' }}>&gt;</span>}
            {msg}
          </div>
        ))}
        <div ref={streamEndRef} />
      </div>
    </div>
  );
};

export default MatrixFeed;
