import logging
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .expression import ExpressionContext, MediaAccess, choose_action, SILENT_SHIFT
from .memory_stream import MemoryStream
from .llm import get_client
from .scenario import Scenario

logger = logging.getLogger("mirofish.core.agent")


@dataclass
class AgentProfile:
    agent_id: str
    age: int
    occupation: str
    region: str
    base_personality: str = ""
    education: str = ""
    income_level: str = ""
    media: MediaAccess = field(default_factory=MediaAccess)
    deference: int = 40
    seniority_pressure: int = 30
    influence: float = 1.0
    is_kol: bool = False
    follower_count: int = 50


@dataclass
class OpinionState:
    stance: str = "neutral"
    intensity: int = 0
    confidence: int = 50


@dataclass
class AgentState:
    fear: int = 50
    anger: int = 50
    opinion: OpinionState = field(default_factory=OpinionState)


class GenerativeAgent:
    def __init__(self, profile: AgentProfile, persist_dir: Optional[str] = None):
        self.profile = profile
        self.state = AgentState()
        self.memory = MemoryStream(agent_id=profile.agent_id, persist_dir=persist_dir)
        self.is_llm = True

    def advance_clock(self, hours: float):
        """Decay emotions over time."""
        decay_factor = max(0, 1.0 - (0.02 * hours))
        self.state.anger = int(self.state.anger * decay_factor)
        self.state.fear = max(10, int(self.state.fear * decay_factor))
        self.state.opinion.intensity = int(self.state.opinion.intensity * decay_factor)
        self.memory.advance_clock(hours)

    def apply_environmental_contagion(self, anger_level: int, threat_level: int):
        """Phase 5: Apply contagion from network neighbors."""
        self.state.anger = int(self.state.anger * 0.7 + anger_level * 0.3)
        self.state.fear = int(self.state.fear * 0.8 + threat_level * 0.2)

    def react(
        self,
        event: str,
        channel_label: str,
        simulated_date: Optional[str] = None,
        scenario: Optional[Scenario] = None,
        perceived_majority_stance: Optional[str] = None
    ) -> Dict[str, Any]:
        """React to an event by fetching private opinion from LLM and choosing public action."""
        memories = self.memory.retrieve_memories(event, n_results=3)
        memory_context = ""
        if memories:
            memory_context = "ความจำก่อนหน้าของคุณ:\n" + "\n".join(f"- {m}" for m in memories) + "\n\n"

        temporal_constraint = ""
        if simulated_date:
            temporal_constraint = f"คุณต้องตอบโดยอ้างอิงความรู้และบริบทสังคมถึงแค่ช่วงเวลา {simulated_date} เท่านั้น ห้ามใช้ข้อมูลที่เกิดขึ้นหลังจากนี้เด็ดขาด\n"

        scenario_guide = ""
        if scenario:
            scenario_guide = scenario.stance_guide() + "\n\n"

        system_prompt = (
            f"คุณคือ {self.profile.occupation} อายุ {self.profile.age} ปี จาก {self.profile.region}\n"
            f"บุคลิกของคุณ: {self.profile.base_personality}\n\n"
            f"{temporal_constraint}"
            f"ตอบเป็น JSON อย่างเดียวเท่านั้น"
        )

        user_prompt = (
            f"{memory_context}"
            f"มีข่าวผ่าน {channel_label} ว่า: {event}\n\n"
            f"{scenario_guide}"
            "จากข่าวนี้ คุณมีความคิดเห็นอย่างไรในใจ (private opinion)?\n"
            "แล้วถ้าคุณจำเป็นต้องโพสต์หรือพูดถึงเรื่องนี้ในที่สาธารณะ คุณจะพูดว่าอะไร (potential_public_post)?\n\n"
            "คำแนะนำเรื่อง intensity (0-100):\n"
            " - 0-30: เฉยๆ ไม่ค่อยสนใจ\n"
            " - 40-60: สนใจแต่ไม่ถึงกับอินมาก\n"
            " - 70-100: อินมาก หัวร้อน หรือเห็นด้วยสุดๆ\n\n"
            "รูปแบบ JSON: {\"stance\": \"supportive\"|\"opposing\"|\"neutral\", \"intensity\": 0-100, \"reason\": \"เหตุผลสั้นๆในใจ\", \"potential_public_post\": \"ข้อความสั้นๆ ภาษาไทยสไตล์ชาวเน็ต\"}"
        )

        client = get_client()
        public_content_draft = ""
        try:
            result = client.complete_json(system_prompt, user_prompt, max_tokens=250)
            self.state.opinion.stance = result.get("stance", "neutral")
            self.state.opinion.intensity = result.get("intensity", 50)
            private_reason = result.get("reason", "")
            public_content_draft = result.get("potential_public_post", "")
        except Exception as e:
            logger.error(f"LLM Error for {self.profile.agent_id}: {e}")
            self.state.opinion.stance = "neutral"
            self.state.opinion.intensity = 0
            private_reason = "Error processing."
            public_content_draft = ""

        ctx = ExpressionContext(
            fear=self.state.fear,
            anger=self.state.anger,
            opinion_intensity=self.state.opinion.intensity,
            deference=self.profile.deference,
            seniority_pressure=self.profile.seniority_pressure,
            media=self.profile.media,
            stance=self.state.opinion.stance,
            available=scenario.actions if scenario else None,
            perceived_majority_stance=perceived_majority_stance
        )

        action = choose_action(ctx)

        public_content = ""
        if action.key != SILENT_SHIFT.key:
            public_content = public_content_draft

        mem_text = f"ข่าว: {event}. คิดในใจ: {self.state.opinion.stance} ({private_reason}). การกระทำ: {action.label_th} ({public_content})"
        self.memory.add_memory(mem_text, importance=int(self.state.opinion.intensity / 10))

        return {
            "agent_id": self.profile.agent_id,
            "private_opinion": {
                "stance": self.state.opinion.stance,
                "intensity": self.state.opinion.intensity,
                "reason": private_reason
            },
            "action_key": action.key,
            "action_label": action.label_th,
            "exposure": action.exposure,
            "public_content": public_content
        }
