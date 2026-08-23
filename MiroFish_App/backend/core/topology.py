import random

class TopologyManager:
    def __init__(self, agents: list):
        self.agents = agents
        # Dictionary mapping agent_id to a list of follower agent_ids
        self.followers_graph = {agent.agent_id: [] for agent in agents}
        
    def seed_fyp(self, post_content: str, count: int = 500) -> list:
        """
        Mimic TikTok FYP/Algorithmic Feed: Randomly push content to 'count' agents 
        who are not necessarily following the brand.
        Returns a list of agent_ids who received the content in their queue.
        """
        sampled_agents = random.sample(self.agents, min(count, len(self.agents)))
        seeded_ids = []
        for agent in sampled_agents:
            # In a real implementation, we would push to the agent's observation queue
            # Here we just return the ids
            seeded_ids.append(agent.agent_id)
        return seeded_ids

    def propagate(self, post_content: str, agent_id: str) -> list:
        """
        Push content to all followers of the given agent.
        """
        followers = self.followers_graph.get(agent_id, [])
        # Push to their queues (omitted for stub)
        return followers
