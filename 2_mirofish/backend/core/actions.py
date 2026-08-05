"""
Action space ระดับสังคม — ไม่ใช่แค่พฤติกรรมบนแพลตฟอร์ม (ดู C2 ใน PLAN.md)

หลักสำคัญ:
  1. "เงียบ" ไม่ใช่ผลลัพธ์ว่าง — คนส่วนใหญ่ของสังคมไม่เคยโพสต์ แต่เขาไปเลือกตั้ง
     เลิกซื้อของ กักตุนของ พฤติกรรมพวกนี้ต้องนับเป็นผลลัพธ์เต็มตัว
  2. exposure = ความเสี่ยงทางสังคมที่มองเห็นได้ ไม่ใช่ความแรงของความรู้สึก
     "เลี่ยงบาลี" มี exposure ต่ำเพราะพูดอ้อมจนจับผิดไม่ได้ แม้จะโพสต์สาธารณะ
     "แบนสินค้า" exposure ต่ำมากเพราะไม่มีใครรู้ แต่เป็นพฤติกรรมที่มีผลจริง
"""
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional


class Channel(str, Enum):
    """ช่องทางที่การกระทำเกิดขึ้น"""
    PUBLIC_ONLINE = "public_online"    # โซเชียลสาธารณะ
    PRIVATE_ONLINE = "private_online"  # กลุ่มไลน์ ปิด ไว้ใจสูง
    OFFLINE_TALK = "offline_talk"      # คุยกับคนจริงๆ
    OFFLINE_ACT = "offline_act"        # ลงมือทำในโลกจริง
    INTERNAL = "internal"              # ไม่แสดงออกเลย


@dataclass(frozen=True)
class Action:
    key: str
    label_th: str
    channel: Channel
    # ความเสี่ยงที่คนอื่นเห็นและเอาผิดได้ 0 = ไม่มีใครรู้, 5 = เปิดเผยตัวตนเต็มที่
    exposure: float
    # ความสะใจ/ความรู้สึกว่าได้ระบาย 0-5
    # แยกจาก exposure เพราะบางการกระทำ "ได้ระบายมากแต่เสี่ยงน้อย"
    # เช่น เลี่ยงบาลี หรือส่งในกลุ่มไลน์ปิด ซึ่งเป็นทางออกหลักของสังคมที่ถูกกดทับ
    # None = ใช้ค่าเท่ากับ exposure
    expressive_value: Optional[float] = None
    # ต้องมีช่องทางไหนถึงจะทำได้ (None = ทำได้เสมอ)
    requires: Optional[str] = None
    # ต้องมีแรงผลักดันขั้นต่ำแค่ไหนถึงจะลงมือ (0-1)
    min_drive: float = 0.0
    # เกรงใจ/ระบบอาวุโส กดการกระทำนี้แรงแค่ไหน (0 = ไม่เกี่ยวเลย, 2 = กดแรงมาก)
    # เกรงใจเป็นเรื่องของ "ความสัมพันธ์กับคู่สนทนา" ไม่ใช่คุณสมบัติของคนเฉยๆ
    # คนคนเดียวกันบ่นกับคนที่บ้านได้ แต่พูดเรื่องเดียวกันกับหัวหน้าไม่ได้
    deference_weight: float = 1.0
    # เป็นการ "แสดงความเห็น" มั้ย (False = เป็นพฤติกรรมแต่ไม่ได้ประกาศจุดยืน)
    is_expression: bool = True
    # การกระทำนี้สมเหตุสมผลกับจุดยืนแบบไหน
    #   "oppose"  = ทำเมื่อไม่เห็นด้วยเท่านั้น (แบน ม็อบ ลงชื่อคัดค้าน)
    #   "support" = ทำเมื่อเห็นด้วยเท่านั้น (โพสต์อวด ออกมาปกป้อง)
    #   "any"     = ทำได้ทุกจุดยืน เนื้อหาเป็นตัวบอกทิศทางเอง (โพสต์ คุยกับที่บ้าน)
    #
    # ⚠️ `buy_anyway` ตั้งใจให้เป็น "any" ไม่ใช่ "support" — เพราะปรากฏการณ์ที่
    #    อยากจับคือ "ด่าแต่ยังไปซื้อ" ถ้ากันไว้ให้เฉพาะคนที่เห็นด้วย
    #    ช่องว่างระหว่างสิ่งที่พูดกับสิ่งที่ทำจะหายไปทั้งหมด
    stance_direction: str = "any"
    description: str = ""

    @property
    def satisfaction(self) -> float:
        """ความรู้สึกว่าได้ระบาย — ปริยายเท่ากับ exposure"""
        return self.exposure if self.expressive_value is None else self.expressive_value


