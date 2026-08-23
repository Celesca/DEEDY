"""
MiroFish TH - Thai Society Simulation Runner (Phase 6B / D11)

เชื่อมต่อ `core/` (Simulation Engine) เข้ากับ `app/` (OASIS Shell)
รับผิดชอบการทำตามสัญญา 3 ข้อของเปลือกแอป:
1. อ่านการตั้งค่าจาก simulation_config.json
2. เขียน actions.jsonl ออกมาทุกรอบ
3. ตอบกลับคำสั่งจาก IPC Server (interview / close_env)
"""
import argparse
import json
import logging
import os
import random
import sys
import time
from datetime import datetime
from pathlib import Path

# Setup paths
_scripts_dir = os.path.dirname(os.path.abspath(__file__))
_backend_dir = os.path.abspath(os.path.join(_scripts_dir, '..'))
sys.path.insert(0, _backend_dir)

from core.environment import PlatformHub
from core.population import load_population
from core.agent import GenerativeAgent, AgentProfile
from core.expression import MediaAccess
from core.llm import get_client
from core.scenario import build as build_scenario, ScenarioError
from core.config import SIM

# OASIS integration
from app.services.simulation_ipc import SimulationIPCClient, SimulationIPCServer, CommandType, CommandStatus
from action_logger import PlatformActionLogger

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("thai_society_runner")

def fallback_population():
    return [
        AgentProfile(
            agent_id="student_bkk", age=22, occupation="นักศึกษา", region="กรุงเทพฯ",
            base_personality="หัวก้าวหน้า ชอบตั้งคำถามกับระบบเก่า",
            media=MediaAccess(social_media=True, line=True, tv=False),
            deference=20, seniority_pressure=15,
        ),
        AgentProfile(
            agent_id="civil_servant_isan", age=47, occupation="ข้าราชการ", region="ภาคอีสาน",
            base_personality="รักสงบ ไม่ชอบมีเรื่อง",
            media=MediaAccess(social_media=False, line=True, tv=True, community=True),
            deference=70, seniority_pressure=65,
        ),
    ]

def load_config(config_path: str) -> dict:
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def parse_events(config: dict) -> dict:
    """Map events by simulated_hour"""
    events_by_hour = {}
    for event in config.get("events", []):
        hour = event.get("scheduled_hour", 0)
        if hour not in events_by_hour:
            events_by_hour[hour] = []
        events_by_hour[hour].append({
            "description": event.get("description", ""),
            "channel": event.get("channel", "โซเชียลมีเดีย"),
            "state_threat_level": event.get("state_threat_level", 0),
            "scenario_key": event.get("scenario_key", "political"),
            "subject": event.get("subject", "เหตุการณ์นี้")
        })
    return events_by_hour


