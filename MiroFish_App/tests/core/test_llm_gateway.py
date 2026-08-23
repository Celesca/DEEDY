import pytest
from backend.core.llm_gateway import generate_agent_action, generate_reflection

@pytest.mark.asyncio
async def test_generate_agent_action_returns_dict():
    # Mock the underlying API call
    result = await generate_agent_action("System: You are an agent...", model="qwen/qwen3.7-flash")
    assert isinstance(result, dict)
    assert "action" in result

@pytest.mark.asyncio
async def test_generate_reflection_uses_large_model():
    result = await generate_reflection("Summarize this: ...", model="google/gemini-3.6-flash")
    assert isinstance(result, str)
