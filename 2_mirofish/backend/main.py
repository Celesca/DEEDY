"""
API ของเครื่องยนต์จำลอง MiroFish TH (DEEDY)

รัน:  cd backend && ../backend/venv/bin/uvicorn main:app --reload --port 8000

⚠️ สถานะ Phase 0/1 — ประชากรยัง hardcode ไว้ 3 คนเพื่อทดสอบ
   Phase 3 จะโหลดจากไฟล์ประชากรที่สุ่มตามสัดส่วน NSO จริง
"""
import logging
import random
from typing import Any, Dict, List

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from core.agent import AgentProfile, GenerativeAgent
from core.config import LLM, SIM
from core.environment import PlatformHub
from core.expression import MediaAccess

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

app = FastAPI(
    title="MiroFish TH — Thai Social Simulation Engine",
    description="จำลองความเห็นและพฤติกรรมของสังคมไทยเมื่อเกิดเหตุการณ์",
    version="0.2.0",
)

hub = PlatformHub()


# ── ประชากรทดสอบ (Phase 3 จะแทนที่ด้วยประชากรจริงตามสัดส่วน NSO) ──

def _seed_population() -> None:
    rng = random.Random(SIM.seed)
    people = [
        AgentProfile(
            agent_id="student_bkk", age=22, occupation="นักศึกษา", region="กรุงเทพฯ",
            base_personality="หัวก้าวหน้า ชอบตั้งคำถามกับระบบเก่า พิมพ์ติดตลก",
            education="ปริญญาตรี",
            media=MediaAccess(social_media=True, line=True, tv=False),
            deference=20, seniority_pressure=15,
        ),
        AgentProfile(
            agent_id="civil_servant_isan", age=47, occupation="ข้าราชการ", region="ภาคอีสาน",
            base_personality="รักสงบ ไม่ชอบมีเรื่อง แต่แอบอึดอัดกับระบบเส้นสาย",
            education="ปริญญาตรี",
            media=MediaAccess(social_media=False, line=True, tv=True, community=True),
            deference=70, seniority_pressure=65,
        ),
        AgentProfile(
            agent_id="shop_owner_south", age=58, occupation="เจ้าของร้านค้า", region="ภาคใต้",
            base_personality="อนุรักษ์นิยม เชื่อในความพยายาม ห่วงเรื่องเศรษฐกิจ",
            education="มัธยม",
            media=MediaAccess(social_media=False, line=True, tv=True, community=True),
            deference=55, seniority_pressure=40,
        ),
    ]
    for p in people:
        hub.add_agent(GenerativeAgent(p, rng=random.Random(rng.randrange(1 << 30))))


_seed_population()


# ── Schema ──

class EventPayload(BaseModel):
    description: str = Field(..., description="เหตุการณ์ที่เกิดขึ้น")
    channel: str = Field("โซเชียลมีเดีย", description="ช่องทางที่ข่าวมาถึง")
    state_threat_level: int = Field(0, ge=0, le=100, description="ระดับท่าทีคุกคามจากรัฐ")


class PrivateOpinionOut(BaseModel):
    stance: str
    intensity: int
    confidence: int
    text: str


class AgentReaction(BaseModel):
    agent_id: str
    round: int
    private_opinion: PrivateOpinionOut
    action_key: str
    action_label: str
    channel: str
    exposure: float
    public_content: str
    holds_back: bool
    emotions: Dict[str, int]
    expected_exposure: float


class SimulationResponse(BaseModel):
    event: str
    reactions: List[AgentReaction]
    snapshot: Dict[str, Any]
    silent_count: int = Field(..., description="จำนวนคนที่มีความเห็นแต่ไม่พูดอะไรออกมา")


# ── Endpoints ──

@app.get("/")
def read_root() -> Dict[str, Any]:
    return {
        "status": "ok",
        "engine": "MiroFish TH (DEEDY)",
        "model": LLM.model,
        "llm_configured": LLM.is_configured(),
        "population": len(hub.agents),
        "round": hub.round_num,
    }


@app.get("/simulate/state")
def get_state() -> Dict[str, Any]:
    return hub.snapshot()


@app.post("/simulate/event", response_model=SimulationResponse)
async def trigger_event(payload: EventPayload) -> SimulationResponse:
    if not LLM.is_configured():
        raise HTTPException(500, "ยังไม่ได้ตั้งค่า LLM_API_KEY ใน .env")
    if not hub.agents:
        raise HTTPException(500, "ยังไม่มีประชากรในระบบ")

    hub.state_threat = payload.state_threat_level
    results = await hub.broadcast_event_async(payload.description, payload.channel)

    return SimulationResponse(
        event=payload.description,
        reactions=[AgentReaction(**r) for r in results],
        snapshot=hub.snapshot(),
        silent_count=sum(1 for r in results if not r["public_content"]),
    )


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
