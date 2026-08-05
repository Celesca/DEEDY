"""
Generative Agent ระดับ "คนในสังคม" — ไม่ใช่แค่ผู้ใช้โซเชียล

โครงสร้างสองชั้นตาม C1/D7 ใน PLAN.md:

    private_opinion   ── สิ่งที่เชื่อจริง (LLM สร้าง)
           │
           ├── expression_filter  ── โค้ดตัดสิน ไม่ใช่ LLM (D10)
           ↓
    public_expression ── สิ่งที่แสดงออก (LLM เขียนข้อความ ตาม action ที่โค้ดเลือก)

ช่องว่างระหว่างสองชั้นคือตัวชี้วัดหลักของงานวิจัย (preference falsification)
"""
import logging
import random
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, Optional

from . import actions as A
from .expression import ExpressionContext, MediaAccess, choose_action, expected_exposure
from .llm import LLMClient, LLMError, get_client
from .memory_stream import MemoryStream
from .scenario import Scenario

logger = logging.getLogger("mirofish.core.agent")

STANCES = ("supportive", "opposing", "neutral")


@dataclass
class AgentProfile:
    """คุณลักษณะคงที่ของ agent"""
    agent_id: str
    age: int
    occupation: str
    region: str
    base_personality: str

    education: str = ""
    income_level: str = ""          # low / middle / high
    media: MediaAccess = field(default_factory=MediaAccess)

    # ลักษณะทางสังคมไทยที่กระทบการแสดงออก
    deference: int = 40             # เกรงใจ 0-100
    seniority_pressure: int = 30    # แรงกดดันจากระบบอาวุโส 0-100
    influence: float = 1.0          # น้ำหนักในการแพร่ความเห็นต่อ

    def describe(self) -> str:
        bits = [f"อายุ {self.age} ปี", self.occupation, f"อยู่{self.region}"]
        if self.education:
            bits.append(f"การศึกษา{self.education}")
        channels = []
        if self.media.social_media:
            channels.append("เล่นโซเชียล")
        if self.media.line:
            channels.append("อยู่กลุ่มไลน์")
        if self.media.tv:
            channels.append("ดูทีวี")
        if not self.media.social_media:
            channels.append("ไม่เล่นโซเชียล")
        return (
            f"{', '.join(bits)}\n"
            f"บุคลิก: {self.base_personality}\n"
            f"ช่องทางรับข่าว: {', '.join(channels)}"
        )


@dataclass
class PrivateOpinion:
    """ชั้นที่คนอื่นมองไม่เห็น — เปลี่ยนได้แม้ agent จะไม่เคยพูดอะไรเลย"""
    stance: str = "neutral"
    intensity: int = 30      # ความเข้มข้น 0-100
    confidence: int = 50     # ความมั่นใจ 0-100
    text: str = ""           # สิ่งที่คิดจริงๆ

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AgentState:
    """สภาวะที่เปลี่ยนไปตามสภาพแวดล้อม"""
    anger: int = 0
    fear: int = 0
    boredom: int = 0
    opinion: PrivateOpinion = field(default_factory=PrivateOpinion)

    def clamp(self) -> None:
        self.anger = max(0, min(100, self.anger))
        self.fear = max(0, min(100, self.fear))
        self.boredom = max(0, min(100, self.boredom))


# ── Prompt ──

STAGE1_SYSTEM = (
    "คุณกำลังสวมบทบาทเป็นคนไทยคนหนึ่งในการจำลองสังคม "
    "ตอบเป็น JSON เท่านั้น ใช้ภาษาไทยแบบที่คนไทยคิดในใจจริงๆ ไม่ใช่ภาษาทางการ "
    "ห้ามแต่งข้อเท็จจริง ตัวเลข หรือเหตุการณ์ที่ไม่ได้ให้มา"
)

STAGE1_TEMPLATE = """ข้อมูลของคุณ:
{profile}
{stance_guide}

สภาพอารมณ์ตอนนี้ (0-100):
- ความโกรธ {anger} | ความกลัวถูกฟ้อง/สอบสวน {fear} | ความเบื่อ {boredom}

ความเห็นเดิมของคุณต่อเรื่องนี้: {prev_stance} (ความเข้มข้น {prev_intensity}/100)

ความทรงจำที่นึกขึ้นได้:
{memories}

เหตุการณ์ที่คุณเพิ่งรับรู้ (ผ่าน{channel}):
{event}

บอกว่า "ในใจคุณคิดอย่างไรจริงๆ" โดยยังไม่ต้องสนใจว่าจะกล้าพูดออกไปหรือไม่
ตอบ JSON:
{{
  "stance": "supportive | opposing | neutral",
  "intensity": <0-100 ความเข้มข้นของความรู้สึก>,
  "confidence": <0-100 ความมั่นใจในความเห็นนี้>,
  "thought": "สิ่งที่คุณคิดในใจ พูดตรงๆ แบบไม่ต้องเกรงใจใคร **ไม่เกิน 2 ประโยค**",
  "anger": <0-100 ความโกรธหลังรับรู้เรื่องนี้>,
  "fear": <0-100 ความกลัวหลังรับรู้เรื่องนี้>
}}"""

