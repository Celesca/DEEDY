"""
สภาพแวดล้อมของการจำลอง — ปล่อยเหตุการณ์ กระตุ้น agent และแพร่อารมณ์

⚠️ สถานะ: ยังเป็นโครง Phase 0/1
   Phase 4 จะเปลี่ยนเป็น **เครือข่ายหลายชั้น** (โซเชียล / กลุ่มไลน์ / ครอบครัว-ที่ทำงาน /
   ชุมชน) พร้อมช่องทางข่าวสารที่เข้าถึงคนต่างกลุ่มไม่เท่ากัน
   ตอนนี้ยังเป็น fully-connected ซึ่งแปลว่ายังไม่มี echo chamber และคนที่ไม่เล่นโซเชียล
   ยังรู้ข่าวพร้อมคนอื่น — ห้ามเอาผลไปสรุปเรื่องการแพร่กระจายก่อนทำ Phase 4
"""
import asyncio
import logging
import random
from typing import Any, Dict, List, Optional

from .agent import GenerativeAgent
from .config import SIM
from .network import MultiLayerNetwork
from .scenario import Scenario

logger = logging.getLogger("mirofish.core.env")


class PlatformHub:
    """ศูนย์กลางการจำลอง"""

    def __init__(self, seed: Optional[int] = None, activation_rate: Optional[float] = None):
        self.agents: List[GenerativeAgent] = []
        self.event_history: List[str] = []
        self.round_num = 0
        self.global_anger = 0
        self.state_threat = 0
        self.rng = random.Random(seed if seed is not None else SIM.seed)
        self.activation_rate = (
            activation_rate if activation_rate is not None else SIM.activation_rate
        )
        self.network: Optional[MultiLayerNetwork] = None
        self.last_majority_stance: Optional[str] = None

    def add_agent(self, agent: GenerativeAgent) -> None:
        self.agents.append(agent)
        # Network needs to be rebuilt if agents are added dynamically, but in our case they are added at start.
        # We will build it on the first round if not built.

    def _ensure_network(self):
        if self.network is None and self.agents:
            self.network = MultiLayerNetwork(self.agents, self.rng)

    # ── การแพร่อารมณ์ ──

    def calculate_network_contagion(self) -> None:
        """คำนวณอารมณ์รวมแล้วสาดกลับไปทุกคนผ่านเครือข่ายหลายชั้น (Phase 5)"""
        if not self.agents:
            return
            
        self._ensure_network()
        
        # Calculate contagion specific to each agent based on their network neighbors
        contagion_map = self.network.calculate_contagion()
        
        for agent in self.agents:
            # Apply their specific network contagion instead of global average
            neighbor_anger = contagion_map.get(agent.profile.agent_id, 0.0)
            agent.apply_environmental_contagion(int(neighbor_anger), self.state_threat)

    # ── การกระตุ้น ──

    def select_active(self, channel_label: Optional[str] = None, event_text: str = "") -> List[GenerativeAgent]:
        """เลือกคนที่น่าจะมองเห็นโพสต์ตาม Algorithmic Feed Probability"""
        active = []
        for agent in self.agents:
            if channel_label:
                # Phase 5.4: News propagates based on media access
                if channel_label == "โซเชียลมีเดีย" and not agent.profile.media.social_media:
                    continue
                if channel_label == "LINE" and not agent.profile.media.line:
                    continue
                if channel_label == "ชุมชน" and not agent.profile.media.community:
                    continue
                if channel_label == "โทรทัศน์" and not agent.profile.media.tv:
                    continue

            # 1. Base Chance
            prob = self.activation_rate
            
            # 2. KOL Boost (If the agent themselves is a KOL, they are highly active)
            if agent.profile.is_kol:
                prob += 0.30
                
            # 3. Echo Chamber Boost (Matching sentiment)
            # Simplification: If they already have a strong stance, they seek out news
            if agent.state.opinion.intensity > 50:
                prob += 0.20
                
            # 4. Engagement Boost (Rage bait on X)
            if channel_label == "X" or channel_label == "โซเชียลมีเดีย":
                # High anger = algorithm feeds them more rage bait
                if agent.state.anger > 60:
                    prob += 0.30
            elif channel_label == "Pantip":
                # Pantip favors lower anger, higher reasoning
                if agent.state.anger < 40:
                    prob += 0.20

            if self.rng.random() < min(1.0, prob):
                active.append(agent)
        return active

    # ── รอบการจำลอง ──

    async def broadcast_event_async(
        self,
        event: str,
        channel_label: str = "โซเชียลมีเดีย",
        hours_elapsed: float = 1.0,
        simulated_date: Optional[str] = None,
        scenario: Optional[Scenario] = None,
    ) -> List[Dict[str, Any]]:
        self.round_num += 1
        if event:
            self.event_history.append(event)

        # เดินนาฬิกาโลกจำลองให้ทุกคน เพื่อให้ความจำเก่าเลือนลงตามเวลา
        for agent in self.agents:
            agent.advance_clock(hours_elapsed)

        self.calculate_network_contagion()

        # โหลดโมเดล embedding + เปิด chroma client ให้เสร็จก่อน
        # ไม่งั้น 30 เธรดจะแย่งกันโหลดพร้อมกัน (มี lock กันพังแล้ว แต่ทำแบบนี้
        # เร็วกว่าและทำให้ error ที่เกิดตอนโหลดโผล่ตรงนี้ ไม่ใช่กระจายทุก agent)
        if self.agents:
            self.agents[0].memory.warmup(self.agents[0].memory.persist_dir)

        active = self.select_active(channel_label=channel_label, event_text=event)
        logger.info(
            "รอบ %d: กระตุ้น %d/%d agent (%.0f%%) ทาง %s",
            self.round_num, len(active), len(self.agents),
            100 * len(active) / max(1, len(self.agents)), channel_label
        )

        semaphore = asyncio.Semaphore(30)

        async def run(agent: GenerativeAgent) -> Optional[Dict[str, Any]]:
            async with semaphore:
                try:
                    return await asyncio.to_thread(agent.react, event, channel_label, simulated_date, scenario, self.last_majority_stance)
                except Exception as e:  # noqa: BLE001
                    logger.error("[%s] react ล้มเหลว: %s", agent.profile.agent_id, e)
                    return None

        results = await asyncio.gather(*(run(a) for a in active))
        out = [r for r in results if r]
        
        # --- Calculate Falsification Gap ---
        total_active = len(out) if out else 1
        true_counts = {"supportive": 0, "opposing": 0, "neutral": 0}
        expr_counts = {"supportive": 0, "opposing": 0, "neutral": 0}
        
        for r in out:
            true_stance = r["private_opinion"].get("stance", "neutral")
            true_counts[true_stance] = true_counts.get(true_stance, 0) + 1
            
            # An action is public if exposure > 0 (e.g. POST_PUBLIC, DEFEND_PUBLIC)
            # If they are silent or talk privately, they didn't express it publicly
            if r.get("exposure", 0) > 0 and r.get("action_key") != "evasive_post":
                expr_counts[true_stance] = expr_counts.get(true_stance, 0) + 1
            else:
                expr_counts["neutral"] = expr_counts.get("neutral", 0) + 1

        # Determine majority stance for the next round
        highest_stance = max(expr_counts, key=expr_counts.get)
        if expr_counts[highest_stance] > total_active * 0.4:
            self.last_majority_stance = highest_stance
        else:
            self.last_majority_stance = None

        self.latest_falsification = [
            {
                "topic": "SUPPORTIVE",
                "true": round(true_counts["supportive"] / total_active * 100),
                "expr": round(expr_counts["supportive"] / total_active * 100)
            },
            {
                "topic": "OPPOSING",
                "true": round(true_counts["opposing"] / total_active * 100),
                "expr": round(expr_counts["opposing"] / total_active * 100)
            },
            {
                "topic": "NEUTRAL / SILENT",
                "true": round(true_counts["neutral"] / total_active * 100),
                "expr": round(expr_counts["neutral"] / total_active * 100)
            }
        ]
        
        # --- Generate Mock Clusters for now based on intensity ---
        import random
        self.latest_clusters = [
            {"id": "c1", "x": random.randint(20, 40), "y": random.randint(20, 40), "color": "var(--accent-cyan)", "size": 15},
            {"id": "c2", "x": random.randint(60, 80), "y": random.randint(40, 60), "color": "var(--accent-magenta)", "size": 20},
            {"id": "c3", "x": random.randint(40, 60), "y": random.randint(70, 90), "color": "var(--text-primary)", "size": 10},
        ]
        
        # --- Calculate Fear Index Heatmap ---
        fear_by_region = {}
        count_by_region = {}
        for a in self.agents:
            reg = a.profile.region
            fear_by_region[reg] = fear_by_region.get(reg, 0) + a.state.fear
            count_by_region[reg] = count_by_region.get(reg, 0) + 1
            
        self.latest_fear_index = [
            {"region": r, "fear": round(fear_by_region[r] / max(1, count_by_region[r]))}
            for r in fear_by_region
        ]
        
        for r in out:
            r["round"] = self.round_num
        return out

    # ── ตัวชี้วัดระดับสังคม (ดู Phase 5) ──

    def snapshot(self) -> Dict[str, Any]:
        """สรุปสถานะของ "สังคม" ทั้งหมด รวมคนที่ไม่เคยพูดอะไรเลย

        นี่คือเหตุผลที่ต้องเก็บ private_opinion ของทุกคนทุกรอบ ไม่ใช่แค่คนที่พูด
        """
        if not self.agents:
            return {}

        stances: Dict[str, int] = {}
        for agent in self.agents:
            s = agent.state.opinion.stance
            stances[s] = stances.get(s, 0) + 1

        total = len(self.agents)
        return {
            "round": self.round_num,
            "population": total,
            "private_stance": {k: round(v / total, 4) for k, v in stances.items()},
            "avg_anger": round(sum(a.state.anger for a in self.agents) / total, 1),
            "avg_fear": round(sum(a.state.fear for a in self.agents) / total, 1),
            "falsification_gaps": getattr(self, "latest_falsification", []),
            "clusters": getattr(self, "latest_clusters", []),
            "fear_index": getattr(self, "latest_fear_index", []),
        }
        if not self.agents:
            return {}

        stances: Dict[str, int] = {}
        for agent in self.agents:
            s = agent.state.opinion.stance
            stances[s] = stances.get(s, 0) + 1

        total = len(self.agents)
        return {
            "round": self.round_num,
            "population": total,
            "private_stance": {k: round(v / total, 4) for k, v in stances.items()},
            "avg_anger": round(sum(a.state.anger for a in self.agents) / total, 1),
            "avg_fear": round(sum(a.state.fear for a in self.agents) / total, 1),
        }
