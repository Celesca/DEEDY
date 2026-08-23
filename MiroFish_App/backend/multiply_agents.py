import json
from pathlib import Path

def multiply_agents(multiplier: int = 10):
    data_path = Path(__file__).parent / "data" / "population_200.json"
    
    with open(data_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    original_agents = data["agents"]
    new_agents = []
    
    for i in range(multiplier):
        for agent in original_agents:
            new_agent = agent.copy()
            # Make the ID unique by appending the batch number
            new_agent["agent_id"] = f"{agent['agent_id']}_batch{i+1}"
            new_agents.append(new_agent)
            
    data["agents"] = new_agents
    
    with open(data_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        
    print(f"Successfully multiplied agents! New population: {len(new_agents)}")

if __name__ == "__main__":
    multiply_agents(10) # 20 * 10 = 200 agents
