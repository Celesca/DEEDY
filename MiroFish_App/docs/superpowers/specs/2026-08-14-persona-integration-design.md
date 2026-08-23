# Phase 6.5 Design: Persona Integration (Campaign Studio)

## Overview
Integrate the Thai Persona Generation script directly into the web application. Users will be able to generate and inject realistic Thai netizen personas into their simulation directly from the Campaign Studio.

## Selected Approach
**Option 1: Campaign Studio Step 0**
The persona generation will be integrated as the very first step in the `CampaignStudio.jsx` wizard. 

## 1. Backend API (`app/api/personas.py` or `app/api/simulation.py`)
- **Endpoint:** `POST /api/personas/generate`
- **Functionality:** 
  - Imports the logic from `scripts/generate_thai_personas.py`.
  - Runs the LLM extraction process asynchronously or synchronously (since it's a small sample, ~15-20s, sync might be acceptable, but async with polling is safer). For MVP, we will try synchronous generation with a long timeout, or adapt the existing `/generate` threading pattern.
- **Output:** Returns a JSON array of generated `AgentProfile` objects.

## 2. Frontend Wizard (`CampaignStudio.jsx`)
- **Step 0: Population Seeding:**
  - UI: A prominent button "Generate Audience from Real Data (DEEDY)".
  - Interaction: Clicking it shows a loading spinner ("Analyzing Thai Social Data...").
  - Result: Once complete, it displays the generated personas (e.g., "5 Archetypes Generated: The Angry Boomer, The Woke GenZ, etc.") in small pill badges.
- **Wizard Flow:**
  - Step 1 (was 1): Define Campaign
  - Step 2 (was 2): Swarm Configuration
  - Step 3 (was 3): Pre-Flight Checklist
- **State Management:**
  - The generated personas will be stored in the component state and passed along in the `handleDeploy` POST request to `/start`.

## 3. Backend Simulation Runner Updates
- The `/start` endpoint in `simulation.py` must accept the custom `personas` array from the frontend and write them to `data/<sim_id>/population.json` or pass them directly to the `Population` initializer, bypassing the default static fallback population.