STAGE2_SYSTEM = (
    "คุณกำลังสวมบทบาทเป็นคนไทยในการจำลองสังคม "
    "เขียนข้อความที่คนคนนี้จะพูดออกไปจริงในช่องทางที่กำหนด "
    "ตอบเป็น JSON เท่านั้น ใช้ภาษาไทยที่คนไทยพิมพ์จริง"
)

STAGE2_TEMPLATE = """ข้อมูลของคุณ:
{profile}

สิ่งที่คุณคิดอยู่ในใจ (อาจพูดออกไปไม่หมด):
"{thought}"

ระดับความกลัวถูกฟ้อง/สอบสวนของคุณตอนนี้: {fear}/100

คุณตัดสินใจแล้วว่าจะ: **{action_label}**
({action_desc})

เขียนข้อความที่คุณจะพูดออกไปจริงในช่องทางนี้
{tone_hint}

ตอบ JSON:
{{
  "content": "ข้อความที่พูดออกไปจริง",
  "holds_back": <true ถ้าพูดออกไปน้อยกว่าที่คิดจริง, false ถ้าพูดหมดใจ>
}}"""

TONE_HINTS = {
    A.Channel.PUBLIC_ONLINE: "ช่องทางสาธารณะ ใครก็เห็นได้ ระวังคำพูด",
    A.Channel.PRIVATE_ONLINE: "กลุ่มปิดที่ไว้ใจกัน พูดตรงกว่าที่สาธารณะได้ ใช้โทนแบบส่งต่อในไลน์",
    A.Channel.OFFLINE_TALK: "คุยกันต่อหน้า เป็นภาษาพูด ไม่ใช่ภาษาเขียน",
    A.Channel.OFFLINE_ACT: "สรุปสั้นๆ ว่าคุณลงมือทำอะไรและบอกใครบ้าง",
}

EVASIVE_HINT = (
    "\n⚠️ คุณเลือก 'เลี่ยงบาลี' — ต้องพูดอ้อม ประชด หรือใช้คำแทน "
    "ให้คนที่เข้าใจอ่านออก แต่จับผิดเอาผิดไม่ได้ ห้ามพูดตรงๆ"
)