async def run_simulation(args, config, time_config, events_by_hour, total_rounds, minutes_per_round, hub, profiles, action_logger, ipc_server, sim_dir, sim_id):
    logger.info(f"Starting simulation {sim_id} for {total_rounds} rounds")
    running = True
    for round_num in range(1, total_rounds + 1):
        if not running:
            break
            
        simulated_hour = (round_num * minutes_per_round) // 60
        action_logger.log_round_start(round_num, simulated_hour)
        
        # 1. Trigger events or empty string if none (to allow gossip/contagion)
        current_event = ""
        channel_label = "โซเชียลมีเดีย"
        scenario = None
        if simulated_hour in events_by_hour:
            event_obj = events_by_hour[simulated_hour][0]  # Just take first for now
            current_event = event_obj["description"]
            channel_label = event_obj.get("channel", "โซเชียลมีเดีย")
            hub.state_threat = event_obj.get("state_threat_level", 0)
            
            try:
                scenario = build_scenario(
                    key=event_obj.get("scenario_key", "political"),
                    subject=event_obj.get("subject", "เรื่องที่เกิดขึ้น")
                )
            except ScenarioError as e:
                logger.error(f"Error building scenario: {e}")
                scenario = None
                
            logger.info(f"EVENT at hour {simulated_hour}: {current_event}")
            del events_by_hour[simulated_hour]
            
        # 2. Run simulation step via environment
        # Pass empty string if no event, the environment might still trigger agents due to network contagion
        results = await hub.broadcast_event_async(current_event, channel_label, hours_elapsed=minutes_per_round/60.0, simulated_date=args.simulated_date, scenario=scenario)
        
        # 3. Log results (results are from agents who actively reacted)
        actions_count = len(results)
        
        # Phase 6A/5: Log all agents' state (preference falsification gap) even if they didn't act
        for i, agent in enumerate(hub.agents):
            try:
                # Find if they acted
                acted_result = next((r for r in results if r["agent_id"] == agent.profile.agent_id), None)
                
                private_reason = acted_result["private_opinion"]["reason"] if acted_result else ""
                
                if args.baseline and acted_result:
                    action_name = "POST_PUBLIC"
                    post_text = f"[{agent.state.opinion.stance}] {private_reason}"
                else:
                    action_name = acted_result["action_key"] if acted_result else "NO_ACTION"
                    post_text = acted_result.get("public_content", "") if acted_result else ""
                
                action_args = {
                    "private_stance": agent.state.opinion.stance,
                    "private_intensity": agent.state.opinion.intensity,
                    "private_confidence": agent.state.opinion.confidence,
                    "private_text": private_reason,
                    "post_text": post_text,
                    "fear": agent.state.fear,
                    "anger": agent.state.anger,
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
        
        # 4. Check IPC
        cmd = ipc_server.poll_commands()
        if cmd:
            if cmd.command_type == CommandType.CLOSE_ENV:
                logger.info("Received CLOSE_ENV command")
                ipc_server.send_success(cmd.command_id, {})
                running = False
            elif cmd.command_type == CommandType.INTERVIEW:
                # Fetch recent memories for the interview
                agent_id = cmd.args.get("agent_id")
                target_agent = next((a for a in hub.agents if a.profile.agent_id == agent_id), None)
                if target_agent:
                    mems = "\n".join([m.text for m in target_agent.memory.retrieve_scored("ความทรงจำเกี่ยวกับเหตุการณ์", n_results=5)])
                    
                    system_prompt = (
                        f"คุณคือ {target_agent.profile.occupation} อายุ {target_agent.profile.age} ปี จาก {target_agent.profile.region}\n"
                        f"บุคลิกของคุณ: {target_agent.profile.base_personality}\n"
                        f"คุณกำลังถูกผู้สื่อข่าวสัมภาษณ์ ให้ตอบคำถามตามความเป็นจริง (และตามบุคลิกของคุณ) โดยใช้ความทรงจำเหล่านี้เป็นฐานข้อมูล:\n{mems}"
                    )
                    user_prompt = f"นักข่าวถามว่า: {cmd.args.get('prompt', 'คุณคิดยังไงกับสถานการณ์ปัจจุบัน?')}"
                    
                    try:
                        client = get_client()
                        response = client.complete(system_prompt, user_prompt, max_tokens=150)
                        ipc_server.send_success(cmd.command_id, {"response": response})
                    except Exception as e:
                        ipc_server.send_success(cmd.command_id, {"response": f"ไม่สามารถตอบได้ในขณะนี้ ({e})"})
                else:
                    ipc_server.send_success(cmd.command_id, {"response": "Agent not found."})
            else:
                ipc_server.send_success(cmd.command_id, {})
                
    action_logger.log_simulation_end(total_rounds, 0)
    logger.info("Simulation loop completed.")
    
    if not args.no_wait:
        logger.info("Waiting for IPC commands... (Press Ctrl+C to exit)")
        try:
            while running:
                cmd = ipc_server.poll_commands()
                if cmd:
                    if cmd.command_type == CommandType.CLOSE_ENV:
                        ipc_server.send_success(cmd.command_id, {})
                        running = False
                    elif cmd.command_type == CommandType.INTERVIEW:
                        ipc_server.send_success(cmd.command_id, {"response": "Mock interview response (waiting state)"})
                await asyncio.sleep(2)
        except KeyboardInterrupt:
            logger.info("Exiting...")

def main():
    parser = argparse.ArgumentParser(description="Run Thai Society Simulation")
    parser.add_argument("--config", type=str, required=True, help="Path to simulation_config.json")
    parser.add_argument("--no-wait", action="store_true", help="Do not wait for commands after finishing")
    parser.add_argument("--baseline", action="store_true", help="Run in baseline mode (bypass expression filter, pure private opinion)")
    parser.add_argument("--simulated-date", type=str, default=None, help="Temporal cutoff date string (e.g. 'ตุลาคม 2563')")
    args = parser.parse_args()

    config_path = args.config
    sim_dir = os.path.dirname(config_path)
    
    config = load_config(config_path)
    time_config = config.get("time_config", {})
    total_hours = time_config.get("total_simulation_hours", 72)
    minutes_per_round = time_config.get("minutes_per_round", 30)
    total_rounds = int(total_hours * 60 / minutes_per_round)
    
    events_by_hour = parse_events(config)
    
    hub = PlatformHub(seed=SIM.seed)
    
    custom_pop_file = Path(sim_dir) / "custom_population.json"
    pop_file = Path(_backend_dir) / "data" / "population_200.json"
    
    if custom_pop_file.exists():
        profiles = load_population(str(custom_pop_file))
        logger.info(f"Loaded {len(profiles)} custom agents from {custom_pop_file}")
    elif pop_file.exists():
        profiles = load_population(str(pop_file))
        logger.info(f"Loaded {len(profiles)} agents from {pop_file}")
    else:
        profiles = fallback_population()
        logger.warning("Fallback to hardcoded population")
        
    for p in profiles:
        agent = GenerativeAgent(p)
        hub.add_agent(agent)

    action_logger = PlatformActionLogger("thai_society", sim_dir)
    action_logger.log_simulation_start(config)
    
    sim_id = os.path.basename(sim_dir)
    ipc_server = SimulationIPCServer(sim_dir)
    
    import asyncio
    asyncio.run(run_simulation(args, config, time_config, events_by_hour, total_rounds, minutes_per_round, hub, profiles, action_logger, ipc_server, sim_dir, sim_id))

if __name__ == "__main__":
    main()
