const fs = require('fs');
const path = require('path');

function multiplyAgents(multiplier = 10) {
    const dataPath = path.join(__dirname, 'data', 'population_200.json');
    const data = JSON.parse(fs.readFileSync(dataPath, 'utf-8'));
    
    const originalAgents = data.agents;
    const newAgents = [];
    
    for (let i = 0; i < multiplier; i++) {
        for (const agent of originalAgents) {
            const newAgent = { ...agent };
            newAgent.agent_id = `${agent.agent_id}_batch${i + 1}`;
            newAgents.push(newAgent);
        }
    }
    
    data.agents = newAgents;
    fs.writeFileSync(dataPath, JSON.stringify(data, null, 2), 'utf-8');
    console.log(`Successfully multiplied agents! New population: ${newAgents.length}`);
}

multiplyAgents(10);