# ── ออนไลน์ สาธารณะ ──
POST_PUBLIC = Action(
    "post_public", "โพสต์สาธารณะ", Channel.PUBLIC_ONLINE, exposure=5.0,
    requires="social_media", min_drive=0.35, deference_weight=0.7,
    description="ประกาศจุดยืนโดยเปิดเผยตัวตน เสี่ยงสูงสุด",
)
SHARE_PUBLIC = Action(
    "share_public", "แชร์ข่าวสาธารณะ", Channel.PUBLIC_ONLINE, exposure=3.5,
    requires="social_media", min_drive=0.2, deference_weight=0.6,
    description="แชร์ต่อโดยไม่ต้องเขียนความเห็นเอง เสี่ยงน้อยกว่าโพสต์",
)
EVASIVE_POST = Action(
    "evasive_post", "เลี่ยงบาลี", Channel.PUBLIC_ONLINE, exposure=1.5,
    # ระบายได้เยอะ (3.6) แต่เสี่ยงต่ำ (1.5) — นี่คือเหตุผลที่มันเป็นทางออกหลัก
    # ของคนที่โกรธมากแต่กลัวคดี
    expressive_value=3.6,
    requires="social_media", min_drive=0.25, deference_weight=0.25,
    description="พูดอ้อม ประชด หรือใช้คำแทน เพื่อระบายโดยไม่ให้จับผิดได้ "
                "— พฤติกรรมเด่นของโซเชียลไทยเมื่อกลัวผลทางกฎหมาย",
)

# ── ออนไลน์ ปิด ──
SHARE_LINE = Action(
    "share_line", "ส่งในกลุ่มไลน์", Channel.PRIVATE_ONLINE, exposure=2.0,
    # กลุ่มปิดที่ไว้ใจกัน พูดได้เต็มปาก (3.2) แต่คนนอกไม่เห็น (2.0)
    expressive_value=3.2,
    requires="line", min_drive=0.15, deference_weight=0.9,
    description="ส่งต่อในกลุ่มปิด ไว้ใจสูง ตรวจสอบยาก เป็นท่อหลักของคนวัยกลางคนขึ้นไป",
)

# ── ออฟไลน์ คุย ──
TALK_FAMILY = Action(
    "talk_family", "คุยกับคนในบ้าน", Channel.OFFLINE_TALK, exposure=1.0,
    # บ่นกับคนที่บ้านได้เต็มที่ (2.8) โดยแทบไม่มีความเสี่ยง (1.0)
    expressive_value=2.8,
    min_drive=0.1, deference_weight=0.5,
    description="ปลอดภัยที่สุดในการระบาย และเป็นท่อที่ความเห็นข้ามรุ่นข้ามขั้วได้",
)
TALK_WORK = Action(
    "talk_work", "คุยกับเพื่อนร่วมงาน", Channel.OFFLINE_TALK, exposure=2.5,
    min_drive=0.2, deference_weight=1.7,
    description="เสี่ยงกว่าที่บ้านเพราะมีเรื่องอาวุโสและผลต่อหน้าที่การงาน",
)
CONSULT_LEADER = Action(
    "consult_leader", "ปรึกษาผู้นำชุมชน", Channel.OFFLINE_TALK, exposure=2.5,
    requires="community", min_drive=0.3, deference_weight=1.9,
    description="สำคัญมากในต่างจังหวัด",
)

