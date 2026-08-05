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

    def add_agent(self, agent: GenerativeAgent) -> None:
        self.agents.append(agent)

    # ── การแพร่อารมณ์ ──

    def calculate_network_contagion(self) -> None:
        """คำนวณอารมณ์รวมแล้วสาดกลับไปทุกคน

        Phase 4: ต้องเปลี่ยนเป็นคิดจากเพื่อนบ้านในกราฟแต่ละชั้น
        ไม่ใช่ค่าเฉลี่ยทั้งระบบแบบนี้ ซึ่งทำให้ทุกคนกลายเป็นเหมือนกันหมด
        """
        if not self.agents:
            return
        self.global_anger = int(sum(a.state.anger for a in self.agents) / len(self.agents))
        for agent in self.agents:
            agent.apply_environmental_contagion(self.global_anger, self.state_threat)

    # ── การกระตุ้น ──

    def select_active(self) -> List[GenerativeAgent]:
        """เลือกเฉพาะคนที่ "สนใจ" เรื่องนี้ในรอบนี้

        คนส่วนใหญ่ไม่ตอบสนองต่อทุกเรื่อง — เป็นทั้งความสมจริงและการประหยัดต้นทุน
        (ลด activation จาก 100% เหลือ 15% ประหยัดค่า LLM ราว 6.6 เท่า)
        คนที่โกรธหรือมีความเห็นเข้มข้นอยู่แล้ว มีโอกาสถูกกระตุ้นสูงกว่า
        """
        active = []
        for agent in self.agents:
            base = self.activation_rate
            boost = (agent.state.anger + agent.state.opinion.intensity) / 200 * 0.5
            if self.rng.random() < min(1.0, base + boost):
                active.append(agent)
        return active

    # ── รอบการจำลอง ──

    async def broadcast_event_async(
        self,
        event: str,
        channel_label: str = "โซเชียลมีเดีย",
        hours_elapsed: float = 1.0,
    ) -> List[Dict[str, Any]]:
        self.round_num += 1
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

        active = self.select_active()
        logger.info(
            "รอบ %d: กระตุ้น %d/%d agent (%.0f%%)",
            self.round_num, len(active), len(self.agents),
            100 * len(active) / max(1, len(self.agents)),
        )

        semaphore = asyncio.Semaphore(30)

        async def run(agent: GenerativeAgent) -> Optional[Dict[str, Any]]:
            async with semaphore:
                try:
                    return await asyncio.to_thread(agent.react, event, channel_label)
                except Exception as e:  # noqa: BLE001
                    logger.error("[%s] react ล้มเหลว: %s", agent.profile.agent_id, e)
                    return None

        results = await asyncio.gather(*(run(a) for a in active))
        out = [r for r in results if r]
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
        }
