import React, { useContext, useState, useRef, useMemo } from 'react';
import { AppContext } from '../App';
import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls, Html } from '@react-three/drei';
import ForceGraph2D from 'react-force-graph-2d';
import { AreaChart, Area, XAxis, Tooltip, ResponsiveContainer } from 'recharts';

// --- Data Generators ---
const generateGraphData = () => {
  const nodes = []; const links = []; const numNodes = 100;
  for (let i = 0; i < numNodes; i++) { nodes.push({ id: `u${i}`, group: i < 50 ? 1 : 2, val: 2 }); }
  for (let i = 0; i < 200; i++) { links.push({ source: `u${Math.floor(Math.random()*100)}`, target: `u${Math.floor(Math.random()*100)}` }); }
  return { nodes, links };
};
const diffusionData = [ { time: '1h', supp: 100, opp: 40 }, { time: '2h', supp: 250, opp: 180 }, { time: '3h', supp: 500, opp: 480 } ];
const fakeTweets = [
  { id: 1, user: '@student123', text: 'ค่าเทอมแพงไปไหม? ยุคนี้เศรษฐกิจก็แย่', stance: 'opp' },
  { id: 2, user: '@admin_tu', text: 'มหาลัยจำเป็นต้องนำเงินไปพัฒนาระบบ AI ให้พวกคุณนะ', stance: 'supp' },
  { id: 3, user: '@angry_bird', text: 'ไม่เห็นด้วย! ประท้วงเถอะ', stance: 'opp' },
];

// --- 3D Bean ---
function BeanAgent({ position, color, message, isHovered, setHovered, id }) {
  const meshRef = useRef();
  useFrame((state) => { meshRef.current.position.y = position[1] + Math.sin(state.clock.elapsedTime * 2 + id) * 0.1; });
  return (
    <group position={position}>
      <mesh ref={meshRef} onPointerOver={() => setHovered(id)} onPointerOut={() => setHovered(null)}>
        <capsuleGeometry args={[0.4, 0.8, 16, 32]} />
        <meshStandardMaterial color={color} roughness={0.3} />
        <mesh position={[-0.15, 0.2, 0.35]}><sphereGeometry args={[0.06, 16, 16]} /><meshBasicMaterial color="#1a1a1a" /></mesh>
        <mesh position={[0.15, 0.2, 0.35]}><sphereGeometry args={[0.06, 16, 16]} /><meshBasicMaterial color="#1a1a1a" /></mesh>
        {isHovered === id && (
          <Html position={[0, 1.2, 0]} center>
            <div style={{ background: 'white', padding: '6px 12px', borderRadius: '16px', boxShadow: 'var(--shadow)', fontSize: '12px', fontWeight: 500, color: '#333', whiteSpace: 'nowrap' }}>
              {message}
            </div>
          </Html>
        )}
      </mesh>
    </group>
  );
}

export default function LiveSimulation() {
  const { isAdvanced } = useContext(AppContext);
  const [hoveredBean, setHoveredBean] = useState(null);
  const graphData = useMemo(() => generateGraphData(), []);

  return (
    <div className="flex-col gap-24 mt-24">
      
      {/* Top Section: Always show Beans and Pulse, but adjust layout based on Advanced */}
      <div className={isAdvanced ? "grid-2" : "grid-2"}>
        
        {/* 3D Live Feed */}
        <div className="card" style={{ padding: 0, overflow: 'hidden', position: 'relative', height: '400px' }}>
          <div style={{ position: 'absolute', top: 24, left: 24, zIndex: 10 }}>
            <h3>Live Social Topology</h3>
            <p className="subtitle" style={{ fontSize: '13px' }}>Hover over agents to see live chat</p>
          </div>
          <Canvas camera={{ position: [0, 3, 6], fov: 45 }}>
            <ambientLight intensity={0.6} />
            <directionalLight position={[10, 10, 5]} intensity={1} />
            <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.8, 0]}><planeGeometry args={[20, 20]} /><meshStandardMaterial color="#f5f5f5" /></mesh>
            <BeanAgent id={1} pos={[-1.5, 0, 0]} color="var(--red)" msg="แพงไปป่าว?" isHovered={hoveredBean} setHovered={setHoveredBean} />
            <BeanAgent id={2} pos={[1.5, 0, -1]} color="var(--green)" msg="ก็สมเหตุสมผลนะ" isHovered={hoveredBean} setHovered={setHoveredBean} />
            <BeanAgent id={3} pos={[0, 0, 1]} color="var(--red)" msg="ไม่ยอมเว้ยยย" isHovered={hoveredBean} setHovered={setHoveredBean} />
            <OrbitControls enableZoom={true} enablePan={false} maxPolarAngle={Math.PI / 2 - 0.1} />
          </Canvas>
        </div>

        {/* Dynamic Right Panel based on Mode */}
        {isAdvanced ? (
          /* Advanced: Network Graph */
          <div className="card" style={{ padding: 0, overflow: 'hidden', position: 'relative', height: '400px' }}>
            <div style={{ position: 'absolute', top: 24, left: 24, zIndex: 10, background: 'rgba(255,255,255,0.8)', padding: '8px', borderRadius: '8px' }}>
              <h3 style={{ margin: 0 }}>Macro Network Graph</h3>
            </div>
            <ForceGraph2D
              graphData={graphData}
              width={600} height={400}
              nodeColor={n => n.group === 1 ? 'var(--red)' : 'var(--green)'}
              nodeRelSize={4} linkColor={() => 'rgba(200,200,200,0.5)'}
            />
          </div>
        ) : (
          /* Simple: Live Feed & Pulse Meter */
          <div className="flex-col gap-24">
            <div className="card" style={{ flex: 1 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <h3>อุณหภูมิสังคม (Pulse Meter)</h3>
                <span className="pulse-badge hot">🔥 ร้อนแรงมาก</span>
              </div>
              <div className="mt-24 flex-col gap-16">
                {fakeTweets.map(t => (
                  <div key={t.id} style={{ padding: '12px', background: 'var(--bg)', borderRadius: 'var(--radius-sm)', borderLeft: `4px solid ${t.stance === 'opp' ? 'var(--red)' : 'var(--green)'}` }}>
                    <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-muted)' }}>{t.user}</div>
                    <div style={{ fontSize: '14px', marginTop: '4px' }}>{t.text}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Advanced Only: Extra Analytics at bottom */}
      {isAdvanced && (
        <div className="card mt-24">
          <h3>Diffusion Scale (Stacked Area)</h3>
          <div style={{ width: '100%', height: '200px', marginTop: '16px' }}>
            <ResponsiveContainer>
              <AreaChart data={diffusionData}>
                <XAxis dataKey="time" stroke="#aaa" fontSize={12} tickLine={false} axisLine={false} />
                <Tooltip />
                <Area type="monotone" dataKey="opp" stackId="1" stroke="var(--red)" fill="var(--red)" fillOpacity={0.6} />
                <Area type="monotone" dataKey="supp" stackId="1" stroke="var(--green)" fill="var(--green)" fillOpacity={0.6} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

    </div>
  );
}