# ── ออฟไลน์ ลงมือ ──
JOIN_PROTEST = Action(
    "join_protest", "ไปม็อบ", Channel.OFFLINE_ACT, exposure=5.0, min_drive=0.7, deference_weight=0.8,
    stance_direction="oppose",
    description="แสดงตัวต่อสาธารณะ ต้นทุนสูงทั้งเวลาและความเสี่ยง",
)
SIGN_PETITION = Action(
    "sign_petition", "ลงชื่อคัดค้าน", Channel.OFFLINE_ACT, exposure=3.5, min_drive=0.4, deference_weight=0.7,
    stance_direction="oppose",
    description="แสดงตัวแต่อยู่ในกรอบกฎหมายชัดเจน",
)
COMPLAIN_OFFICIAL = Action(
    "complain_official", "ร้องเรียนหน่วยงาน", Channel.OFFLINE_ACT, exposure=3.0, min_drive=0.45, deference_weight=1.2,
    stance_direction="oppose",
    description="ใช้ช่องทางทางการ เปิดเผยตัวแต่เฉพาะต่อหน่วยงาน",
)
BOYCOTT = Action(
    "boycott", "เลิกซื้อ/แบน", Channel.OFFLINE_ACT, exposure=0.5, min_drive=0.3,
    # ลงมือจริงจึงรู้สึกว่าได้ทำอะไร (2.5) แต่ไม่มีใครรู้ (0.5)
    expressive_value=2.5, is_expression=False, deference_weight=0.0,
    stance_direction="oppose",
    description="ไม่มีใครรู้ว่าเราทำ แต่รวมกันแล้วมีผลทางเศรษฐกิจจริง",
)
STOCKPILE = Action(
    "stockpile", "กักตุนของ", Channel.OFFLINE_ACT, exposure=0.5, min_drive=0.35,
    is_expression=False, deference_weight=0.0,
    description="พฤติกรรมตอบสนองความกลัว ไม่ใช่การแสดงจุดยืน",
)
WITHDRAW_MONEY = Action(
    "withdraw_money", "ถอนเงิน/ย้ายเงิน", Channel.OFFLINE_ACT, exposure=0.5, min_drive=0.5,
    is_expression=False, deference_weight=0.0,
    description="ตอบสนองความไม่มั่นใจทางเศรษฐกิจ",
)

