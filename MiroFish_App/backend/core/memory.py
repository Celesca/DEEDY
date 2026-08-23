from .db import get_memory_collection
import uuid

class MemoryManager:
    def __init__(self):
        # Redis stub for Short-term memory
        self.redis_mock = {}
        # Persistent ChromaDB for Long-term memory
        self.chroma_collection = get_memory_collection()
        
    async def add_short_term(self, agent_id: str, memory: str):
        if agent_id not in self.redis_mock:
            self.redis_mock[agent_id] = []
        self.redis_mock[agent_id].append(memory)
        
    async def get_short_term(self, agent_id: str) -> list[str]:
        return self.redis_mock.get(agent_id, [])

    async def reflect_to_long_term(self, agent_id: str):
        # This will call the Gemini-3.6-flash analyst/reflection model
        # to summarize the short_term memory and store as vector in ChromaDB.
        short_term_data = self.redis_mock.get(agent_id, [])
        if short_term_data:
            summary = f"Reflected: {', '.join(short_term_data)}"
            # Store in ChromaDB
            self.chroma_collection.add(
                documents=[summary],
                metadatas=[{"agent_id": agent_id}],
                ids=[str(uuid.uuid4())]
            )
            # Clear short term after reflection
            self.redis_mock[agent_id] = []
            
    async def search_long_term(self, agent_id: str, query: str, limit: int = 3) -> list[str]:
        results = self.chroma_collection.query(
            query_texts=[query],
            n_results=limit,
            where={"agent_id": agent_id}
        )
        return results["documents"][0] if results["documents"] else []
