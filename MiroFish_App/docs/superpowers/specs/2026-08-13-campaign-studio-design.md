# Design Spec: MarketFish Campaign Studio

## 1. Overview
The **Campaign Studio** is a frontend UI module that allows marketers to configure and launch a MarketFish simulation without touching JSON files or the terminal. It acts as a 3-step wizard, transforming user inputs into a structured `simulation_config.json` payload, which is then sent to the backend to trigger the simulation.

## 2. User Journey (3-Step Wizard)

### Step 1: Campaign Brief (เนื้อหาแคมเปญ)
- **Campaign Topic:** The main subject or brand name.
- **Content / Caption:** The text of the social media post or the crisis event description.
- **Target Platform:** e.g., Twitter (X), TikTok, Facebook (influences agent behavior).

### Step 2: Target Audience & Environment (กลุ่มเป้าหมายและสภาพแวดล้อม)
- **KOL Ratio:** Slider to determine what percentage of agents are Cognitive LLM KOLs (e.g., 1% to 10%).
- **Bot / IO Injection (Stress Test):** Slider (0% - 30%) to simulate a coordinated bot attack during the campaign. If > 0%, bots will inject negative sentiments into the stream to test organic resilience.
- **Simulation Speed/Time:** Define how many rounds to run (e.g., 24 hours).

### Step 3: Review & Launch (ตรวจสอบและเริ่มรัน)
- A summary screen showing the configuration.
- A glowing **"Deploy Campaign"** button.
- Upon clicking, the UI shows a loading state, calls the backend API, and redirects to the `/live` Matrix Feed dashboard once the simulation initializes.

## 3. Architecture & Data Flow

### Frontend (`frontend-v2/src/pages/CampaignStudio.jsx`)
- Built using React state to manage the wizard form data.
- Styled with the Premium Dark Mode and Glassmorphism aesthetics defined in `index.css`.
- API Call: `POST /api/simulation/start` with the JSON payload.

### Backend (`backend/app/main.py` & API Routes)
- **Endpoint:** `POST /api/simulation/start`
- **Logic:**
  1. Receives the configuration payload.
  2. Generates a unique `sim_id` and directory.
  3. Writes the payload to `data/simulations/{sim_id}/simulation_config.json`.
  4. Spawns `run_marketfish_simulation.py` as an asynchronous background subprocess.
  5. Returns `{ "status": "started", "sim_id": "..." }` to the frontend.

## 4. Error Handling
- **Invalid Inputs:** Frontend validation ensures no empty captions or extreme (invalid) percentages.
- **API Failure:** If the backend fails to spawn the process, the Studio shows an inline error alert instead of redirecting.

## 5. Scope Boundaries
- **In Scope:** The UI wizard, the backend API route to start the process, and the JSON payload generation.
- **Out of Scope:** We will not be generating dynamic Agent Populations in this phase; we will rely on the existing `population_200.json` and partition them based on the KOL ratio slider.
