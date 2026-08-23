'use client';

export default function LiveFeed({ feed, onAgentSelect, onClearFeed }) {
  return (
    <section className="glass-panel live-feed-panel">
      <div className="panel-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <span className="glow-text-cyan" style={{ fontWeight: 600 }}>EVENT FEED</span>
          <div className="feed-tabs">
            <span className="active">AGENTS</span>
            <span>EVENTS</span>
          </div>
        </div>
        {onClearFeed && (
          <button className="clear-btn" onClick={onClearFeed}>CLEAR</button>
        )}
      </div>
      
      <div className="feed-content">
        {feed.length === 0 && <div className="text" style={{opacity:0.5}}>Waiting for events...</div>}
        {feed.map((item) => (
          <div key={item.id} className={`feed-row ${item.isSilent ? 'silent-row' : ''}`}>
            <span className="time">{item.time}:</span>
            <span className="text">
              {item.agent_id && onAgentSelect && (
                <span 
                  className="agent-link glow-text-cyan" 
                  onClick={() => onAgentSelect(item.agent_id)}
                >
                  [{item.agent_id}]
                </span>
              )}{' '}
              {item.actionLabel && <span className="action-badge">{item.actionLabel}</span>}{' '}
              {item.text}
            </span>
          </div>
        ))}
      </div>

      <style jsx>{`
        .live-feed-panel {
          display: flex;
          flex-direction: column;
          flex: 1;
          border-bottom: 2px solid var(--accent-magenta);
          overflow: hidden;
        }
        .feed-tabs {
          display: flex;
          gap: 10px;
        }
        .feed-tabs span {
          font-size: 0.7rem;
          padding: 4px 10px;
          border: 1px solid var(--border-color);
          border-radius: 4px;
          cursor: pointer;
        }
        .feed-tabs span.active {
          background: rgba(0, 240, 255, 0.1);
          border-color: var(--accent-cyan);
          color: var(--accent-cyan);
        }
        .clear-btn {
          background: transparent;
          border: 1px solid var(--text-secondary);
          color: var(--text-secondary);
          padding: 4px 10px;
          border-radius: 4px;
          font-size: 0.7rem;
          cursor: pointer;
          transition: 0.2s;
        }
        .clear-btn:hover {
          background: rgba(255,255,255,0.1);
          color: white;
          border-color: white;
        }
        .feed-content {
          padding: 16px;
          overflow-y: auto;
          flex: 1;
          display: flex;
          flex-direction: column;
          gap: 12px;
          font-family: "JetBrains Mono", monospace;
          font-size: 0.85rem;
        }
        .feed-row {
          display: flex;
          gap: 12px;
          animation: slideIn 0.3s ease forwards;
          border-left: 2px solid var(--accent-cyan);
          padding-left: 10px;
          color: #e2e8f0;
        }
        .time {
          color: var(--accent-cyan);
          opacity: 0.8;
          min-width: 75px;
        }
        .text {
          letter-spacing: 0.5px;
        }
        .agent-link {
          cursor: pointer;
          font-weight: bold;
          text-decoration: underline;
          text-decoration-color: transparent;
          transition: 0.3s;
        }
        .agent-link:hover {
          text-decoration-color: var(--accent-cyan);
          text-shadow: 0 0 5px var(--accent-cyan);
        }
        .silent-row {
          opacity: 0.6;
          border-left: 2px dashed var(--text-secondary);
        }
        .silent-row .text {
          font-style: italic;
          color: var(--text-secondary);
        }
        .action-badge {
          display: inline-block;
          font-size: 0.65rem;
          padding: 2px 6px;
          border-radius: 4px;
          background: rgba(255,255,255,0.1);
          color: var(--text-primary);
          margin-right: 6px;
          vertical-align: middle;
        }
      `}</style>
    </section>
  )
}
