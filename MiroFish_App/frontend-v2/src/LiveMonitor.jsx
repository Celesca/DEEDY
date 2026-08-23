import React, { useRef, useState, useMemo } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls, Html } from '@react-three/drei';
import ForceGraph2D from 'react-force-graph-2d';
import { AgGridReact } from 'ag-grid-react';
import 'ag-grid-community/styles/ag-grid.css';
import 'ag-grid-community/styles/ag-theme-alpine.css';
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';

// --- Dummy Data Generators ---
const generateGraphData = () => {
  const nodes = [];
  const links = [];
  const numNodes = 100;
  for (let i = 0; i < numNodes; i++) {
    const group = i < 50 ? 1 : 2;
    nodes.push({ id: `user_${i}`, group, val: Math.random() * 5 + 1 });
  }
  for (let i = 0; i < 200; i++) {
    const source = Math.floor(Math.random() * numNodes);
    let target;
    if (Math.random() > 0.1) {
      const offset = source < 50 ? 0 : 50;
      target = offset + Math.floor(Math.random() * 50);
    } else {
      target = Math.floor(Math.random() * numNodes);
    }
    links.push({ source: `user_${source}`, target: `user_${target}` });
  }
  return { nodes, links };
};

const generateLogs = () => {
  const logs = [];
  const stances = ['Supportive', 'Opposing', 'Neutral'];
  const actions = ['Post', 'Reply', 'Retweet'];
  for (let i = 0; i < 50; i++) {
    logs.push({
      timestamp: new Date(Date.now() - Math.random() * 10000000).toISOString().slice(0, 19).replace('T', ' '),
      agentId: `Agent_${Math.floor(Math.random() * 200)}`,
      actionType: actions[Math.floor(Math.random() * actions.length)],
      stance: stances[Math.floor(Math.random() * stances.length)],
      sentiment: (Math.random() * 2 - 1).toFixed(2),
      content: "This is a simulated trace log output...",
    });
  }
  return logs.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
};

const diffusionData = [
  { time: '08:00', supportive: 400, opposing: 240, neutral: 100 },
  { time: '09:00', supportive: 800, opposing: 350, neutral: 120 },
  { time: '10:00', supportive: 1500, opposing: 980, neutral: 200 },
];

// --- 3D Bean Component ---
function BeanAgent({ position, color, message, isHovered, setHovered, id }) {
  const meshRef = useRef();
  useFrame((state) => {
    meshRef.current.position.y = position[1] + Math.sin(state.clock.elapsedTime * 2 + id) * 0.1;
  });

  return (
    <group position={position}>
      <mesh 
        ref={meshRef}
        onPointerOver={() => setHovered(id)}
        onPointerOut={() => setHovered(null)}
      >
        <capsuleGeometry args={[0.4, 0.8, 16, 32]} />
        <meshStandardMaterial color={color} roughness={0.3} />
        
        <mesh position={[-0.15, 0.2, 0.35]}>
          <sphereGeometry args={[0.06, 16, 16]} />
          <meshBasicMaterial color="#1a1a1a" />
        </mesh>
        <mesh position={[0.15, 0.2, 0.35]}>
          <sphereGeometry args={[0.06, 16, 16]} />
          <meshBasicMaterial color="#1a1a1a" />
        </mesh>

        {isHovered === id && (
          <Html position={[0, 1.2, 0]} center>
            <div style={{
              background: 'white', padding: '6px 12px', borderRadius: '16px',
              boxShadow: '0 4px 12px rgba(0,0,0,0.1)', fontSize: '12px',
              fontWeight: 500, color: '#333', whiteSpace: 'nowrap'
            }}>
              {message}
            </div>
          </Html>
        )}
      </mesh>
    </group>
  );
}