# ── ออฟไลน์ ลงมือ: ฝั่ง "เข้าร่วม" ──
# ของเดิมมีแต่ประท้วง/ร้องเรียน/ถอนตัว ไม่มีอะไรที่แปลว่า "เอาด้วย" เลย
# ทำให้จำลองปรากฏการณ์แบบ "ยิ่งด่ายิ่งขายดี" ไม่ได้ในเชิงโครงสร้าง
# (OASIS มี PURCHASE_PRODUCT อยู่แล้ว แต่ MiroFish ปิดไว้ ไม่ได้เปิดใช้)
BUY_ANYWAY = Action(
    "buy_anyway", "ซื้อ/ใช้บริการอยู่ดี", Channel.OFFLINE_ACT, exposure=0.3,
    # ได้ของสมใจนิดหน่อย (1.2) และไม่มีใครรู้ว่าเราซื้อ (0.3)
    # ค่า satisfaction ต่ำ ทำให้คนที่ "ไม่ได้เดือดร้อนอะไร" เลือกตัวนี้
    # ส่วนคนที่โกรธจัดจะไปเลือกตัวที่ระบายได้มากกว่า — ตรงกับความจริง
    expressive_value=1.2, min_drive=0.0,
    is_expression=False, deference_weight=0.0,
    description="ซื้อหรือใช้บริการต่อ ทั้งที่อาจวิจารณ์อยู่ในที่สาธารณะ "
                "— ไม่มีใครรู้ จึงเป็นด้านตรงข้ามของ 'แบน' ที่วัดไม่ได้จากโซเชียล",
)
SHOW_OFF = Action(
    "show_off", "ซื้อแล้วโพสต์อวด", Channel.PUBLIC_ONLINE, exposure=4.0,
    expressive_value=3.4, requires="social_media", min_drive=0.25,
    deference_weight=0.6, stance_direction="support",
    description="ประกาศจุดยืนฝั่งสนับสนุนด้วยการอวดว่าได้มาแล้ว "
                "เสี่ยงโดนทัวร์ลงถ้ากระแสสังคมกำลังต้าน",
)
DEFEND_PUBLIC = Action(
    "defend_public", "ออกมาปกป้อง/แย้งกระแส", Channel.PUBLIC_ONLINE, exposure=4.5,
    expressive_value=3.8, requires="social_media", min_drive=0.4,
    # สวนกระแสสังคมต้องใช้ความกล้ามากกว่าไหลตามกระแส จึงถูกความเกรงใจกดแรงกว่า
    deference_weight=1.1, stance_direction="support",
    description="เถียงแทนฝ่ายที่ถูกวิจารณ์ ต้นทุนทางสังคมสูงเพราะสวนกระแส",
)

# ── ไม่แสดงออก ──
SILENT_SHIFT = Action(
    "silent_shift", "เงียบ (ความเห็นเปลี่ยนในใจ)", Channel.INTERNAL, exposure=0.0,
    min_drive=0.0, is_expression=False, deference_weight=0.0,
    description="สำคัญที่สุดและถูกมองข้ามบ่อยที่สุด — คนส่วนใหญ่อยู่ตรงนี้ "
                "ความเห็นเปลี่ยนแล้วแต่ไม่แสดงออก และจะไปโผล่ที่คูหาเลือกตั้งแทน",
)


ALL_ACTIONS: List[Action] = [
    POST_PUBLIC, SHARE_PUBLIC, EVASIVE_POST, SHOW_OFF, DEFEND_PUBLIC,
    SHARE_LINE,
    TALK_FAMILY, TALK_WORK, CONSULT_LEADER,
    JOIN_PROTEST, SIGN_PETITION, COMPLAIN_OFFICIAL,
    BOYCOTT, BUY_ANYWAY, STOCKPILE, WITHDRAW_MONEY,
    SILENT_SHIFT,
]

BY_KEY = {a.key: a for a in ALL_ACTIONS}

# จุดยืนที่ยอมรับ — normalize ชื่อจาก LLM ที่อาจตอบได้หลายแบบ
_STANCE_ALIASES = {
    "support": "support", "supportive": "support", "เห็นด้วย": "support",
    "oppose": "oppose", "opposing": "oppose", "opposed": "oppose", "ไม่เห็นด้วย": "oppose",
    "neutral": "neutral", "เป็นกลาง": "neutral",
}


def normalize_stance(stance: Optional[str]) -> Optional[str]:
    """แปลงคำตอบ stance ให้เป็นค่ามาตรฐาน — คืน None ถ้าไม่รู้จัก"""
    if not stance:
        return None
    return _STANCE_ALIASES.get(str(stance).strip().lower())


def allowed_for_stance(action: Action, stance: Optional[str]) -> bool:
    """action นี้สมเหตุสมผลกับจุดยืนนี้มั้ย

    ยังไม่รู้จุดยืน (None) หรือเป็นกลาง -> อนุญาตเฉพาะ action ที่เป็น "any"
    เพราะคนที่ยังไม่มีจุดยืนไม่ควรไปม็อบหรือออกมาปกป้องใคร
    """
    if action.stance_direction == "any":
        return True
    return stance == action.stance_direction


def get(key: str) -> Optional[Action]:
    return BY_KEY.get(key)
