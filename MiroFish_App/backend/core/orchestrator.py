import asyncio
import os
from .agent import Agent
from .topology import TopologyManager
from .memory import MemoryManager
from .events import event_bus

OASIS_DEFAULT_MAX_ROUNDS = int(os.environ.get("OASIS_DEFAULT_MAX_ROUNDS", 10))

class Orchestrator:
    def __init__(self, agents: list[Agent], topology: TopologyManager):
        self.agents = agents
        self.topology = topology
        # Hybrid ABM: First 50 agents are LLM KOLs, the rest are Math-based "Thai Mung"
        self.llm_agent_ids = {a.agent_id for a in self.agents[:50]}
        
    async def run_simulation(self, initial_post: str, company_description: str, platforms: list[str], objective: str, brand_voice: str, pre_bias: str, campaign_id: str, use_kol: bool = False, io_mode: str = "None"):
        print(f"Starting simulation with {len(self.agents)} agents for {OASIS_DEFAULT_MAX_ROUNDS} rounds.")
        import asyncio
        await asyncio.sleep(2.0) # Wait for WebSockets from frontend to connect before blasting events!
        
        stats = {"likes": 0, "shares": 0, "comments": 0, "sentiment_sum": 0, "comment_texts": []}
        reached_agents = set()
        sentiment_timeline = []
        
        # Broadcast sampled topology for the Network Graph (50 KOLs + 150 Math Agents)
        import random
        sampled_math = random.sample([a.agent_id for a in self.agents if a.agent_id not in self.llm_agent_ids], min(150, len(self.agents)-50))
        sampled_nodes = list(self.llm_agent_ids) + sampled_math
        
        graph_data = {
            "nodes": [{"id": nid, "group": 1 if nid in self.llm_agent_ids else 2} for nid in sampled_nodes],
            "links": []
        }
        for nid in sampled_nodes:
            followers = self.topology.followers_graph.get(nid, [])
            for follower in followers:
                if follower in sampled_nodes:
                    graph_data["links"].append({"source": nid, "target": follower})
                    
        await event_bus.publish(campaign_id, {"event": "topology_init", "data": graph_data})
        
        # Prepare IO Bots if enabled
        io_agent_ids = set()
        if io_mode != "None":
            non_llm = [a.agent_id for a in self.agents if a.agent_id not in self.llm_agent_ids]
            import random
            io_count = int(len(non_llm) * 0.05) # 5% IO bots
            io_agent_ids = set(random.sample(non_llm, io_count))
        
        async def broadcast_action(agent_id, res):
            action = res.get("action", "IGNORE")
            comment = res.get("comment", "")
            sentiment = res.get("sentiment", 0)
            
            if action != "IGNORE":
                if action == "LIKE": stats["likes"] += 1
                elif action == "SHARE": stats["shares"] += 1
                elif action == "COMMENT": stats["comments"] += 1
                
                if isinstance(sentiment, (int, float)):
                    stats["sentiment_sum"] += sentiment
                    
                # Broadcast Agent Action to UI for Network Graph highlighting
                await event_bus.publish(campaign_id, {"event": "graph_highlight", "agent_id": agent_id, "action": action, "sentiment": sentiment})
                    
                # Decide if we show this in Matrix Feed
                show_in_feed = False
                if agent_id in self.llm_agent_ids:
                    show_in_feed = True
                else:
                    # 10% chance to show Math agent to flood the feed with numbers
                    import random
                    if random.random() < 0.10:
                        show_in_feed = True
                        if action == "LIKE": comment = random.choice(["กดใจให้รัวๆ", "ชอบมากแม่", "เลิฟเลย", "ดือออ", "เริ่ด"])
                        elif action == "SHARE": comment = random.choice(["แชร์วนไป", "ต้องแชร์แล้วป่ะ", "กระจายข่าวหน่อย", "ปังมากแม่ ขอแชร์"])
                        else:
                            if sentiment > 0: comment = random.choice(["ดีงามพระรามแปด", "สุดปัง", "ไม่ผิดหวังเลย", "แบรนด์นี้ทำดีตลอด"])
                            elif sentiment < 0: comment = random.choice(["อิหยังวะ", "หิวแสงเว่อ", "พักก่อน", "พังมาก", "บ้งไม่ไหว"])
                            else: comment = random.choice(["เออ ก็ได้อยู่", "อืมมม", "ตามนั้น", "ก็โอเค"])
                
                if show_in_feed:
                    # Pick a random platform for this action
                    import random
                    plat = random.choice(platforms) if platforms else "Web"
                    
                    emoji = {"LIKE": "❤️", "SHARE": "🔁", "COMMENT": "💬"}.get(action, "👀")
                    msg = f"[{plat}] Agent {agent_id} {action.lower()}d the post. {emoji}"
                    if comment:
                        msg += f" '{comment}'"
                        if agent_id in self.llm_agent_ids:
                            stats["comment_texts"].append(f"Agent {agent_id}: {comment}")
                        
                    await event_bus.publish(campaign_id, {"event": "agent_action", "content": msg})

        # Loop 1: FYP Seeding (Algorithm injection)
        print("--- Tick 1: FYP Seeding ---")
        await event_bus.publish(campaign_id, {"event": "tick_start", "tick": 1})
        if use_kol:
            seeded_ids = list(self.llm_agent_ids)
            await event_bus.publish(campaign_id, {"event": "agent_action", "content": "⚡ [KOL INJECTION] Bypassing FYP! Seeding directly to Top Influencers!"})
        else:
            seeded_ids = self.topology.seed_fyp(initial_post, count=max(10, int(len(self.agents) * 0.05)))
        
        wave_agents = [a for a in self.agents if a.agent_id in seeded_ids]
        reached_agents.update(seeded_ids)
        
        tasks = []
        for agent in wave_agents:
            if agent.agent_id in io_agent_ids:
                if io_mode == "Positive IO":
                    async def io_task(): return {"action": "SHARE", "sentiment": 1, "comment": "ปังมาก สนับสนุนค่ะ!"}
                else:
                    async def io_task(): return {"action": "COMMENT", "sentiment": -1, "comment": "แบนแบรนด์นี้ ทุเรศมาก!"}
                tasks.append(io_task())
            elif agent.agent_id in self.llm_agent_ids:
                tasks.append(agent.process_content(initial_post, company_description, platforms, objective, brand_voice, pre_bias))
            else:
                tasks.append(agent.process_content_math(0.0))
                
        results = await asyncio.gather(*tasks)
        
        sharers = []
        for agent, res in zip(wave_agents, results):
            await broadcast_action(agent.agent_id, res)
            if res.get("action") == "SHARE":
                sharers.append(agent.agent_id)
                
        current_trend = stats["sentiment_sum"] / max(1, stats["likes"] + stats["shares"] + stats["comments"])
        sentiment_timeline.append(current_trend)
        
        print(f"Tick 1 complete. {len(results)} agents reacted.")
        await asyncio.sleep(1.5) # Pacing
        
        # Subsequent Loops (Tick 2 to Max Rounds)
        for tick in range(2, OASIS_DEFAULT_MAX_ROUNDS + 1):
            if not sharers:
                print("Simulation faded out (no one shared).")
                await event_bus.publish(campaign_id, {"event": "agent_action", "content": "💀 [FADED OUT] The post died because no one shared it further."})
                break
                
            print(f"--- Tick {tick} ---")
            await event_bus.publish(campaign_id, {"event": "tick_start", "tick": tick})
            next_wave_ids = set()
            for sid in sharers:
                next_wave_ids.update(self.topology.propagate(initial_post, sid))
                
            # --- FYP Recommendation Algorithm ---
            # If engagement rate from previous wave is high (>15%), push to random outside network
            if len(wave_agents) > 0:
                eng_rate = sum(1 for r in results if r.get("action") != "IGNORE") / len(wave_agents)
                if eng_rate > 0.15:
                    unreached = [a.agent_id for a in self.agents if a.agent_id not in reached_agents]
                    if unreached:
                        import random
                        push_count = min(len(unreached), int(len(self.agents) * 0.15)) # 15% random push
                        fyp_push = random.sample(unreached, push_count)
                        next_wave_ids.update(fyp_push)
                        await event_bus.publish(campaign_id, {"event": "agent_action", "content": "🔥 [FYP ALGORITHM] Engagement Spike Detected! Pushing post to new audiences!"})
            
            # Filter out already reached agents
            next_wave_ids = next_wave_ids - reached_agents
            if not next_wave_ids:
                break
                
            reached_agents.update(next_wave_ids)
            wave_agents = [a for a in self.agents if a.agent_id in next_wave_ids]
            
            # Calculate current trend to feed into Math Agents
            total_actions = max(1, stats["likes"] + stats["shares"] + stats["comments"])
            current_trend = stats["sentiment_sum"] / total_actions
            
            tasks = []
            for agent in wave_agents:
                if agent.agent_id in io_agent_ids:
                    if io_mode == "Positive IO":
                        async def io_task(): return {"action": "SHARE", "sentiment": 1, "comment": "ปังมาก สนับสนุนค่ะ!"}
                    else:
                        async def io_task(): return {"action": "COMMENT", "sentiment": -1, "comment": "แบนแบรนด์นี้ ทุเรศมาก!"}
                    tasks.append(io_task())
                elif agent.agent_id in self.llm_agent_ids:
                    tasks.append(agent.process_content(initial_post, company_description, platforms, objective, brand_voice, pre_bias))
                else:
                    tasks.append(agent.process_content_math(current_trend))
                    
            results = await asyncio.gather(*tasks)
            
            sharers = []
            for agent, res in zip(wave_agents, results):
                await broadcast_action(agent.agent_id, res)
                if res.get("action") == "SHARE":
                    sharers.append(agent.agent_id)
            
            current_trend = stats["sentiment_sum"] / max(1, stats["likes"] + stats["shares"] + stats["comments"])
            sentiment_timeline.append(current_trend)
            
            # Send stats update to Matrix Feed
            await event_bus.publish(campaign_id, {"event": "stats_update", "total_agents": len(self.agents), "reached": len(reached_agents), "engaged": stats["likes"] + stats["shares"] + stats["comments"]})
            await asyncio.sleep(1.5) # Pacing
            
        print("Simulation complete. Triggering global reflections...")
        
        # Calculate final metrics
        total_actions = max(1, stats["likes"] + stats["shares"] + stats["comments"])
        viral_score = min(100, int((stats["shares"] * 3 + stats["likes"] * 1 + stats["comments"] * 2) / max(1, len(self.agents)) * 100))
        avg_sentiment = stats["sentiment_sum"] / total_actions
        sentiment_shift = f"{'+' if avg_sentiment > 0 else ''}{avg_sentiment * 100:.1f}%"
        
        metrics_summary = (
            f"Campaign ID: {campaign_id}\n"
            f"Total Reach (Agents): {len(self.agents)}\n"
            f"Likes: {stats['likes']}, Shares: {stats['shares']}, Comments: {stats['comments']}\n"
            f"Average Sentiment Score: {avg_sentiment:.2f}\n"
            f"Sample Comments:\n" + "\n".join(stats["comment_texts"][:20]) # Limit to 20 comments
        )
        
        from .events import campaign_reports
        from .llm_gateway import generate_reflection
        
        print("Generating AI Insights...")
        insights = await generate_reflection(metrics_summary)
        
        print("Running Long-term Memory Reflection for KOLs...")
        reflection_tasks = [a.memory.reflect_to_long_term(a.agent_id) for a in self.agents if a.agent_id in self.llm_agent_ids]
        await asyncio.gather(*reflection_tasks)
        print("KOL Reflections stored in ChromaDB.")
        
        campaign_reports[campaign_id] = {
            "status": "complete",
            "campaign_id": campaign_id,
            "viral_score": viral_score,
            "sentiment_shift": sentiment_shift,
            "analyst_summary": insights,
            "sentiment_timeline": sentiment_timeline,
            "engagement_mix": {"likes": stats["likes"], "shares": stats["shares"], "comments": stats["comments"]}
        }
        print("AI Insights generated and saved.")
