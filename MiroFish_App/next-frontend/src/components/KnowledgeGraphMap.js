'use client';
import { useMemo } from 'react';
import ForceGraph2D from 'react-force-graph-2d';

export default function KnowledgeGraphMap({ width = 400, height = 400 }) {
  // Generate a mock graph with agents and topics
  const graphData = useMemo(() => {
    const nodes = [
      { id: 'Agent1', group: 1, label: 'student_bkk' },
      { id: 'Agent2', group: 1, label: 'civil_servant_isan' },
      { id: 'Agent3', group: 1, label: 'shop_owner_south' },
      { id: 'Topic1', group: 2, label: 'เศรษฐกิจ' },
      { id: 'Topic2', group: 2, label: 'การเมือง' },
      { id: 'Topic3', group: 2, label: 'ระบบราชการ' },
      { id: 'Topic4', group: 2, label: 'สังคม' },
      { id: 'Cluster1', group: 3, label: 'หัวก้าวหน้า' },
      { id: 'Cluster2', group: 3, label: 'อนุรักษ์นิยม' },
      { id: 'Cluster3', group: 3, label: 'รักสงบ' },
    ];
    
    // add some random extra nodes
    for (let i = 4; i <= 30; i++) {
      nodes.push({ id: `Agent${i}`, group: 1, label: `Agent ${i}` });
    }

    const links = [
      { source: 'Agent1', target: 'Topic2', value: 2 },
      { source: 'Agent1', target: 'Cluster1', value: 3 },
      { source: 'Agent2', target: 'Topic3', value: 2 },
      { source: 'Agent2', target: 'Cluster3', value: 3 },
      { source: 'Agent3', target: 'Topic1', value: 2 },
      { source: 'Agent3', target: 'Cluster2', value: 3 },
      { source: 'Topic1', target: 'Topic4', value: 1 },
      { source: 'Topic2', target: 'Topic4', value: 1 },
      { source: 'Topic3', target: 'Topic4', value: 1 },
      { source: 'Cluster1', target: 'Topic2', value: 2 },
      { source: 'Cluster2', target: 'Topic1', value: 2 },
    ];

    // connect random agents to clusters and topics
    for (let i = 4; i <= 30; i++) {
      const isProgressive = Math.random() > 0.5;
      links.push({
        source: `Agent${i}`,
        target: isProgressive ? 'Cluster1' : (Math.random() > 0.5 ? 'Cluster2' : 'Cluster3'),
        value: 1
      });
      links.push({
        source: `Agent${i}`,
        target: `Topic${Math.floor(Math.random() * 4) + 1}`,
        value: 1
      });
    }

    return { nodes, links };
  }, []);

  return (
    <div style={{ borderRadius: '16px', overflow: 'hidden', border: '1px solid var(--border-color)', background: 'rgba(0,0,0,0.2)' }}>
      <ForceGraph2D
        width={width}
        height={height}
        graphData={graphData}
        nodeColor={node => {
          if (node.group === 1) return '#e0b1cb'; // magenta for agents
          if (node.group === 2) return '#00f0ff'; // cyan for topics
          return '#fff'; // white for clusters
        }}
        nodeRelSize={4}
        linkColor={() => 'rgba(255,255,255,0.1)'}
        linkWidth={link => link.value}
        backgroundColor="transparent"
        nodeCanvasObject={(node, ctx, globalScale) => {
          const label = node.label;
          const fontSize = 12/globalScale;
          ctx.font = `${fontSize}px Sans-Serif`;
          
          // draw node
          ctx.beginPath();
          ctx.arc(node.x, node.y, node.group === 2 ? 6 : 4, 0, 2 * Math.PI, false);
          ctx.fillStyle = node.group === 1 ? '#e0b1cb' : (node.group === 2 ? '#00f0ff' : '#fff');
          ctx.fill();
          
          if (node.group !== 1 || globalScale > 2) {
             ctx.textAlign = 'center';
             ctx.textBaseline = 'middle';
             ctx.fillStyle = 'rgba(255, 255, 255, 0.8)';
             ctx.fillText(label, node.x, node.y + (node.group === 2 ? 10 : 8));
          }
        }}
      />
    </div>
  );
}
