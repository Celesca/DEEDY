from fastapi import APIRouter, WebSocket, WebSocketDisconnect, BackgroundTasks
from .models import CampaignInput
from ..core.orchestrator import Orchestrator
from ..core.topology import TopologyManager
from ..core.agent import Agent
import uuid
import asyncio
from ..core.events import event_bus

router = APIRouter()

# In-memory store for active websockets (just for stub)
active_connections: dict[str, WebSocket] = {}

@router.post("/simulate")
async def start_simulation(campaign: CampaignInput, background_tasks: BackgroundTasks):
    campaign_id = str(uuid.uuid4())
    
    # Initialize the Orchestrator with some dummy agents
    # In a real scenario, we spawn agent instances from a DB distribution
    # We now pass the full agent count. Orchestrator handles Hybrid ABM (LLM + Math)
    agents = []
    for i in range(campaign.agent_count):
        agents.append(Agent(agent_id=f"agent_{i}", base_persona="Thai Gen Z", is_llm=(i < 50)))
        
    topology = TopologyManager(agents)
    orchestrator = Orchestrator(agents, topology)
    
    # Run the heavy simulation in the background so API responds immediately
    background_tasks.add_task(
        orchestrator.run_simulation, 
        initial_post=campaign.post_content,
        company_description=campaign.company_description,
        platforms=campaign.platforms,
        objective=campaign.objective,
        brand_voice=campaign.brand_voice,
        pre_bias=campaign.pre_bias,
        campaign_id=campaign_id,
        use_kol=campaign.use_kol,
        io_mode=campaign.io_mode
    )
    
    return {"campaign_id": campaign_id, "status": "Simulation started in background"}

from ..core.events import event_bus, campaign_reports

@router.get("/report/{campaign_id}")
async def get_report(campaign_id: str):
    if campaign_id in campaign_reports:
        return campaign_reports[campaign_id]
    return {"status": "processing"}

import random

@router.websocket("/stream/{campaign_id}")
async def websocket_endpoint(websocket: WebSocket, campaign_id: str):
    await websocket.accept()
    
    queue = event_bus.subscribe(campaign_id)
    
    try:
        # Loop to send real-time simulated actions to the Matrix Feed UI
        while True:
            # Await event from Orchestrator via EventBus
            event = await queue.get()
            await websocket.send_json(event)
    except WebSocketDisconnect:
        event_bus.unsubscribe(campaign_id, queue)
        print(f"Client disconnected from campaign {campaign_id}")
