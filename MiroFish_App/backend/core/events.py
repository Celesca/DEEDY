import asyncio
from collections import defaultdict

class EventBus:
    def __init__(self):
        # Maps campaign_id to a list of subscriber queues
        self.queues: dict[str, list[asyncio.Queue]] = defaultdict(list)
        
    def subscribe(self, campaign_id: str) -> asyncio.Queue:
        queue = asyncio.Queue()
        self.queues[campaign_id].append(queue)
        return queue
        
    def unsubscribe(self, campaign_id: str, queue: asyncio.Queue):
        if campaign_id in self.queues and queue in self.queues[campaign_id]:
            self.queues[campaign_id].remove(queue)
            
    async def publish(self, campaign_id: str, message: dict):
        for queue in self.queues.get(campaign_id, []):
            await queue.put(message)

# Global singleton event bus
event_bus = EventBus()

# Global in-memory storage for final analyst reports
campaign_reports = {}
