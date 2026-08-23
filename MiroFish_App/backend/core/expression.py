"""
Expression filter — แปลง "สิ่งที่คิด" เป็น "สิ่งที่ทำ" (D10 ใน PLAN.md)

⚠️ ส่วนนี้ต้องเป็นโค้ด ห้ามฝากไว้กับ LLM

เหตุผล (วัดจริงแล้ว ดู C4 ใน PLAN.md):
  - LLM แทบไม่ตอบสนองต่อค่า fear เลย fear=15 กับ fear=85 ให้ผลเกือบเท่ากัน
  - พอบอกกติกาชัดเจนใน prompt กลับยุบเหลือคำตอบเดียว 100% ทุกระดับ
  - แค่ตัดฟิลด์ออกจากสคีมา การกระจาย action ก็เปลี่ยน
    -> ผลลัพธ์ไวต่อรูปแบบ prompt มากกว่าไวต่อตัวแปรที่เราตั้งใจศึกษา

การทำเป็นโค้ดทำให้กลไกตรวจสอบได้ ปรับจูนได้ อธิบายได้ และ reproduce ได้

โมเดล:
    drive    = แรงผลักให้อยากทำอะไรสักอย่าง (โกรธ + ความเข้มของความเห็น)
    ceiling  = เพดานความเสี่ยงที่ยอมรับได้ (ลดลงตามความกลัว/เกรงใจ/อาวุโส)
    weight   = ทำได้มั้ย x อยู่ใต้เพดานมั้ย x แรงผลักพอมั้ย
"""
import math
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .actions import (
    ALL_ACTIONS,
    SILENT_SHIFT,
    Action,
    allowed_for_stance,
    normalize_stance,
)


@dataclass
class MediaAccess:
    """เข้าถึงช่องทางไหนได้บ้าง — ตัวกำหนดว่ารับข่าวและพูดผ่านอะไรได้"""
    social_media: bool = False
    line: bool = True
    tv: bool = True
    community: bool = False

    def has(self, requirement: Optional[str]) -> bool:
        if requirement is None:
            return True
        return bool(getattr(self, requirement, False))


@dataclass
class ExpressionContext:
    """สภาวะที่ใช้ตัดสินว่าจะแสดงออกแค่ไหน (ทุกค่า 0-100)"""
    fear: int = 0             # กลัวถูกฟ้อง/สอบสวน — มีผลกับทุกช่องทาง
    anger: int = 0            # โกรธ
    opinion_intensity: int = 50   # ความเข้มข้นของความเห็น

    # เกรงใจและอาวุโสเป็น "แนวโน้มประจำตัว"
    # แต่จะกดจริงแค่ไหนขึ้นกับว่ากำลังพูดกับใคร (ดู Action.deference_weight)
    deference: int = 40
    seniority_pressure: int = 30

    # ตัวคูณตามสถานการณ์ 0-2 (1.0 = ปกติ)
    # เช่น เรื่องที่กระทบที่ทำงานตัวเองโดยตรง เกรงใจจะพุ่งขึ้น
    # หรือถ้าใช้บัญชีนิรนาม เกรงใจจะแทบหายไป
    situational_deference: float = 1.0

    media: MediaAccess = field(default_factory=MediaAccess)

    # จุดยืนปัจจุบัน — ใช้กัน action ที่ขัดกับจุดยืน (เช่น คนที่เห็นด้วยไปลงชื่อคัดค้าน)
    # None = ยังไม่มีจุดยืน จะเหลือเฉพาะ action ที่เป็นกลางทางทิศทาง
    stance: Optional[str] = None

    # action ที่ "มีอยู่จริง" ในเหตุการณ์นี้ (ดู core/scenario.py)
    # None = ใช้ทั้งหมด ซึ่งเป็นค่าที่ทำให้เกิดบั๊ก "ไปม็อบเรื่องไอศกรีม"
    # จึงควรส่งชุดของ scenario เข้ามาเสมอเมื่อใช้งานจริง
    available: Optional[List[Action]] = None
    
    # Spiral of Silence: ความเห็นส่วนใหญ่ของรอบที่แล้ว
    perceived_majority_stance: Optional[str] = None

    # ── ตัวแปรที่คำนวณได้ ──

    @property
    def drive(self) -> float:
        """แรงผลักให้อยากทำอะไรสักอย่าง 0-1"""
        return min(1.0, (self.anger * 0.6 + self.opinion_intensity * 0.4) / 100)

    @property
    def legal_fear(self) -> float:
        """ความกลัวผลทางกฎหมาย 0-1 — มีผลกับทุกช่องทางเท่ากัน

        ต่างจากเกรงใจตรงที่ไม่ได้ขึ้นกับว่าคุยกับใคร
        โพสต์ผิดในกลุ่มไลน์ก็โดนได้เหมือนโพสต์สาธารณะ
        """
        courage = (self.anger / 100) * 0.18
        return max(0.0, min(1.0, self.fear / 100 - courage))

    @property
    def social_pressure(self) -> float:
        """แรงกดทางสังคมประจำตัว 0-1 (ยังไม่คูณกับคู่สนทนา)"""
        base = (self.deference * 0.6 + self.seniority_pressure * 0.4) / 100
        
        # ทฤษฎี Spiral of Silence: ถ้าจุดยืนตรงกับคนส่วนใหญ่ จะกล้าพูดมากขึ้น (เกรงใจลดลง 50%)
        if self.stance and self.perceived_majority_stance and self.stance == self.perceived_majority_stance:
            base *= 0.5
            
        return max(0.0, min(1.5, base * self.situational_deference))

    def risk_aversion_for(self, action: Action) -> float:
        """ความไม่อยากเสี่ยงสำหรับ action หนึ่งๆ

        แยกสองแรง:
          - กลัวคดี   -> กดเท่ากันทุกช่องทาง
          - เกรงใจ    -> กดตามว่ากำลังเผชิญหน้ากับใคร (deference_weight)
        นี่คือเหตุผลที่คนคนเดียวกันบ่นที่บ้านได้ แต่เงียบกริบต่อหน้าหัวหน้า
        """
        return (
            self.legal_fear * 3.5
            + self.social_pressure * action.deference_weight * 1.6
        )

    @property
    def exposure_ceiling(self) -> float:
        """เพดานความเสี่ยงจากความกลัวคดี (ตัดขาดอีกชั้น)"""
        return max(0.0, min(5.0, 5.0 * (1.0 - self.legal_fear)))