export default function LiveMonitor() {
  const graphData = useMemo(() => generateGraphData(), []);
  const logData = useMemo(() => generateLogs(), []);
  const [hoveredBean, setHoveredBean] = useState(null);

  const agents = [
    { id: 1, pos: [-1.5, 0, 0], color: '#97bca3', msg: 'ค่าเทอมแพงไปไหม?' },
    { id: 2, pos: [0, 0, 1], color: '#a0c4e1', msg: 'ก็เศรษฐกิจมันแย่อ่ะ' },
    { id: 3, pos: [1.5, 0, -0.5], color: '#d99c9c', msg: 'ประท้วงเถอะ! 😡' },
  ];
  
  const columnDefs = [
    { field: 'timestamp', headerName: 'Timestamp', width: 160 },
    { field: 'agentId', headerName: 'Agent ID', width: 120 },
    { field: 'actionType', headerName: 'Action', width: 100 },
    { field: 'stance', headerName: 'Stance', width: 120 },
    { field: 'sentiment', headerName: 'Sentiment', width: 110 },
    { field: 'content', headerName: 'Trace Content', flex: 1 },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      
      {/* Top Row: Live Feed (3D) & Network Topology */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px', height: '350px' }}>
        
        {/* 3D Scene Panel */}
        <div className="soft-card" style={{ padding: 0, overflow: 'hidden', position: 'relative' }}>
          <div style={{ position: 'absolute', top: 16, left: 16, zIndex: 10, background: 'rgba(255,255,255,0.8)', padding: '8px', borderRadius: '8px' }}>
            <h3 style={{ margin: 0, fontSize: '16px' }}>Live Micro-Feed</h3>
            <p style={{ fontSize: '12px', margin: 0 }}>Hover to read live agent chat</p>
          </div>
          <Canvas camera={{ position: [0, 3, 6], fov: 45 }}>
            <ambientLight intensity={0.6} />
            <directionalLight position={[10, 10, 5]} intensity={1} castShadow />
            <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.8, 0]}>
              <planeGeometry args={[20, 20]} />
              <meshStandardMaterial color="#f5f5f5" />
            </mesh>
            {agents.map((agent) => (
              <BeanAgent key={agent.id} id={agent.id} position={agent.pos} color={agent.color} message={agent.msg} isHovered={hoveredBean} setHovered={setHoveredBean} />
            ))}
            <OrbitControls enableZoom={true} enablePan={false} maxPolarAngle={Math.PI / 2 - 0.1} />
          </Canvas>
        </div>

        {/* Network Topology */}
        <div className="soft-card" style={{ padding: 0, overflow: 'hidden', position: 'relative' }}>
          <div style={{ position: 'absolute', top: 16, left: 16, zIndex: 10, background: 'rgba(255,255,255,0.8)', padding: '8px', borderRadius: '8px' }}>
            <h3 style={{ margin: 0, fontSize: '16px' }}>Macro Topology</h3>
            <p style={{ fontSize: '12px', margin: 0 }}>Echo Chamber Clustering</p>
          </div>
          <ForceGraph2D
            graphData={graphData}
            width={700} height={350}
            nodeColor={node => node.group === 1 ? '#97bca3' : '#d99c9c'}
            nodeRelSize={4} linkColor={() => 'rgba(200,200,200,0.5)'}
          />
        </div>
      </div>

      {/* Middle Row: Stacked Area */}
      <div className="soft-card">
        <h3>Diffusion Scale (Stacked Area)</h3>
        <div style={{ width: '100%', height: '200px' }}>
          <ResponsiveContainer>
            <AreaChart data={diffusionData}>
              <XAxis dataKey="time" stroke="#aaa" fontSize={12} tickLine={false} axisLine={false} />
              <YAxis stroke="#aaa" fontSize={12} tickLine={false} axisLine={false} />
              <Tooltip contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: 'var(--shadow-soft)' }} />
              <Area type="monotone" dataKey="supportive" stackId="1" stroke="#97bca3" fill="#97bca3" fillOpacity={0.6} />
              <Area type="monotone" dataKey="opposing" stackId="1" stroke="#d99c9c" fill="#d99c9c" fillOpacity={0.6} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Bottom Row: Data Grid */}
      <div className="soft-card" style={{ height: '350px', padding: '16px', display: 'flex', flexDirection: 'column' }}>
        <h3 style={{ marginBottom: '12px' }}>Interaction Trace Log</h3>
        <div className="ag-theme-alpine" style={{ flex: 1, width: '100%', border: '1px solid #eee', borderRadius: '8px', overflow: 'hidden' }}>
          <AgGridReact rowData={logData} columnDefs={columnDefs} defaultColDef={{ resizable: true, filter: true }} pagination={true} paginationPageSize={10} />
        </div>
      </div>

    </div>
  );
}
