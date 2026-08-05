import React, { useContext, useMemo } from 'react';
import { AppContext } from '../App';
import { AgGridReact } from 'ag-grid-react';
import { Download } from 'lucide-react';
import 'ag-grid-community/styles/ag-grid.css';
import 'ag-grid-community/styles/ag-theme-alpine.css';

const generateLogs = () => {
  const logs = [];
  const stances = ['Supportive', 'Opposing', 'Neutral'];
  for (let i = 0; i < 50; i++) {
    logs.push({
      timestamp: new Date(Date.now() - Math.random() * 100000).toISOString().slice(0, 19).replace('T', ' '),
      agentId: `Agent_${Math.floor(Math.random() * 200)}`,
      stance: stances[Math.floor(Math.random() * stances.length)],
      sentiment: (Math.random() * 2 - 1).toFixed(2),
      content: "นี่คือข้อความจำลองจากเหตุการณ์...",
    });
  }
  return logs.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
};

export default function InsightReport() {
  const { isAdvanced } = useContext(AppContext);
  const logData = useMemo(() => generateLogs(), []);

  const columnDefs = [
    { field: 'timestamp', headerName: 'Timestamp', width: 160 },
    { field: 'agentId', headerName: 'Agent ID', width: 120 },
    { field: 'stance', headerName: 'Stance', width: 120 },
    { field: 'sentiment', headerName: 'Sentiment', width: 110 },
    { field: 'content', headerName: 'Trace Content', flex: 1 },
  ];

  return (
    <div className="flex-col gap-24 mt-24">
      
      {/* Top Header / Score */}
      <div className="card" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div>
          <h2>สรุปผลการจำลองเหตุการณ์ (Insight Report)</h2>
          <p className="subtitle">รายงานฉบับสมบูรณ์วิเคราะห์พฤติกรรมชาวเน็ตจำลอง</p>
        </div>
        <div className="risk-score">
          <div style={{ textAlign: 'right' }}>
            <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-muted)' }}>PR CRISIS RISK</div>
            <div style={{ color: '#c0392b', fontWeight: 600 }}>High Risk</div>
          </div>
          <div className="risk-number high">8<span style={{fontSize: '24px', color: 'var(--border)'}}>/10</span></div>
        </div>
      </div>

      <div className="grid-2">
        
        {/* Storytelling Section (Always visible) */}
        <div className="card">
          <h3 style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
            <span style={{ fontSize: '20px' }}>📖</span> สรุปเรื่องราว (Executive Summary)
          </h3>
          <p style={{ lineHeight: 1.6, color: 'var(--text-muted)' }}>
            หลังจากมีการเผยแพร่เหตุการณ์ "ขึ้นค่าเทอม" กระแสสังคมบนแพลตฟอร์มทวิตเตอร์ 
            <strong>เกิดการต่อต้านอย่างรุนแรง (70%)</strong> ภายในเวลาเพียง 2 ชั่วโมงแรก 
            โดยกลุ่มแกนนำหลักคือ <span style={{color: 'var(--red)', fontWeight: 600}}>นักศึกษา (Gen Z)</span> ที่สร้างแฮชแท็กและเกิดพฤติกรรม Echo Chamber รวมกลุ่มกันด่าทอ 
            ในขณะที่กลุ่มผู้ใหญ่หรือคนทำงาน (30%) มีท่าทีเป็นกลางหรือพยายามเข้าใจเหตุผลของมหาวิทยาลัย แต่เสียงถูกกลบไปอย่างรวดเร็ว
          </p>
          
          <h4 style={{ marginTop: '24px', marginBottom: '12px' }}>💡 Key Quotes (เสียงสะท้อนสำคัญ)</h4>
          <div className="quote-card">
            <div className="quote-text">"จะขึ้นทำไมยุคนี้? เศรษฐกิจก็แย่ คนตกงานเพียบ มหาลัยเห็นแกได้เกินไปป่าว?"</div>
            <div className="quote-author">— Agent_84 (นักศึกษา, ฝ่ายต่อต้าน)</div>
          </div>
          <div className="quote-card" style={{ borderLeftColor: 'var(--green)' }}>
            <div className="quote-text">"ก็เข้าใจนะว่าต้นทุนทุกอย่างมันขึ้น ถ้าไม่ขึ้นค่าเทอมแล้วมหาลัยจะเอาเงินที่ไหนมาจ้างอาจารย์ดีๆ"</div>
            <div className="quote-author">— Agent_12 (วัยทำงาน, ฝ่ายสนับสนุน)</div>
          </div>
        </div>

        {/* Dynamic Right Side */}
        <div className="flex-col gap-24">
          
          {/* Stance Breakdown (Always visible) */}
          <div className="card">
            <h3>สัดส่วนความเห็น (Stance Breakdown)</h3>
            <div className="mt-24 flex-col gap-16">
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px', fontSize: '14px', fontWeight: 500 }}>
                  <span>ต่อต้าน (Opposing)</span> <span style={{ color: 'var(--red)' }}>70%</span>
                </div>
                <div style={{ width: '100%', height: '8px', background: 'var(--bg)', borderRadius: '4px' }}>
                  <div style={{ width: '70%', height: '100%', background: 'var(--red)', borderRadius: '4px' }}></div>
                </div>
              </div>
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px', fontSize: '14px', fontWeight: 500 }}>
                  <span>เป็นกลาง (Neutral)</span> <span style={{ color: 'var(--beige)' }}>20%</span>
                </div>
                <div style={{ width: '100%', height: '8px', background: 'var(--bg)', borderRadius: '4px' }}>
                  <div style={{ width: '20%', height: '100%', background: 'var(--beige)', borderRadius: '4px' }}></div>
                </div>
              </div>
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px', fontSize: '14px', fontWeight: 500 }}>
                  <span>สนับสนุน (Supportive)</span> <span style={{ color: 'var(--green)' }}>10%</span>
                </div>
                <div style={{ width: '100%', height: '8px', background: 'var(--bg)', borderRadius: '4px' }}>
                  <div style={{ width: '10%', height: '100%', background: 'var(--green)', borderRadius: '4px' }}></div>
                </div>
              </div>
            </div>
          </div>

          {/* Advanced Only */}
          {isAdvanced && (
            <div className="card" style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', textAlign: 'center' }}>
              <h3>Deep Interview</h3>
              <p className="subtitle" style={{ fontSize: '13px', marginBottom: '16px' }}>
                ต้องการเจาะลึกวิธีคิดของ Agent หรือไม่?
              </p>
              <button className="btn btn-outline"><Sparkles size={16}/> สัมภาษณ์ Agent_84 (ตัวแทนฝั่งต่อต้าน)</button>
            </div>
          )}
        </div>
      </div>

      {/* Advanced Only: Trace Data Grid */}
      {isAdvanced && (
        <div className="card" style={{ height: '400px', padding: '24px', display: 'flex', flexDirection: 'column' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <div>
              <h3 style={{ margin: 0 }}>Trace Data (Log การกระทำทั้งหมด)</h3>
              <p className="subtitle" style={{ fontSize: '13px', margin: 0 }}>ใช้สำหรับอ้างอิงเชิงวิชาการ (Trace-Grounded)</p>
            </div>
            <button className="btn btn-dark" style={{ fontSize: '12px', padding: '8px 16px' }}><Download size={14} /> Export CSV</button>
          </div>
          <div className="ag-theme-alpine" style={{ flex: 1, width: '100%', border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)', overflow: 'hidden' }}>
            <AgGridReact rowData={logData} columnDefs={columnDefs} defaultColDef={{ resizable: true, filter: true }} pagination={true} paginationPageSize={10} />
          </div>
        </div>
      )}

    </div>
  );
}

// Sparkles icon (missing import in the actual file, so adding a quick inline SVG for it)
const Sparkles = ({size}) => <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 3v18M3 12h18M5 5l14 14M19 5L5 19"/></svg>