def score_actions(ctx: ExpressionContext) -> List[Tuple[Action, float]]:
    """ให้น้ำหนักทุก action ตามสภาวะ — คืนเฉพาะตัวที่มีน้ำหนัก > 0

    สามแรงประกอบกัน:
      1. อยากทำแค่ไหน  — target = drive x 5 (โกรธมาก/เห็นเข้มข้น = อยากทำแรง)
      2. กลัวแค่ไหน    — risk_aversion กดทุก action ตามสัดส่วน exposure (ต่อเนื่อง)
      3. เพดานเด็ดขาด  — เกิน ceiling แล้วโอกาสร่วงแรง
    """
    ceiling = ctx.exposure_ceiling
    drive = ctx.drive
    target = drive * 5.0
    stance = normalize_stance(ctx.stance)
    pool = ctx.available if ctx.available is not None else ALL_ACTIONS
    scored: List[Tuple[Action, float]] = []

    for action in pool:
        if action.key == SILENT_SHIFT.key:
            continue  # คิดแยกด้านล่าง

        # 1) ช่องทางต้องมี
        if not ctx.media.has(action.requires):
            continue

        # 2) ต้องเข้ากับจุดยืน — คนที่เห็นด้วยไม่ไปลงชื่อคัดค้านตัวเอง
        if not allowed_for_stance(action, stance):
            continue

        # 3) แรงผลักต้องถึงขั้นต่ำ
        if drive < action.min_drive:
            continue

        # 4) ระยะห่างระหว่าง "ความสะใจที่ได้" กับ "ความสะใจที่อยากได้"
        #    ใช้ satisfaction ไม่ใช่ exposure เพราะบางการกระทำได้ระบายเยอะแต่เสี่ยงน้อย
        #    (เลี่ยงบาลี / กลุ่มไลน์ปิด) ซึ่งเป็นทางออกของสังคมที่ถูกกดทับ
        delta = action.satisfaction - target
        if delta > 0:
            weight = math.exp(-1.2 * delta)      # แรงกว่าที่อยากทำ
        else:
            weight = math.exp(-0.55 * -delta)    # เบากว่าที่อยากทำ ยังเป็นไปได้มาก

        # 5) ความไม่อยากเสี่ยง — คิดแยกรายการ เพราะเกรงใจกดแต่ละช่องทางไม่เท่ากัน
        weight *= math.exp(-ctx.risk_aversion_for(action) * action.exposure / 5.0)

        # 6) เกินเพดานเด็ดขาด ลงโทษซ้ำอีกชั้น
        over_ceiling = action.exposure - ceiling
        if over_ceiling > 0:
            weight *= math.exp(-1.8 * over_ceiling)

        if weight > 1e-4:
            scored.append((action, weight))

    # "เงียบ" เป็นตัวเลือกเสมอ และต้องหนักขึ้นชัดเจนเมื่อกลัวมาก
    # ใช้เลขชี้กำลัง 1.5 เพื่อให้ผลของความกลัวมาแรงในช่วงท้าย
    # (คนกลัวปานกลางยังพูด แต่คนกลัวมากเงียบสนิท)
    silent_weight = (
        0.25
        + ((ctx.fear / 100) ** 1.5) * 3.6
        + (1.0 - drive) * 1.0
    )
    scored.append((SILENT_SHIFT, silent_weight))
    return scored


def choose_action(ctx: ExpressionContext, rng: Optional[random.Random] = None) -> Action:
    """สุ่มเลือก action ตามน้ำหนัก (ใช้ rng ที่ seed ไว้เพื่อให้ reproduce ได้)"""
    rng = rng or random
    scored = score_actions(ctx)
    actions = [a for a, _ in scored]
    weights = [w for _, w in scored]
    return rng.choices(actions, weights=weights, k=1)[0]


def distribution(ctx: ExpressionContext) -> Dict[str, float]:
    """คืนความน่าจะเป็นของแต่ละ action — ใช้ตรวจสอบและดีบักกลไก"""
    scored = score_actions(ctx)
    total = sum(w for _, w in scored) or 1.0
    return {a.label_th: w / total for a, w in sorted(scored, key=lambda x: -x[1])}


def expected_exposure(ctx: ExpressionContext) -> float:
    """ค่า exposure คาดหวัง — ตัวชี้วัดหลักว่ากลไก fear ทำงานมั้ย"""
    scored = score_actions(ctx)
    total = sum(w for _, w in scored) or 1.0
    return sum(a.exposure * w for a, w in scored) / total
