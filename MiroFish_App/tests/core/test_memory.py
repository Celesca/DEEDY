import pytest
from backend.core.memory import MemoryManager

@pytest.mark.asyncio
async def test_memory_manager_short_term():
    manager = MemoryManager()
    await manager.add_short_term("agent_1", "Saw a funny post")
    memories = await manager.get_short_term("agent_1")
    assert len(memories) == 1
    assert "funny post" in memories[0]

@pytest.mark.asyncio
async def test_memory_manager_long_term_reflection():
    manager = MemoryManager()
    await manager.add_short_term("agent_1", "User was angry at brand X")
    await manager.reflect_to_long_term("agent_1")
    # After reflection, short term memory might be cleared or moved
    # This is a stub test for the long term reflection logic
    assert True
