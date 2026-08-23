import chromadb
from chromadb.config import Settings
import os

# Initialize persistent ChromaDB client
db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "chroma_data")
chroma_client = chromadb.PersistentClient(path=db_path)

# Get or create the agent memory collection
agent_memory_collection = chroma_client.get_or_create_collection(name="agent_memories")

def get_memory_collection():
    return agent_memory_collection
