# MiroFish TH (DEEDY)

MiroFish TH is a Thai Social Simulation Engine built upon the DEEDY methodology. It aims to simulate realistic Thai societal behaviors and information diffusion by modeling individual agents with Thai contexts, demographics, media access, and distinct public vs. private opinions.

## Project Structure

The codebase is split into two primary layers:
1. **`backend/core/` (Simulation Engine):** The heart of the simulation handling synthetic populations, scenarios, agent states, private/public expression filters, and interactions.
2. **`backend/app/` (Application Layer):** The API wrapper and legacy logic exposing the simulation to external interfaces.
3. **`frontend-v2/` (Web UI):** A modern React 19 + Three.js + React Router application for visualizing the social graphs and simulation results.

*(Note: `frontend/` and `next-frontend/` are deprecated in favor of `frontend-v2/`)*

## Quick Start (Backend)

The backend is built with FastAPI/Flask and relies heavily on LLM calls (via OpenAI SDK format) to power the agents.

### 1. Requirements

Ensure you have Python 3.11+ installed. We recommend using `uv` for dependency management.

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Environment Variables

Create a `.env` file in the project root with your OpenRouter configuration:

```ini
OPENROUTER_API_KEY="sk-or-v1-your-key-here"
LLM_BASE_URL="https://openrouter.ai/api/v1"
LLM_MODEL_NAME="deepseek/deepseek-v4-flash-0731"
LLM_COMPARISON_MODEL_NAME="qwen/qwen3-8b"
```

### 3. Run the Server

```bash
cd backend
uvicorn main:app --reload
```

## Quick Start (Frontend-v2)

```bash
cd frontend-v2
npm install
npm run dev
```

## Core Methodology Highlights

- **Private vs. Public Stance**: The engine actively models the "Preference Falsification" gap. Agents have private opinions but filter them through fear of legal repercussions and social deference before posting publicly.
- **Thai NLP Processing**: Native integration for Thai text chunking, embedding, and NLP tasks for Retrieval-Augmented Generation (RAG).
- **Offline Actions**: Agents don't just "post" on social media. They can interact offline, join LINE groups, or take silent actions (like boycotts).

Please refer to `PLAN.md` and `project_ideas_and_research.md` for complete architectural design and research context.
