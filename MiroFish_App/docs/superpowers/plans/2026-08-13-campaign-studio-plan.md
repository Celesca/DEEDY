# Campaign Studio Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a 3-step UI wizard and a backend endpoint to configure and launch a MarketFish simulation without manual JSON editing.

**Architecture:** A React functional component holding wizard state, making a `POST` request to a new Flask route, which writes `simulation_config.json` and spawns `run_marketfish_simulation.py` via `subprocess.Popen`.

**Tech Stack:** React 19, Flask, Python `subprocess`.

## Global Constraints
- Target platform: macOS
- Backend uses port 5001 (based on previous config)
- Premium dark mode aesthetics from `index.css` must be used in the UI.
- No dynamic population generation in this phase; use existing `population_200.json`.

---

### Task 1: Backend API Endpoint (Simulation Launcher)

**Files:**
- Modify: `backend/app/api/simulation.py`

**Interfaces:**
- Consumes: JSON payload from frontend with `campaign_brief`, `kol_ratio`, `bot_injection_percentage`.
- Produces: JSON response `{"status": "started", "sim_id": <sim_id>}`.

- [ ] **Step 1: Write the endpoint logic**
Append the new route to `simulation.py`:
```python
import subprocess
import time
from flask import request, jsonify

@simulation_bp.route('/marketfish/start', methods=['POST'])
def start_marketfish_simulation():
    data = request.json
    sim_id = f"marketfish_{int(time.time())}"
    sim_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", sim_id)
    os.makedirs(sim_dir, exist_ok=True)
    
    config = {
        "seed": 42,
        "bot_injection_percentage": data.get("bot_injection_percentage", 0.0),
        "kol_ratio": data.get("kol_ratio", 0.05),
        "time_config": {
            "total_simulation_hours": 24,
            "minutes_per_round": 60
        },
        "events": [
            {
                "scheduled_hour": 1,
                "description": data.get("campaign_brief", "Default campaign text"),
                "channel": data.get("target_platform", "X"),
                "state_threat_level": 50
            }
        ]
    }
    
    config_path = os.path.join(sim_dir, "simulation_config.json")
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
        
    runner_script = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "scripts", "run_marketfish_simulation.py")
    subprocess.Popen([sys.executable, runner_script, "--config", config_path])
    
    return jsonify({"status": "started", "sim_id": sim_id})
```

- [ ] **Step 2: Commit backend changes**
```bash
git add backend/app/api/simulation.py
git commit -m "feat(backend): add /marketfish/start endpoint for Campaign Studio"
```

### Task 2: Frontend Routing

**Files:**
- Modify: `frontend-v2/src/App.jsx`

**Interfaces:**
- Exposes `/studio` route to users.

- [ ] **Step 1: Import and Add Route**
Update `App.jsx` to import `CampaignStudio` and add it to the React Router routes list.
```jsx
import CampaignStudio from './pages/CampaignStudio';
// Inside <Routes>:
// <Route path="/studio" element={<CampaignStudio />} />
```

- [ ] **Step 2: Add Sidebar Link**
Update the Sidebar in `App.jsx` to include a link to `/studio`.
```jsx
<Link to="/studio" className="sidebar-link">
  <span>🎬 Campaign Studio</span>
</Link>
```

- [ ] **Step 3: Commit frontend routing**
```bash
git add frontend-v2/src/App.jsx
git commit -m "feat(frontend): add /studio route and sidebar link"
```

### Task 3: Campaign Studio UI (The Wizard)

**Files:**
- Create: `frontend-v2/src/pages/CampaignStudio.jsx`

**Interfaces:**
- Consumes: User inputs via React state.
- Produces: `POST` request to `http://127.0.0.1:5001/api/simulation/marketfish/start`.

- [ ] **Step 1: Write `CampaignStudio.jsx`**
Implement the 3-step wizard.
```jsx
import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';

export default function CampaignStudio() {
  const navigate = useNavigate();
  const [step, setStep] = useState(1);
  const [formData, setFormData] = useState({
    campaign_brief: '',
    target_platform: 'X',
    kol_ratio: 0.05,
    bot_injection_percentage: 0.0
  });
  
  const handleNext = () => setStep(s => s + 1);
  const handleBack = () => setStep(s => s - 1);
  
  const handleLaunch = async () => {
    try {
      const res = await fetch('http://127.0.0.1:5001/api/simulation/marketfish/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData)
      });
      const data = await res.json();
      if (data.status === 'started') {
        // Option to pass sim_id via context or just navigate
        navigate('/live');
      }
    } catch (e) {
      alert("Error starting simulation");
    }
  };

  return (
    <div className="flex-col gap-24 mt-24">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h1 style={{ color: 'var(--text)' }}>Campaign Studio</h1>
          <p className="subtitle">Configure and launch a new MarketFish simulation</p>
        </div>
      </div>
      
      <div className="glass-panel" style={{ padding: '32px', borderRadius: 'var(--radius)' }}>
        {step === 1 && (
          <div className="flex-col gap-12">
            <h2>Step 1: Campaign Brief</h2>
            <textarea 
              style={{ width: '100%', height: '100px', padding: '12px', background: 'var(--bg)', color: 'var(--text)', border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)' }}
              value={formData.campaign_brief}
              onChange={e => setFormData({...formData, campaign_brief: e.target.value})}
              placeholder="Enter your campaign copy or crisis event description..."
            />
            <button className="btn btn-primary" onClick={handleNext}>Next</button>
          </div>
        )}
        
        {step === 2 && (
          <div className="flex-col gap-12">
            <h2>Step 2: Audience & Environment</h2>
            <label style={{ color: 'var(--text-muted)' }}>Bot Attack Probability (Stress Test): {formData.bot_injection_percentage}</label>
            <input 
              type="range" min="0" max="0.3" step="0.05"
              value={formData.bot_injection_percentage}
              onChange={e => setFormData({...formData, bot_injection_percentage: parseFloat(e.target.value)})}
            />
            <div style={{ display: 'flex', gap: '12px' }}>
              <button className="btn btn-outline" onClick={handleBack}>Back</button>
              <button className="btn btn-primary" onClick={handleNext}>Next</button>
            </div>
          </div>
        )}
        
        {step === 3 && (
          <div className="flex-col gap-12">
            <h2>Step 3: Review & Launch</h2>
            <pre style={{ background: 'var(--bg)', padding: '16px', color: 'var(--text-muted)', borderRadius: 'var(--radius-sm)' }}>
              {JSON.stringify(formData, null, 2)}
            </pre>
            <div style={{ display: 'flex', gap: '12px' }}>
              <button className="btn btn-outline" onClick={handleBack}>Back</button>
              <button className="btn btn-primary" onClick={handleLaunch}>Deploy Campaign</button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Commit Campaign Studio component**
```bash
git add frontend-v2/src/pages/CampaignStudio.jsx
git commit -m "feat(frontend): create 3-step Campaign Studio wizard UI"
```
