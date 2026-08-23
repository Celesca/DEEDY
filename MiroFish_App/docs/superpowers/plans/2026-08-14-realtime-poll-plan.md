# Realtime Poll API Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove the mockup data in the `LiveSimulation` dashboard by implementing a `/poll` API that parses `actions.jsonl` and serves real-time metrics and agent actions to the frontend.

**Architecture:**
- **Backend:** A new Flask route `GET /api/simulation/<sim_id>/poll`. It will open the `actions.jsonl` file for the given `sim_id` and platform (e.g., `marketfish`), aggregate sentiments per round (positive/negative/bots), and collect the most recent actions.
- **Frontend:** Remove the `isLive` mock fallback in `LiveSimulation.jsx` and map the true data from the API to the Recharts graph and Matrix Feed.

**Tech Stack:** Python (Flask), React (Recharts).

## Global Constraints
- Read `actions.jsonl` directly. Keep parsing efficient (e.g., read the last 1000 lines if the file gets too big, or just read all lines since this is a lightweight simulation).
- The bot count is defined as actions where `action_type == "BOT_ATTACK"`.
- Positive sentiment = actions where `private_stance == "supporting"` or `neutral`.
- Negative sentiment = actions where `private_stance == "opposing"`.

---

### Task 1: Backend `/poll` Endpoint

**Files:**
- Modify: `backend/app/api/simulation.py`

**Interfaces:**
- Consumes: `GET /api/simulation/<sim_id>/poll`
- Produces: JSON `{"pulse_history": [...], "recent_actions": [...]}`

- [ ] **Step 1: Write the endpoint logic**
Append the new route to `backend/app/api/simulation.py`:
```python
@simulation_bp.route('/<simulation_id>/poll', methods=['GET'])
def poll_simulation(simulation_id: str):
    try:
        sim_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", simulation_id)
        
        # Action logger writes to sim_dir/<platform>/actions.jsonl
        log_path = os.path.join(sim_dir, "marketfish", "actions.jsonl")
        
        if not os.path.exists(log_path):
            log_path = os.path.join(sim_dir, "thai_society", "actions.jsonl")
            if not os.path.exists(log_path):
                return jsonify({"pulse_history": [], "recent_actions": []})

        pulse_history = []
        recent_actions = []
        
        round_stats = {} # round -> {positive, negative, bots}
        
        with open(log_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        for line in lines:
            if not line.strip(): continue
            try:
                entry = json.loads(line)
                round_num = entry.get("round", 0)
                if round_num not in round_stats:
                    round_stats[round_num] = {"time": round_num, "positive": 0, "negative": 0, "bots": 0}
                
                # Check event type
                event_type = entry.get("event_type")
                if not event_type: # It's an action
                    recent_actions.append(entry)
                    action_type = entry.get("action_type", "")
                    stance = entry.get("action_args", {}).get("private_stance", "")
                    
                    if action_type == "BOT_ATTACK":
                        round_stats[round_num]["bots"] += 1
                    elif stance == "opposing":
                        round_stats[round_num]["negative"] += 1
                    else:
                        round_stats[round_num]["positive"] += 1
                        
            except:
                pass
                
        # Format pulse history
        pulse_history = [stats for _, stats in sorted(round_stats.items()) if stats["positive"] > 0 or stats["negative"] > 0 or stats["bots"] > 0]
        
        # Take last 50 actions for the matrix feed
        recent_actions = recent_actions[-50:]
        recent_actions.reverse() # Newest first
        
        return jsonify({
            "pulse_history": pulse_history,
            "recent_actions": recent_actions
        })
        
    except Exception as e:
        logger.error(f"Poll failed: {str(e)}")
        return jsonify({"error": str(e)}), 500
```

### Task 2: Frontend Update

**Files:**
- Modify: `frontend-v2/src/pages/LiveSimulation.jsx`

**Interfaces:**
- Consumes: The new `/poll` endpoint JSON format.

- [ ] **Step 1: Map the Real Data**
In `LiveSimulation.jsx`, update the mapping logic:
```javascript
        if (data.pulse_history && data.pulse_history.length > 0) {
           const mapped = data.pulse_history.map(p => ({
             time: p.time,
             positive: p.positive,
             negative: p.negative,
             bots: p.bots
           }));
           setPulseData(mapped);
        }
        
        if (data.recent_actions && data.recent_actions.length > 0) {
           const mapped = data.recent_actions.map(a => ({
             id: a.timestamp + a.agent_id,
             user: a.agent_name || `Agent ${a.agent_id}`,
             publicAction: a.action_type,
             text: a.action_args?.post_text || a.action_args?.private_text || '',
             privateStance: a.action_args?.private_stance || 'neutral',
             isLLM: a.action_args?.is_llm || false
           }));
           // Directly set from API since the API already returns the latest 50 reversed
           setActions(mapped);
        }
```

- [ ] **Step 2: Remove the Mock Fallback**
Remove `displayData` and just use `pulseData` directly in the `AreaChart`.
```javascript
<AreaChart data={pulseData} ...>
```
