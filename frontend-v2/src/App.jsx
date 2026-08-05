import React, { useState, createContext } from 'react';
import { BrowserRouter, Routes, Route, NavLink, Navigate } from 'react-router-dom';
import { LayoutDashboard, Users, Activity, FileBarChart, Settings, Bell, Search } from 'lucide-react';

import CreateScenario from './pages/CreateScenario';
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
              <NavLink to="/create" className={({isActive}) => isActive ? 'sidebar-link active' : 'sidebar-link'}>
                <LayoutDashboard size={20} /> Scenario Studio
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
            <header className="topbar">
              
              {/* Search Bar (Claymorphism style) */}
              <div style={{ flex: 1, display: 'flex' }}>
                <div style={{
                  display: 'flex', alignItems: 'center', gap: '12px',
                  background: 'var(--card)', padding: '12px 24px', borderRadius: 'var(--radius)',
                  boxShadow: 'var(--shadow-clay)', color: 'var(--text-light)', width: '300px'
                }}>
                  <Search size={18} />
                  <span style={{ fontSize: '14px' }}>Search scenarios...</span>
                </div>
              </div>

              {/* Simple / Advanced Toggle */}
              <div className="toggle-wrapper" style={{ boxShadow: 'var(--shadow-clay)' }}>
                <span className={`toggle-label ${!isAdvanced ? 'active' : ''}`} onClick={() => setIsAdvanced(false)}>
                  Simple
                </span>
                <div 
                  className={`toggle-switch ${isAdvanced ? 'advanced' : ''}`}
                  onClick={() => setIsAdvanced(!isAdvanced)}
                >
                  <div className="toggle-thumb" style={{ boxShadow: 'var(--shadow-clay)' }}></div>
                </div>
                <span className={`toggle-label ${isAdvanced ? 'active' : ''}`} onClick={() => setIsAdvanced(true)}>
                  Advanced
                </span>
              </div>

              {/* Notification Bell (3D effect simulation) */}
              <div style={{
                background: 'var(--primary-yellow)',
                color: '#B45309',
                width: '48px', height: '48px',
                borderRadius: '50%',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                boxShadow: '4px 8px 16px rgba(250, 204, 21, 0.4), inset -4px -4px 8px rgba(217, 119, 6, 0.4), inset 4px 4px 8px rgba(254, 240, 138, 1)',
                cursor: 'pointer'
              }}>
                <Bell size={24} strokeWidth={2.5} />
              </div>
              
              {/* Profile Avatar */}
              <div style={{
                width: '48px', height: '48px',
                borderRadius: '50%',
                background: 'var(--card)',
                boxShadow: 'var(--shadow-clay)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontWeight: 'bold', color: 'var(--primary-blue)'
              }}>
                OP
              </div>
            </header>

            {/* Main Page Area */}
            <main className="page">
              <Routes>
                <Route path="/" element={<Navigate to="/create" replace />} />
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
