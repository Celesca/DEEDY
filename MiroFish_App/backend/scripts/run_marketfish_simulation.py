"""
MarketFish - Social Media Marketing Simulation Runner
Implements Hybrid ABM (5% LLM KOLs, 95% Math Agents)
"""
import argparse
import json
import logging
import os
import random
import sys
from datetime import datetime
from pathlib import Path

# Setup paths
_scripts_dir = os.path.dirname(os.path.abspath(__file__))
_backend_dir = os.path.abspath(os.path.join(_scripts_dir, '..'))
sys.path.insert(0, _backend_dir)

from core.environment import PlatformHub
from core.population import load_population
from core.agent import GenerativeAgent, MathAgent, AgentProfile
from core.config import SIM

# OASIS integration
from app.services.simulation_ipc import SimulationIPCServer, CommandType
from action_logger import PlatformActionLogger

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("marketfish_runner")

def load_config(config_path: str) -> dict:
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def parse_events(config: dict) -> dict:
    events_by_hour = {}
    for event in config.get("events", []):
        hour = event.get("scheduled_hour", 0)
        if hour not in events_by_hour:
            events_by_hour[hour] = []
        events_by_hour[hour].append({
            "description": event.get("description", ""),
            "channel": event.get("channel", "โซเชียลมีเดีย"),
            "state_threat_level": event.get("state_threat_level", 0)
        })
    return events_by_hour


async def run_simulation(args, config, time_config, events_by_hour, total_rounds, minutes_per_round, hub, profiles, action_logger, ipc_server, sim_dir, sim_id):
    logger.info(f"Starting MarketFish simulation {sim_id} for {total_rounds} rounds")
    running = True
    
    bot_percentage = config.get("bot_injection_percentage", 0.05) # IO module config
    
    for round_num in range(1, total_rounds + 1):
        if not running:
            break
            
        simulated_hour = (round_num * minutes_per_round) // 60
        action_logger.log_round_start(round_num, simulated_hour)
        
        current_event = ""
        channel_label = "โซเชียลมีเดีย"
        if simulated_hour in events_by_hour:
            event_obj = events_by_hour[simulated_hour][0]
            current_event = event_obj["description"]
            channel_label = event_obj.get("channel", "โซเชียลมีเดีย")
            hub.state_threat = event_obj.get("state_threat_level", 0)
            logger.info(f"EVENT at hour {simulated_hour}: {current_event}")
            del events_by_hour[simulated_hour]
            
        # Trigger FYP Seeding + Broadcast
        results = await hub.broadcast_event_async(current_event, channel_label, hours_elapsed=minutes_per_round/60.0, simulated_date=args.simulated_date)
        
        actions_count = len(results)
        
        for i, agent in enumerate(hub.agents):
            try:
                acted_result = next((r for r in results if r["agent_id"] == agent.profile.agent_id), None)
                private_reason = acted_result["private_opinion"]["reason"] if acted_result else ""
                
                action_name = acted_result["action_key"] if acted_result else "NO_ACTION"
                post_text = acted_result.get("public_content", "") if acted_result else ""
                
                # Check for Astroturfing (Bot Injection) overriding sentiment
                if bot_percentage > 0 and not getattr(agent, 'is_llm', False) and action_name == "NO_ACTION":
                    if random.random() < bot_percentage:
                        if random.random() < 0.5:
                            action_name = "BOT_ATTACK"
                            post_text = "แบนแบรนด์นี้! ทุเรศมาก ไม่ไหวแล้ว!"
                            agent.state.opinion.stance = "opposing"
                        else:
                            action_name = "BOT_SUPPORT"
                            post_text = "ของเขาดีจริงๆ นะคะ คอนเฟิร์มเลยว่าเริ่ดมาก!"
                            agent.state.opinion.stance = "supporting"
                        agent.state.opinion.intensity = 100
                
                action_args = {
                    "private_stance": agent.state.opinion.stance,
                    "private_intensity": agent.state.opinion.intensity,
                    "private_text": private_reason,
                    "post_text": post_text,
                    "fear": agent.state.fear,
                    "anger": agent.state.anger,
                    "is_llm": getattr(agent, 'is_llm', False)
                }
                
                try:
                    num_id = int(agent.profile.agent_id.replace("agent_", ""))
                except ValueError:
                    num_id = i + 1
                    
                action_logger.log_action(
                    round_num=round_num,
                    agent_id=num_id,
                    agent_name=agent.profile.agent_id,
                    action_type=action_name,
                    action_args=action_args,
                    success=True
                )
            except Exception as e:
                logger.error(f"Error logging agent {agent.profile.agent_id}: {e}")
                
        action_logger.log_round_end(round_num, actions_count)
        
        cmd = ipc_server.poll_commands()
        if cmd:
            if cmd.command_type == CommandType.CLOSE_ENV:
                ipc_server.send_success(cmd.command_id, {})
                running = False
            else:
                ipc_server.send_success(cmd.command_id, {})
                
    action_logger.log_simulation_end(total_rounds, 0)
    logger.info("MarketFish simulation loop completed.")

def main():
    parser = argparse.ArgumentParser(description="Run MarketFish Simulation (Hybrid ABM)")
    parser.add_argument("--config", type=str, required=True, help="Path to simulation_config.json")
    parser.add_argument("--simulated-date", type=str, default=None)
    args = parser.parse_args()

    config_path = args.config
    sim_dir = os.path.dirname(config_path)
    
    config = load_config(config_path)
    time_config = config.get("time_config", {})
    total_hours = time_config.get("total_simulation_hours", 24)
    minutes_per_round = time_config.get("minutes_per_round", 60)
    total_rounds = int(total_hours * 60 / minutes_per_round)
    
    events_by_hour = parse_events(config)
    
    hub = PlatformHub(seed=SIM.seed)
    
    pop_file = Path(_backend_dir) / "data" / "population_200.json"
    if pop_file.exists():
        profiles = load_population(str(pop_file))
        logger.info(f"Loaded {len(profiles)} agents from {pop_file}")
    else:
        logger.error("Population file missing")
        return
        
    # Hybrid ABM partitioning: 5% KOLs (Generative), 95% Public (Math)
    kol_count = int(len(profiles) * 0.05)
    
    for i, p in enumerate(profiles):
        if i < kol_count:
            p.influence = 5.0 # High influence KOL
            agent = GenerativeAgent(p)
        else:
            p.influence = 0.1 # General public
            agent = MathAgent(p)
        hub.add_agent(agent)

    logger.info(f"Initialized Hybrid ABM: {kol_count} KOLs (LLM) and {len(profiles) - kol_count} Public (Math)")

    action_logger = PlatformActionLogger("marketfish", sim_dir)
    action_logger.log_simulation_start(config)
    
    sim_id = os.path.basename(sim_dir)
    ipc_server = SimulationIPCServer(sim_dir)
    
    import asyncio
    asyncio.run(run_simulation(args, config, time_config, events_by_hour, total_rounds, minutes_per_round, hub, profiles, action_logger, ipc_server, sim_dir, sim_id))

if __name__ == "__main__":
    main()
