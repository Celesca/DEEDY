import React, { useContext, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { AppContext } from '../App';
import { UploadCloud, Play, Sparkles } from 'lucide-react';

export default function CreateScenario() {
  const { isAdvanced } = useContext(AppContext);
  const navigate = useNavigate();
  const [selectedPreset, setSelectedPreset] = useState(null);

  const presets = [
    { id: 'tuition', emoji: '🎓', label: 'มหาวิทยาลัยขึ้นค่าเทอม' },
    { id: 'policy', emoji: '🏛️', label: 'รัฐบาลออกนโยบายภาษีใหม่' },
    { id: 'brand', emoji: '📺', label: 'แบรนด์ออกโฆษณาเหยียดเพศ' },
  ];

  const handleStart = () => {
    navigate('/live');
  };

  return (
    <div className="flex-col gap-24 mt-24">
      
      <div className="card">
        <h2>สร้างสถานการณ์จำลอง (Create Scenario)</h2>
        <p className="subtitle">
          {isAdvanced 
            ? 'กำหนดพารามิเตอร์เชิงลึกสำหรับการจำลอง ตั้งแต่โครงสร้างประชากรไปจนถึงแพลตฟอร์มเป้าหมาย' 
            : 'บอกมาสั้นๆ ว่าจะเกิดอะไรขึ้น แล้วให้ระบบจำลองว่าสังคมจะตอบสนองยังไง'}
        </p>

        <div className="mt-32 flex-col gap-24">
          
          {/* Common Input */}
          <div className="input-group">
            <label>เหตุการณ์ตั้งต้น (Scenario Prompt)</label>
            <textarea placeholder="พิมพ์เรื่องราว, ข่าว, หรือสถานการณ์ที่คุณอยากให้ชาวเน็ตจำลองวิจารณ์..." />
          </div>

          {!isAdvanced && (
            <div className="input-group mt-24">
              <label style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Sparkles size={14} color="var(--blue)" /> เลือกเหตุการณ์สำเร็จรูป (Presets)
              </label>
              <div className="preset-grid">
                {presets.map(p => (
                  <div 
                    key={p.id} 
                    className={`preset-tag ${selectedPreset === p.id ? 'selected' : ''}`}
                    onClick={() => setSelectedPreset(p.id)}
                  >
                    <span className="emoji">{p.emoji}</span> {p.label}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Advanced Only Controls */}
          {isAdvanced && (
            <div className="grid-2 mt-24" style={{ padding: '24px', background: 'var(--bg)', borderRadius: 'var(--radius-sm)' }}>
              
              <div className="flex-col gap-16">
                <div className="slider-group">
                  <div className="slider-label">
                    <span>กลุ่มอายุหลัก (Gen Z ↔ ผู้ใหญ่)</span>
                    <span>50%</span>
                  </div>
                  <input type="range" min="0" max="100" defaultValue="50" />
                </div>
                <div className="slider-group">
                  <div className="slider-label">
                    <span>แพลตฟอร์ม</span>
                    <span style={{color: 'var(--text)'}}>Twitter (X)</span>
                  </div>
                  <select style={{ padding: '8px', borderRadius: '6px', border: '1px solid var(--border)' }}>
                    <option>Twitter (X)</option>
                    <option>Pantip</option>
                    <option>Facebook</option>
                  </select>
                </div>
              </div>

              <div className="file-drop">
                <UploadCloud className="icon" />
                <p><strong>อัปโหลด Dataset ข่าวอ้างอิง</strong></p>
                <p className="text-sm mt-2">รองรับ .pdf, .txt, .csv</p>
              </div>

            </div>
          )}

          <button className="btn btn-primary btn-lg mt-24" style={{ alignSelf: 'flex-start' }} onClick={handleStart}>
            <Play size={18} /> เริ่มจำลองสถานการณ์
          </button>

        </div>
      </div>

    </div>
  );
}
