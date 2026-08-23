'use client';
import { useState, useRef, useEffect } from 'react';

export default function InterviewPanel({ agentId, onClose }) {
  const [messages, setMessages] = useState([
    { role: 'system', text: `Initiated Interview Protocol with Agent #${agentId}` }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const sendMessage = async (e) => {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const userText = input.trim();
    setInput('');
    setMessages(prev => [...prev, { role: 'user', text: userText }]);
    setLoading(true);

    try {
      const res = await fetch(`http://localhost:8000/agent/${agentId}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: userText })
      });
      
      if (res.ok) {
        const data = await res.json();
        setMessages(prev => [...prev, { role: 'agent', text: data.response }]);
      } else {
        setMessages(prev => [...prev, { role: 'system', text: 'Error connecting to agent link.' }]);
      }
    } catch (err) {
      setMessages(prev => [...prev, { role: 'system', text: 'Connection failed.' }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-overlay">
      <section className="glass-panel interview-panel">
        <div className="panel-header">
          <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>INTERVIEW MODE: {agentId}</span>
          <button className="close-btn" onClick={onClose}>✕</button>
        </div>
        
        <div className="chat-window" ref={scrollRef}>
          {messages.map((msg, i) => (
            <div key={i} className={`chat-bubble ${msg.role}`}>
              {msg.role === 'system' && <span className="sys-icon">ℹ️ </span>}
              {msg.text}
            </div>
          ))}
          {loading && <div className="chat-bubble agent loading">... analyzing response ...</div>}
        </div>

        <form className="chat-input-area" onSubmit={sendMessage}>
          <input 
            type="text" 
            value={input} 
            onChange={(e) => setInput(e.target.value)} 
            placeholder="Ask something..."
            disabled={loading}
          />
          <button type="submit" disabled={!input.trim() || loading}>SEND</button>
        </form>
      </section>

      <style jsx>{`
        .modal-overlay {
          position: fixed;
          top: 0; left: 0; right: 0; bottom: 0;
          background: rgba(0,0,0,0.6);
          backdrop-filter: blur(8px);
          display: flex;
          align-items: center;
          justify-content: center;
          z-index: 1000;
        }
        .interview-panel {
          display: flex;
          flex-direction: column;
          width: 500px;
          height: 600px;
          max-height: 90vh;
        }
        .panel-header {
          padding: 16px 20px;
          border-bottom: 1px solid var(--border-color);
          display: flex;
          justify-content: space-between;
          align-items: center;
          font-size: 0.9rem;
        }
        .close-btn {
          background: transparent;
          border: none;
          cursor: pointer;
          font-size: 1.2rem;
          color: var(--text-secondary);
          transition: 0.2s;
        }
        .close-btn:hover {
          color: var(--text-primary);
        }
        .chat-window {
          flex: 1;
          padding: 20px;
          overflow-y: auto;
          display: flex;
          flex-direction: column;
          gap: 16px;
          font-size: 0.9rem;
        }
        .chat-bubble {
          max-width: 85%;
          padding: 12px 16px;
          border-radius: 12px;
          line-height: 1.5;
          animation: slideIn 0.3s ease;
        }
        .chat-bubble.system {
          align-self: center;
          background: rgba(255,255,255,0.05);
          color: var(--text-secondary);
          font-size: 0.8rem;
          border: 1px solid var(--border-color);
          border-radius: 16px;
        }
        .chat-bubble.user {
          align-self: flex-end;
          background: rgba(255, 255, 255, 0.1);
          color: var(--text-primary);
          border-bottom-right-radius: 2px;
        }
        .chat-bubble.agent {
          align-self: flex-start;
          background: rgba(160, 196, 255, 0.1);
          color: var(--text-primary);
          border: 1px solid rgba(160, 196, 255, 0.2);
          border-bottom-left-radius: 2px;
        }
        .chat-bubble.agent.loading {
          opacity: 0.6;
        }
        
        .chat-input-area {
          display: flex;
          padding: 16px 20px;
          border-top: 1px solid var(--border-color);
          gap: 12px;
        }
        .chat-input-area input {
          flex: 1;
          background: rgba(0,0,0,0.2);
          border: 1px solid var(--border-color);
          color: var(--text-primary);
          padding: 12px 16px;
          border-radius: 8px;
          font-family: inherit;
          transition: 0.3s;
        }
        .chat-input-area input:focus {
          outline: none;
          border-color: rgba(255,255,255,0.3);
          background: rgba(0,0,0,0.4);
        }
        .chat-input-area button {
          background: var(--text-primary);
          color: var(--bg-color);
          border: none;
          padding: 0 24px;
          border-radius: 8px;
          font-weight: 600;
          cursor: pointer;
          transition: 0.2s;
        }
        .chat-input-area button:disabled {
          background: rgba(255,255,255,0.1);
          color: var(--text-secondary);
          cursor: not-allowed;
        }
      `}</style>
    </div>
  );
}
