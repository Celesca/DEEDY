# Phase 6 Design Specification: Society-level Metrics & Frontend Integration

## Overview
This document outlines the design for Phase 6 of the MiroFish TH (DEEDY) project. The goal is to connect the simulation engine (`core/` and `scripts/run_thai_society_simulation.py`) to the web interface (`frontend-v2/` and `app/api/`) and present society-level metrics—specifically the "Preference Falsification Gap" (the difference between private opinions and public expressions).

## 1. Backend Runner & Logger (`run_thai_society_simulation.py` & `action_logger.py`)
- **Action Logging:** Ensure the Simulation Engine logs both `private_opinion` (stance, intensity, reason) and `public_expression` (action, content) for *every* agent during *every* round, even if the agent's chosen action is `SILENT_SHIFT`.
- **IPC Server Readiness:** The script currently spins up `SimulationIPCServer("thai_society")`. Ensure it responds to `INTERVIEW` commands by returning the agent's private reasoning.
- **Platform Choice:** `SimulationRunner.start_simulation()` will be updated (if not already) to accept `"thai_society"` as a valid simulation type, bypassing the older Twitter/Reddit specific setups.

## 2. API Integration (`app/api/`)
- **Endpoints:** The existing Flask API (`/api/simulations/<id>/status` and `/api/simulations/<id>/actions`) must successfully read the `thai_society` formatted `actions.jsonl` files.
- **Data Contract:** The frontend expects the JSON lines to contain the `action_args` with embedded `private_stance`, `private_text`, and `post_text`. The API should serve these without filtering them out.

## 3. Frontend Dashboard (`frontend-v2/`)
- **Aggregate View (Top Section):**
  - A new Dashboard view that aggregates the latest round's actions.
  - **Visualization:** A Bar Chart or Gauge displaying the proportion of "True Stance" vs "Expressed Stance". This clearly visualizes the Preference Falsification Gap.
- **Drill-down View (Bottom Section):**
  - A list or grid of Agent Cards.
  - **Interaction:** Clicking an agent card flips or expands it to reveal their `private_opinion` and the justification for their action (even if they stayed silent).
  - **Interview:** A button on the card to trigger a manual "Interview" with the agent via the IPC server.

## 4. Testing & Verification (Self-Review)
- **Placeholder Scan:** No TBDs. The design explicitly covers logging, API, and UI.
- **Scope Check:** This is focused purely on Phase 6 (connecting existing engine outputs to the UI). It does not leak into Phase 3 (Ingestion) or Phase 7 (Leakage Protocol).
- **Ambiguity:** "True Stance vs Expressed Stance" is well-defined as the gap between `private_opinion.stance` and the actual `action_key` chosen.

