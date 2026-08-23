import React, { useEffect, useState, useRef, useCallback } from 'react';
import ForceGraph2D from 'react-force-graph-2d';
import './AnalystReport.css';

const NetworkGraph = ({ campaignId }) => {
  const [graphData, setGraphData] = useState({ nodes: [], links: [] });
  const [highlightNodes, setHighlightNodes] = useState(new Set());
  const wsRef = useRef(null);

  useEffect(() => {
    if (!campaignId) {
      setGraphData({ nodes: [], links: [] });
      setHighlightNodes(new Set());
      return;
    }

    const ws = new WebSocket(`ws://localhost:8000/api/v1/stream/${campaignId}`);
    wsRef.current = ws;

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.event === "topology_init") {
          setGraphData(data.data);
        } else if (data.event === "graph_highlight") {
          const agentId = data.agent_id;
          setHighlightNodes((prev) => {
            const next = new Set(prev);
            next.add(agentId);
            return next;
          });
          // Remove highlight after 2 seconds
          setTimeout(() => {
            setHighlightNodes((prev) => {
              const next = new Set(prev);
              next.delete(agentId);
              return next;
            });
          }, 2000);
        }
      } catch (err) {
        // ignore other events
      }
    };

    return () => {
      ws.close();
    };
  }, [campaignId]);

  const paintNode = useCallback((node, ctx, globalScale) => {
    const isHighlighted = highlightNodes.has(node.id);
    const size = isHighlighted ? 6 : (node.group === 1 ? 4 : 2); // KOLs are bigger
    const color = isHighlighted ? '#10b981' : (node.group === 1 ? '#3b82f6' : '#6366f1'); // Green when active, blue for KOL, purple for Math
    
    ctx.beginPath();
    ctx.arc(node.x, node.y, size, 0, 2 * Math.PI, false);
    ctx.fillStyle = color;
    ctx.fill();
    
    if (isHighlighted) {
      ctx.strokeStyle = '#fff';
      ctx.lineWidth = 1;
      ctx.stroke();
    }
  }, [highlightNodes]);

  if (!campaignId) return null;

  return (
    <div className="report-panel" style={{ height: '300px', display: 'flex', flexDirection: 'column' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
        <h3 style={{ color: '#fff', margin: 0 }}>Viral Network Topology</h3>
        <span style={{ fontSize: '0.8rem', color: '#10b981' }}>Live Force Graph</span>
      </div>
      <div style={{ flex: 1, position: 'relative', overflow: 'hidden', borderRadius: '8px', background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.05)' }}>
        {graphData.nodes.length > 0 ? (
          <ForceGraph2D
            graphData={graphData}
            nodeCanvasObject={paintNode}
            linkColor={() => 'rgba(255,255,255,0.1)'}
            width={600}
            height={250}
            d3AlphaDecay={0.05}
            d3VelocityDecay={0.2}
            cooldownTicks={100}
          />
        ) : (
          <div style={{ color: 'var(--accent-color)', display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%', fontWeight: 'bold', textShadow: '0 0 10px var(--accent-color)' }}>
            Generating Graph Topology...
          </div>
        )}
      </div>
    </div>
  );
};

export default NetworkGraph;
