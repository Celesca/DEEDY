import pytest
from backend.core.agent import Agent

@pytest.mark.asyncio
async def test_agent_process_content():
    agent = Agent(agent_id="agent_1", base_persona="Gen Z on X")
    action = await agent.process_content("Brand just launched a new phone")
    assert "action" in action
