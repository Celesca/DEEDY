# Persona Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Integrate the Thai persona generation script into the web app, allowing users to seed the simulation with data-driven personas in `CampaignStudio.jsx`.

**Architecture:** We will add a `POST /api/personas/generate` endpoint that calls the logic from `generate_thai_personas.py`. The frontend will call this in Step 1 of the Campaign Studio wizard. The custom personas are then passed to the `/marketfish/start` endpoint, saved as `custom_population.json`, and injected into `run_thai_society_simulation.py`.

**Tech Stack:** Python (Flask), React.

## Global Constraints
- Do not block the UI for too long; a synchronous LLM call is acceptable if it's within 30 seconds.
- The `generate_thai_personas` script outputs a list of dicts matching `AgentProfile` fields.

---

### Task 1: Backend API for Persona Generation

**Files:**
- Modify: `backend/app/api/simulation.py`
- Modify: `backend/scripts/generate_thai_personas.py`

**Interfaces:**
- Consumes: `POST /api/simulation/personas/generate`
- Produces: JSON `{"personas": [...]}`

- [ ] **Step 1: Refactor generation script for import**
Modify `backend/scripts/generate_thai_personas.py` to extract the core logic into a reusable function:
```python
def generate_personas_sync(sample_size=30, max_personas=5):
    # Move the LLM calling logic here and return the list of dicts.
    pass
```

- [ ] **Step 2: Add API endpoint**
In `backend/app/api/simulation.py`, append:
```python
from scripts.generate_thai_personas import generate_personas_sync

@simulation_bp.route('/personas/generate', methods=['POST'])
def generate_personas():
    try:
        personas = generate_personas_sync(sample_size=20, max_personas=4)
        return jsonify({"personas": personas})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
```

### Task 2: Frontend Campaign Studio Wizard Update

**Files:**
- Modify: `frontend-v2/src/pages/CampaignStudio.jsx`

**Interfaces:**
- Consumes: `POST /api/simulation/personas/generate`
- Produces: `generatedPersonas` in component state.

- [ ] **Step 1: Shift Wizard Steps**
Change step numbers: Campaign Definition becomes Step 2, Swarm Config is Step 3, Checklist is Step 4. Step 1 will be "Target Audience & Personas".

- [ ] **Step 2: Add Step 1 UI**
Add a new `div` for `step === 1` with a button "Generate Audience from DEEDY Data". When clicked, call the new endpoint, show a loading spinner, and render the returned personas as small cards or badges. Save to `const [generatedPersonas, setGeneratedPersonas] = useState([])`.

- [ ] **Step 3: Pass custom personas to Start API**
In `handleDeploy`, include `custom_personas: generatedPersonas` in the body sent to `/marketfish/start`.

### Task 3: Backend Custom Population Injection

**Files:**
- Modify: `backend/app/api/simulation.py`
- Modify: `backend/scripts/run_thai_society_simulation.py`

**Interfaces:**
- Consumes: `custom_personas` from frontend payload.
- Produces: `custom_population.json`

- [ ] **Step 1: Save custom population**
In `backend/app/api/simulation.py` -> `start_marketfish_simulation`, check for `data.get("custom_personas")`. If present, write to `os.path.join(sim_dir, "custom_population.json")`.
Ensure the runner is set to `run_thai_society_simulation.py`.

- [ ] **Step 2: Load custom population in runner**
In `backend/scripts/run_thai_society_simulation.py`, update `fallback_population()` or the main execution flow to check if `custom_population.json` exists in `sim_dir`. If so, load it and map the dicts to `AgentProfile` objects instead of using the hardcoded fallback.
