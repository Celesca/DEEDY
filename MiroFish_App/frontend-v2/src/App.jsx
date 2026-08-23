import React, { useState, createContext } from 'react';
import { BrowserRouter, Routes, Route, NavLink, Navigate } from 'react-router-dom';
import { LayoutDashboard, Users, Activity, FileBarChart, Settings, Bell, Search } from 'lucide-react';

import CreateScenario from './pages/CreateScenario';
import CampaignStudio from './pages/CampaignStudio';
import LiveSimulation from './pages/LiveSimulation';
import InsightReport from './pages/InsightReport';

export const AppContext = createContext();

export default function App() {
  const [isAdvanced, setIsAdvanced] = useState(false);

  return (
    <AppContext.Provider value={{ isAdvanced, setIsAdvanced }}>
      <BrowserRouter>
        <div className="app-shell">
          
          {/* Left Sidebar */}
          <aside className="sidebar">
            <div className="sidebar-logo">
              MiroFish <span>PRO</span>
            </div>
            
            <nav className="sidebar-nav">
              <NavLink to="/studio" className={({isActive}) => isActive ? 'sidebar-link active' : 'sidebar-link'}>
                <LayoutDashboard size={20} /> Campaign Studio
              </NavLink>
              <NavLink to="/live" className={({isActive}) => isActive ? 'sidebar-link active' : 'sidebar-link'}>
                <Activity size={20} /> Live Arena
              </NavLink>
              <NavLink to="/report" className={({isActive}) => isActive ? 'sidebar-link active' : 'sidebar-link'}>
                <FileBarChart size={20} /> Insight Reports
              </NavLink>
              <div style={{ flex: 1, minHeight: '40px' }}></div>
              <NavLink to="/settings" className="sidebar-link" onClick={(e) => e.preventDefault()}>
                <Settings size={20} /> Settings
              </NavLink>
            </nav>
          </aside>

          {/* Main Content Wrapper */}
          <div className="main-wrapper">
            
            {/* Top Header */}
            <header className="topbar" style={{ padding: '16px 24px', background: '#FFFFFF', borderBottom: '1px solid var(--border)', gap: '16px' }}>
              
              {/* Search Bar */}
              <div style={{ flex: 1, display: 'flex' }}>
                <div style={{
                  display: 'flex', alignItems: 'center', gap: '8px',
                  background: '#F8FAFC', padding: '8px 16px', borderRadius: '6px',
                  border: '1px solid var(--border)', color: 'var(--text-muted)', width: '280px'
                }}>
                  <Search size={16} />
                  <input type="text" placeholder="Search scenarios..." style={{ 
                    background: 'transparent', border: 'none', color: 'var(--text)', 
                    fontSize: '13px', width: '100%', outline: 'none', padding: 0
                  }} />
                </div>
              </div>

              {/* Simple / Advanced Toggle */}
              <div className="toggle-wrapper" style={{ 
                background: '#F8FAFC', border: '1px solid var(--border)', padding: '4px 8px'
              }}>
                <span className={`toggle-label ${!isAdvanced ? 'active' : ''}`} onClick={() => setIsAdvanced(false)}>
                  Simple
                </span>
                <div 
                  className={`toggle-switch ${isAdvanced ? 'advanced' : ''}`}
                  onClick={() => setIsAdvanced(!isAdvanced)}
                  style={{ background: isAdvanced ? 'var(--primary-blue)' : '#CBD5E1' }}
                >
                  <div className="toggle-thumb"></div>
                </div>
                <span className={`toggle-label ${isAdvanced ? 'active' : ''}`} onClick={() => setIsAdvanced(true)}>
                  Advanced
                </span>
              </div>

              {/* Notification Bell */}
              <div className="hover-transition" style={{
                background: '#FFFFFF', border: '1px solid var(--border)',
                color: 'var(--text-muted)', width: '36px', height: '36px', borderRadius: '6px',
                display: 'flex', alignItems: 'center', justifyContent: 'center'
              }}>
                <Bell size={18} />
              </div>
              
              {/* Profile Avatar */}
              <div className="hover-transition" style={{
                width: '36px', height: '36px', borderRadius: '6px',
                background: 'var(--primary-blue)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontWeight: '600', color: 'white', fontSize: '13px'
              }}>
                OP
              </div>
            </header>

            {/* Main Page Area */}
            <main className="page">
              <Routes>
                <Route path="/" element={<Navigate to="/studio" replace />} />
                <Route path="/studio" element={<CampaignStudio />} />
                <Route path="/create" element={<CreateScenario />} />
                <Route path="/live" element={<LiveSimulation />} />
                <Route path="/report" element={<InsightReport />} />
              </Routes>
            </main>
          </div>

        </div>
      </BrowserRouter>
    </AppContext.Provider>
  );
}