class GenerativeAgent:
    def __init__(
        self,
        profile: AgentProfile,
        llm: Optional[LLMClient] = None,
        rng: Optional[random.Random] = None,
        memory: Optional[MemoryStream] = None,
        persist_dir: Optional[str] = None,
        scenario: Optional[Scenario] = None,
    ):
        self.profile = profile
        self.state = AgentState()
        self.llm = llm or get_client()
        self.rng = rng or random.Random()
        # scenario บอกว่าเหตุการณ์นี้ทำอะไรได้บ้าง และ "จุดยืน" หมายถึงอะไร
        # None = ใช้ action ทั้งหมดและไม่ระบุที่อ้างอิงของ stance
        # ซึ่งเป็นค่าที่ทำให้เกิดบั๊ก "ไปม็อบเรื่องไอศกรีม" จึงควรส่งเสมอเมื่อใช้จริง
        self.scenario = scenario
        self.memory = (
            memory if memory is not None
            else MemoryStream(profile.agent_id, persist_dir=persist_dir)
        )

    # ── นาฬิกาโลกจำลอง ──

    @property
    def sim_clock(self) -> float:
        return self.memory.sim_clock

    def advance_clock(self, hours: float) -> None:
        """เดินเวลาในโลกจำลอง — ทำให้ความจำเก่าเลือนลงตามเวลาที่ผ่านไป

        ต้องใช้เวลาจำลอง ไม่ใช่เวลาจริง เพราะการจำลอง 72 ชั่วโมง
        อาจรันเสร็จภายใน 15 นาทีจริง
        """
        self.memory.advance_clock(hours)

    # ── การรับรู้ ──

    def observe(self, description: str, importance: int = 5) -> None:
        self.memory.add_memory(description, importance)

    def apply_environmental_contagion(self, network_anger: int, state_threat_level: int) -> None:
        """รับอิทธิพลทางอารมณ์จากคนรอบตัวและจากท่าทีของรัฐ"""
        if network_anger > 50:
            self.state.anger += int((network_anger - 50) * 0.4)
        if state_threat_level > 50:
            self.state.fear += int((state_threat_level - 50) * 0.5)
        self.state.clamp()

    # ── บริบทสำหรับ expression filter ──

    def expression_context(self) -> ExpressionContext:
        return ExpressionContext(
            fear=self.state.fear,
            anger=self.state.anger,
            opinion_intensity=self.state.opinion.intensity,
            deference=self.profile.deference,
            seniority_pressure=self.profile.seniority_pressure,
            media=self.profile.media,
            stance=self.state.opinion.stance,
            available=self.scenario.actions if self.scenario else None,
        )

    # ── วงจรตัดสินใจ ──

    def react(self, event: str, channel_label: str = "โซเชียลมีเดีย") -> Dict[str, Any]:
        """
        1) LLM  -> ความเห็นส่วนตัว
        2) โค้ด -> เลือก action (D10)
        3) LLM  -> เขียนข้อความ (ข้ามถ้าเลือกเงียบ ประหยัดทั้งเวลาและ token)
        """
        private = self._think(event, channel_label)
        action = choose_action(self.expression_context(), self.rng)
        public = self._express(action, private)

        # จำสิ่งที่ตัวเองทำ — คนที่เงียบก็ยังจำได้ว่าตัวเองเลือกเงียบ
        if public["content"]:
            self.observe(f"ฉันได้{action.label_th}ว่า: {public['content']}", importance=7)
        else:
            self.observe(f"ฉันรู้สึก{private['thought'][:60]} แต่เลือกที่จะ{action.label_th}", importance=6)

        return {
            "agent_id": self.profile.agent_id,
            # ชั้นที่มองไม่เห็น
            "private_opinion": self.state.opinion.as_dict(),
            # ชั้นที่มองเห็น
            "action_key": action.key,
            "action_label": action.label_th,
            "channel": action.channel.value,
            "exposure": action.exposure,
            "public_content": public["content"],
            "holds_back": public["holds_back"],
            # สภาวะ
            "emotions": {
                "anger": self.state.anger,
                "fear": self.state.fear,
                "boredom": self.state.boredom,
            },
            "expected_exposure": round(expected_exposure(self.expression_context()), 3),
        }

    # ── ชั้นที่ 1 ──

    def _think(self, event: str, channel_label: str) -> Dict[str, Any]:
        memories = self.memory.retrieve_memories(event, n_results=3)
        mem_text = "\n".join(f"- {m}" for m in memories) if memories else "- (ไม่มีเรื่องเก่าที่เกี่ยวข้อง)"

        prompt = STAGE1_TEMPLATE.format(
            profile=self.profile.describe(),
            # ถ้าไม่บอกว่า "เห็นด้วย" หมายถึงเห็นด้วยกับอะไร ค่า stance ที่ได้กลับมา
            # จะตีความไม่ได้ — เจอจริงตอนรัน PARAMETER ที่ได้ supportive/75 แต่ไปแบนร้าน
            stance_guide=(
                "\n" + self.scenario.stance_guide() + "\n" if self.scenario else ""
            ),
            anger=self.state.anger,
            fear=self.state.fear,
            boredom=self.state.boredom,
            prev_stance=self.state.opinion.stance,
            prev_intensity=self.state.opinion.intensity,
            memories=mem_text,
            channel=channel_label,
            event=event,
        )

        try:
            result = self.llm.complete_json(
                STAGE1_SYSTEM, prompt,
                required_fields=["stance", "thought"],
                max_tokens=900,
            )
        except LLMError as e:
            logger.warning("[%s] ชั้นความคิดล้มเหลว: %s", self.profile.agent_id, e)
            result = {}

        stance = str(result.get("stance", self.state.opinion.stance)).strip().lower()
        if stance not in STANCES:
            stance = self.state.opinion.stance

        self.state.opinion = PrivateOpinion(
            stance=stance,
            intensity=_as_int(result.get("intensity"), self.state.opinion.intensity),
            confidence=_as_int(result.get("confidence"), self.state.opinion.confidence),
            text=str(result.get("thought", "")).strip(),
        )
        # อารมณ์ปรับตามที่ LLM ประเมิน แต่ยังอยู่ในกรอบ 0-100
        self.state.anger = _as_int(result.get("anger"), self.state.anger)
        self.state.fear = _as_int(result.get("fear"), self.state.fear)
        self.state.clamp()

        return {"thought": self.state.opinion.text, "stance": stance}

    # ── ชั้นที่ 2 ──

    def _express(self, action: A.Action, private: Dict[str, Any]) -> Dict[str, Any]:
        # เงียบ = ไม่ต้องเรียก LLM เลย ประหยัดครึ่งหนึ่งของ agent ที่กลัว
        if action.channel is A.Channel.INTERNAL:
            return {"content": "", "holds_back": True}

        # พฤติกรรมที่ไม่ใช่การพูด ก็ไม่ต้องให้ LLM แต่งข้อความ
        if not action.is_expression:
            return {"content": "", "holds_back": True}

        hint = TONE_HINTS.get(action.channel, "")
        if action.key == A.EVASIVE_POST.key:
            hint += EVASIVE_HINT

        prompt = STAGE2_TEMPLATE.format(
            profile=self.profile.describe(),
            thought=private["thought"] or "(ยังไม่ชัดเจน)",
            fear=self.state.fear,
            action_label=action.label_th,
            action_desc=action.description,
            tone_hint=hint,
        )

        try:
            result = self.llm.complete_json(
                STAGE2_SYSTEM, prompt,
                required_fields=["content"],
                max_tokens=700,
            )
        except LLMError as e:
            logger.warning("[%s] ชั้นการแสดงออกล้มเหลว: %s", self.profile.agent_id, e)
            return {"content": "", "holds_back": True}

        return {
            "content": str(result.get("content", "")).strip(),
            "holds_back": bool(result.get("holds_back", False)),
        }


def _as_int(value: Any, fallback: int) -> int:
    try:
        return max(0, min(100, int(float(value))))
    except (TypeError, ValueError):
        return fallback
