"""
Scenario — บอกว่าเหตุการณ์นี้ "ทำอะไรได้บ้าง" และ "จุดยืนหมายถึงอะไร"

แก้สองปัญหาที่เจอตอนรันเคส PARAMETER ด้วยของชิ้นเดียว เพราะมันเป็นปัญหาเดียวกัน
คือ **action space กับ stance ลอยอยู่ ไม่ได้ผูกกับเหตุการณ์**

ปัญหาที่ 1 — action ไม่เข้าเรื่อง
    รันเคสร้านไอศกรีมแล้วได้ ไปม็อบ 3 / ถอนเงินธนาคาร 3 / กักตุนของ 2
    รวม 15 จาก 95 ครั้ง (16%) เพราะ `score_actions` ให้คะแนนทั้ง 17 ตัวเสมอ

    OASIS แก้ด้วย `available_actions` ที่ส่งตอนสร้าง agent แล้วแปลงเป็น
    **รายการ tool ที่ส่งให้ LLM** — action ที่ไม่อยู่ในลิสต์โมเดลมองไม่เห็นเลย
    เลือกไม่ได้ในเชิงโครงสร้าง ไม่ใช่กรองทีหลัง เราใช้แนวเดียวกัน

ปัญหาที่ 2 — `stance` ไม่มีที่อ้างอิง
    ได้ผลลัพธ์อย่าง `supportive/75` ที่โกรธ 60 แล้วไปแบนร้าน
    ซึ่งตีความไม่ได้ว่าสนับสนุนร้าน หรือสนับสนุนคนที่ด่าร้าน
    ข้อนี้ร้ายแรงที่สุดเพราะ `private_opinion` คือตัวแปรผลลัพธ์หลักของงาน

    OASIS ไม่มีปัญหานี้เพราะ **ไม่มี stance เลย** (grep แล้วไม่เจอ
    anger/emotion/stance/sentiment/fear ทั้ง package) ความเห็นอยู่ในข้อความ
    ที่ generate ออกมาเท่านั้น — ลอกไม่ได้ เพราะการมีชั้นความเห็นในใจ
    คือส่วนที่งานนี้เพิ่มเข้าไป จึงต้องนิยามให้ชัดเอง
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .actions import (
    ALL_ACTIONS,
    BOYCOTT,
    BUY_ANYWAY,
    COMPLAIN_OFFICIAL,
    CONSULT_LEADER,
    DEFEND_PUBLIC,
    EVASIVE_POST,
    JOIN_PROTEST,
    POST_PUBLIC,
    SHARE_LINE,
    SHARE_PUBLIC,
    SHOW_OFF,
    SIGN_PETITION,
    SILENT_SHIFT,
    STOCKPILE,
    TALK_FAMILY,
    TALK_WORK,
    WITHDRAW_MONEY,
    Action,
)


class ScenarioError(ValueError):
    pass


@dataclass(frozen=True)
class Scenario:
    """นิยามของเหตุการณ์หนึ่งชุด

    `subject` คือหัวใจ — เป็นตัวตอบว่า "เห็นด้วย/ไม่เห็นด้วย กับอะไร"
    ถ้าไม่มีตัวนี้ ตัวเลขการกระจายความเห็นที่ได้จะเอาไปเทียบโพลไม่ได้
    เพราะไม่รู้ว่ามันวัดอะไรอยู่
    """

    key: str
    label: str
    # อะไรคือสิ่งที่คนกำลังมีความเห็นต่อ
    subject: str
    # "เห็นด้วย" กับ "ไม่เห็นด้วย" ในบริบทนี้แปลว่าอะไร — เขียนให้คนอ่านเข้าใจ
    support_means: str
    oppose_means: str
    actions: List[Action] = field(default_factory=lambda: list(ALL_ACTIONS))
    notes: str = ""

    def __post_init__(self) -> None:
        for f in ("subject", "support_means", "oppose_means"):
            if not getattr(self, f, "").strip():
                raise ScenarioError(
                    f"scenario {self.key!r} ขาด {f} — ถ้าไม่นิยามว่าจุดยืนอ้างอิงกับอะไร "
                    f"ตัวเลขความเห็นที่ได้จะตีความไม่ได้"
                )
        if SILENT_SHIFT not in self.actions:
            # "เงียบ" ต้องเป็นตัวเลือกเสมอ ไม่งั้นบังคับให้ทุกคนต้องทำอะไรสักอย่าง
            object.__setattr__(self, "actions", list(self.actions) + [SILENT_SHIFT])

    @property
    def action_keys(self) -> List[str]:
        return [a.key for a in self.actions]

    def stance_guide(self) -> str:
        """ข้อความที่จะแทรกเข้า prompt ชั้นที่ 1"""
        return (
            f"เรื่องที่คุณกำลังมีความเห็นต่อคือ: {self.subject}\n"
            f'  - "supportive" = {self.support_means}\n'
            f'  - "opposing"   = {self.oppose_means}\n'
            f'  - "neutral"    = ยังไม่มีความเห็นชัดเจน หรือไม่รู้สึกว่าเกี่ยวกับตัวเอง'
        )


# ── ชุดสำเร็จรูป ──

_TALK = [TALK_FAMILY, TALK_WORK]
_ONLINE = [POST_PUBLIC, SHARE_PUBLIC, EVASIVE_POST, SHARE_LINE]

POLITICAL = Scenario(
    key="political",
    label="เหตุการณ์การเมือง/นโยบายรัฐ",
    subject="(ต้องระบุตอนใช้งาน)",
    support_means="เห็นด้วยกับฝ่ายรัฐ/นโยบายนี้",
    oppose_means="ไม่เห็นด้วยกับฝ่ายรัฐ/นโยบายนี้",
    actions=_ONLINE + _TALK + [
        CONSULT_LEADER, JOIN_PROTEST, SIGN_PETITION, COMPLAIN_OFFICIAL,
        BOYCOTT, DEFEND_PUBLIC,
    ],
    notes="ชุดเต็มสำหรับเรื่องที่มีความเสี่ยงทางกฎหมาย มีทั้งม็อบและช่องทางทางการ",
)

CONSUMER = Scenario(
    key="consumer",
    label="ดราม่าสินค้า/แบรนด์",
    subject="(ต้องระบุตอนใช้งาน)",
    support_means="เห็นว่าแบรนด์นี้สมเหตุสมผล/ไม่ได้ผิดอะไร",
    oppose_means="เห็นว่าแบรนด์นี้เอาเปรียบผู้บริโภคหรือไม่เหมาะสม",
    actions=_ONLINE + _TALK + [
        SHOW_OFF, DEFEND_PUBLIC,
        BOYCOTT, BUY_ANYWAY,
        COMPLAIN_OFFICIAL,  # สคบ. เป็นช่องทางจริงของผู้บริโภค
    ],
    notes=(
        "ตัดม็อบ/ลงชื่อคัดค้าน/กักตุน/ถอนเงิน ออก เพราะไม่ใช่พฤติกรรมที่คนทำ"
        "กับดราม่าแบรนด์ และเพิ่มฝั่งเข้าร่วม (ซื้ออยู่ดี/โพสต์อวด/ปกป้อง) "
        "ซึ่งเป็นด้านที่ action space เดิมไม่มีเลย"
    ),
)

DISASTER = Scenario(
    key="disaster",
    label="ภัยพิบัติ/ความปลอดภัยสาธารณะ",
    subject="(ต้องระบุตอนใช้งาน)",
    support_means="เชื่อมั่นว่าหน่วยงานรับมือได้และสถานการณ์ปลอดภัย",
    oppose_means="ไม่เชื่อมั่นในการรับมือ หรือเห็นว่ามีความบกพร่อง",
    actions=_ONLINE + _TALK + [
        CONSULT_LEADER, COMPLAIN_OFFICIAL, SIGN_PETITION,
        STOCKPILE, WITHDRAW_MONEY, BOYCOTT, DEFEND_PUBLIC,
    ],
    notes="มีพฤติกรรมตอบสนองความกลัว (กักตุน/ถอนเงิน) ซึ่งเป็นของเฉพาะกลุ่มนี้",
)

BUILTIN: Dict[str, Scenario] = {s.key: s for s in (POLITICAL, CONSUMER, DISASTER)}


def build(
    key: str,
    subject: str,
    support_means: Optional[str] = None,
    oppose_means: Optional[str] = None,
) -> Scenario:
    """หยิบชุดสำเร็จรูปมาแล้วใส่หัวข้อจริงเข้าไป"""
    base = BUILTIN.get(key)
    if base is None:
        raise ScenarioError(f"ไม่รู้จัก scenario {key!r} (มี: {sorted(BUILTIN)})")
    return Scenario(
        key=base.key,
        label=base.label,
        subject=subject,
        support_means=support_means or base.support_means,
        oppose_means=oppose_means or base.oppose_means,
        actions=list(base.actions),
        notes=base.notes,
    )
