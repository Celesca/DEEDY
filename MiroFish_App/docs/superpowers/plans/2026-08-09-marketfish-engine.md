# MarketFish Phase 1: Core Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the foundational backend simulation engine using `qwen/qwen3.7-flash` for agent interactions and a large model for reflection and analytics.

**Architecture:** A Python backend utilizing asynchronous processing (asyncio) for the tick system, Redis for short-term memory, and ChromaDB for long-term memory. LLM routing is handled by a central gateway.

**Tech Stack:** Python, FastAPI (for future frontend connection), Redis, ChromaDB, LiteLLM (or custom OpenAI-compatible client) for routing, Pytest.

## Global Constraints
- Agent Cognitive tasks (actions, comments, likes) MUST use the **qwen/qwen3.7-flash** model to control costs at scale (Reasoning DISABLED).
- Summarization, Reflection, and Marketing Analyst tasks MUST use **google/gemini-3.6-flash** with Reasoning ENABLED for deep marketing insights.
- All agent LLM responses must be strictly structured JSON.
- Follow Test-Driven Development (TDD).

---

### Task 1: LLM Gateway & Routing Configuration

**Files:**
- Create: `backend/core/llm_gateway.py`
- Create: `tests/core/test_llm_gateway.py`

**Interfaces:**
- Consumes: System environment variables for API keys.
- Produces: `generate_agent_action(prompt: str) -> dict` and `generate_reflection(prompt: str) -> str`

- [ ] **Step 1: Write the failing test**
```python
import pytest
from backend.core.llm_gateway import generate_agent_action, generate_reflection

@pytest.mark.asyncio
async def test_generate_agent_action_returns_dict():
    # Mock the underlying API call
    result = await generate_agent_action("System: You are an agent...", model="deepseek-flash")
    assert isinstance(result, dict)
    assert "action" in result

@pytest.mark.asyncio
async def test_generate_reflection_uses_large_model():
    result = await generate_reflection("Summarize this: ...")
    assert isinstance(result, str)
```

- [ ] **Step 2: Run test to verify it fails**
Run: `pytest tests/core/test_llm_gateway.py -v`
Expected: FAIL with ModuleNotFoundError or NameError.

- [ ] **Step 3: Write minimal implementation**
```python
# backend/core/llm_gateway.py
import json

async def generate_agent_action(prompt: str, model: str = "deepseek-flash") -> dict:
    # Minimal mock implementation for the test to pass
    # Real implementation will use actual API client
    return {"action": "IGNORE", "sentiment": 0}

async def generate_reflection(prompt: str, model: str = "large-model") -> str:
    return "Reflected summary"
```

- [ ] **Step 4: Run test to verify it passes**
Run: `pytest tests/core/test_llm_gateway.py -v`
Expected: PASS

- [ ] **Step 5: Commit**
```bash
git add tests/core/test_llm_gateway.py backend/core/llm_gateway.py
git commit -m "feat: setup LLM gateway and routing stubs for DeepSeek Flash and Large models"
```

### Task 2: Dual-Memory Interface (Redis & ChromaDB)

**Files:**
- Create: `backend/core/memory.py`
- Create: `tests/core/test_memory.py`

**Interfaces:**
- Consumes: `generate_reflection` from Task 1.
- Produces: `MemoryManager` class with `add_short_term`, `get_short_term`, and `reflect_to_long_term`.

- [ ] **Step 1: Write the failing test**
```python
import pytest
from backend.core.memory import MemoryManager

@pytest.mark.asyncio
async def test_memory_manager_short_term():
    manager = MemoryManager()
    await manager.add_short_term("agent_1", "Saw a funny post")
    memories = await manager.get_short_term("agent_1")
    assert len(memories) == 1
    assert "funny post" in memories[0]
```

- [ ] **Step 2: Run test to verify it fails**
Run: `pytest tests/core/test_memory.py -v`
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**
```python
# backend/core/memory.py
class MemoryManager:
    def __init__(self):
        self.redis_mock = {} # Replace with real Redis later
        
    async def add_short_term(self, agent_id: str, memory: str):
        if agent_id not in self.redis_mock:
            self.redis_mock[agent_id] = []
        self.redis_mock[agent_id].append(memory)
        
    async def get_short_term(self, agent_id: str) -> list[str]:
        return self.redis_mock.get(agent_id, [])
```

- [ ] **Step 4: Run test to verify it passes**
Run: `pytest tests/core/test_memory.py -v`
Expected: PASS

- [ ] **Step 5: Commit**
```bash
git add tests/core/test_memory.py backend/core/memory.py
git commit -m "feat: implement dual-memory manager stubs"
```

### Task 3: Agent Persona & Action Generator

**Files:**
- Create: `backend/core/agent.py`
- Create: `tests/core/test_agent.py`

**Interfaces:**
- Consumes: `MemoryManager` from Task 2, `generate_agent_action` from Task 1.
- Produces: `Agent` class that handles cognitive processing.

- [ ] **Step 1: Write the failing test**
```python
import pytest
from backend.core.agent import Agent

@pytest.mark.asyncio
async def test_agent_process_content():
    agent = Agent(agent_id="agent_1", base_persona="Gen Z on X")
    action = await agent.process_content("Brand just launched a new phone")
    assert "action" in action
```

- [ ] **Step 2: Run test to verify it fails**
Run: `pytest tests/core/test_agent.py -v`
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**
```python
# backend/core/agent.py
from .llm_gateway import generate_agent_action

class Agent:
    def __init__(self, agent_id: str, base_persona: str):
        self.agent_id = agent_id
        self.base_persona = base_persona
        
    async def process_content(self, content: str) -> dict:
        prompt = f"Persona: {self.base_persona}. Content: {content}"
        return await generate_agent_action(prompt)
```

- [ ] **Step 4: Run test to verify it passes**
Run: `pytest tests/core/test_agent.py -v`
Expected: PASS

- [ ] **Step 5: Commit**
```bash
git add tests/core/test_agent.py backend/core/agent.py
git commit -m "feat: implement basic Agent processing logic using DeepSeek Flash"
```
