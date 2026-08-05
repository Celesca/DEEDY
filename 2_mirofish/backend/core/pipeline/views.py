"""
Thai-aware text views (Phase 3.4 / O2)

objective ใช้คำว่า *views* เป็นพหูพจน์ด้วยเหตุผล — ข้อความไทยหนึ่งชิ้นต้องมองได้
หลายมุมพร้อมกัน และ **ห้ามยุบเหลือมุมเดียว**

ทำไมถึงไม่ใช้ `app/services/thai_nlp_processor.py` ตรง ๆ (ทั้งที่มีอยู่แล้ว):

  1. `convert_be_to_ce()` ของเดิม **เขียนทับข้อความ** โดยแทนเลข 4 หลักทุกตัวใน
     ช่วง 2400-2600 ด้วย ค่า-543 วัดจริงแล้วได้:
         "ราคา 2500 บาท"      -> "ราคา 1957 บาท"
         "เงินเดือน 2450 บาท"  -> "เงินเดือน 1907 บาท"
         "บ้านเลขที่ 2555"     -> "บ้านเลขที่ 2012"
     แล้วผลที่เพี้ยนนี้ถูกส่งต่อเข้า tokenizer และ NER ทั้งอย่างนั้น
     สำหรับคลังข้อมูลที่ต้องอ้างอิงได้ นี่คือการทำลายหลักฐาน

  2. `tag_expressive_spellings()` เรียก `pythainlp.spell.correct()` ทีละคำ
     ซึ่งเป็นการค้นระยะแก้ไขบนพจนานุกรม — ช้าเกินกว่าจะรันทั้งคลัง

  3. คืน `processed_text` ก้อนเดียว ทำให้ย้อนกลับไปหาตำแหน่งในของดิบไม่ได้

ที่นี่จึงเปลี่ยนเป็น: **ของดิบไม่เปลี่ยน + ปีไทยเป็นคำอธิบายที่มีตำแหน่งกำกับ**
ใครอยากได้ข้อความที่แปลงปีแล้วค่อยเรียก `text_with_ce_years()` เอง
โดยรู้ตัวว่ากำลังแก้ข้อความอยู่
"""
import logging
import re
from dataclasses import dataclass, field
from functools import cached_property
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("mirofish.pipeline.views")

_THAI_CHARS = re.compile(r"[฀-๿]")

# ── การตรวจปีพุทธศักราช ──
# ตัวเลข 4 หลักช่วง 2400-2600 เป็นได้ทั้งปี พ.ศ. ราคา บ้านเลขที่ หรือจำนวนคน
# จึงต้องดู "บริบทรอบข้าง" ไม่ใช่ดูแค่ตัวเลข

_BE_YEAR = re.compile(r"(?<!\d)(2[3-6]\d{2})(?!\d)")

# คำที่อยู่ "ก่อน" ตัวเลขแล้วบ่งชี้ว่าเป็นปี
_YEAR_BEFORE = re.compile(
    r"(?:พ\s*\.?\s*ศ\s*\.?|ปี|เมื่อปี|ตั้งแต่ปี|ในปี|ช่วงปี|ปีที่|ค\.ศ\.)\s*$"
)
# คำที่ตาม "หลัง" ตัวเลขแล้วบ่งชี้ว่า *ไม่ใช่* ปี (เป็นหน่วยนับ)
_UNIT_AFTER = re.compile(
    r"^\s*(?:บาท|คน|ครั้ง|ชิ้น|อัน|เมตร|กม\.|กิโล|ล้าน|แสน|หมื่น|ตัว|หลัง|คัน|"
    r"เครื่อง|ที่นั่ง|ราย|แห่ง|ห้อง|วัน|เดือน)"
)
# คำก่อนหน้าที่บ่งชี้ว่าไม่ใช่ปี
_NONYEAR_BEFORE = re.compile(
    r"(?:ราคา|เลขที่|จำนวน|เงินเดือน|ค่า|ยอด|รวม|ประมาณ|กว่า|เพียง|ห้อง|ชั้น)\s*$"
)

BE_CE_OFFSET = 543


@dataclass(frozen=True)
class YearMention:
    """ตัวเลขที่อาจเป็นปี พ.ศ. พร้อมตำแหน่งในข้อความดิบ"""

    start: int
    end: int
    raw: str
    be_year: int
    ce_year: int
    confidence: float  # 0-1
    reason: str

    @property
    def is_confident(self) -> bool:
        return self.confidence >= 0.6


def detect_be_years(text: str) -> List[YearMention]:
    """หาตัวเลขที่น่าจะเป็นปี พ.ศ. โดย **ไม่แก้ข้อความ**

    ให้คะแนนความมั่นใจจากบริบท แทนที่จะแปลงทุกตัวเลขทิ้ง
    """
    out: List[YearMention] = []
    for m in _BE_YEAR.finditer(text or ""):
        be = int(m.group(1))
        before = text[max(0, m.start() - 12): m.start()]
        after = text[m.end(): m.end() + 12]

        confidence, reason = 0.35, "เลข 4 หลักในช่วงปี พ.ศ. แต่ไม่มีบริบทบ่งชี้"

        if _YEAR_BEFORE.search(before):
            confidence, reason = 0.95, "มีคำว่า ปี/พ.ศ. นำหน้า"
        elif _NONYEAR_BEFORE.search(before):
            confidence, reason = 0.05, "มีคำบ่งชี้จำนวน/ราคานำหน้า"

        if _UNIT_AFTER.match(after):
            confidence = min(confidence, 0.05)
            reason = "มีหน่วยนับตามหลัง จึงไม่ใช่ปี"

        out.append(YearMention(
            start=m.start(), end=m.end(), raw=m.group(1),
            be_year=be, ce_year=be - BE_CE_OFFSET,
            confidence=confidence, reason=reason,
        ))
    return out


def text_with_ce_years(text: str, min_confidence: float = 0.6) -> str:
    """คืนข้อความที่แปลงเฉพาะตัวที่มั่นใจว่าเป็นปีจริง

    เป็นฟังก์ชันแยก **โดยตั้งใจ** — การแก้ข้อความต้องเป็นสิ่งที่ผู้เรียกเลือกทำเอง
    ไม่ใช่ผลข้างเคียงของการประมวลผลทั่วไป
    """
    mentions = [m for m in detect_be_years(text) if m.confidence >= min_confidence]
    if not mentions:
        return text
    out, last = [], 0
    for m in mentions:
        out.append(text[last:m.start])
        out.append(str(m.ce_year))
        last = m.end
    out.append(text[last:])
    return "".join(out)


# ── ลักษณะภาษาไทยที่บ่งบอก "ระดับภาษา" (O3: Thai linguistic attributes) ──

_REPEATED_CHAR = re.compile(r"([฀-๿])\1{2,}")     # มากกก
_REPEAT_MARK = re.compile(r"ๆ")                              # ไม้ยมก
_LAUGH = re.compile(r"5{3,}")                                # 5555
_POLITE_PARTICLE = re.compile(r"(?:ครับ|ค่ะ|คะ|ครัช|คร้าบ|จ้า|จ้ะ|นะคะ|นะครับ)")
_FORMAL_MARKER = re.compile(
    r"(?:ดังกล่าว|ทั้งนี้|อย่างไรก็ตาม|เนื่องจาก|ตามที่|จึงเรียนมาเพื่อ|"
    r"ข้าพเจ้า|ประกาศ|ระเบียบ|พระราชบัญญัติ|มาตรา)"
)
_URL = re.compile(r"https?://\S+")
_HASHTAG = re.compile(r"#\S+")


@dataclass
class InformalityProfile:
    """สัญญาณว่าข้อความเป็นทางการแค่ไหน

    ใช้สองที่:
      - O4 content correspondence — ข้อความที่ agent เขียนต้องมีการกระจาย
        ระดับภาษาใกล้เคียงของจริง ไม่ใช่ทางการหมดหรือกันเองหมด
      - Phase 4 — persona ที่การศึกษาต่างกันควรเขียนคนละระดับ
    """

    repeated_chars: int = 0
    repeat_marks: int = 0
    laughs: int = 0
    polite_particles: int = 0
    formal_markers: int = 0
    hashtags: int = 0
    urls: int = 0

    @property
    def informality_score(self) -> float:
        """0 = ทางการมาก, 1 = กันเองมาก

        เป็น heuristic ไม่ใช่ของที่วัดมา — ใช้เทียบการกระจายระหว่างสองคลังได้
        แต่**อย่าใช้ตัดสินข้อความเดี่ยว ๆ**
        """
        informal = (
            self.repeated_chars * 2 + self.laughs * 2
            + self.polite_particles + self.hashtags
        )
        formal = self.formal_markers * 2
        total = informal + formal
        if total == 0:
            return 0.5
        return round(informal / total, 3)


def profile_informality(text: str) -> InformalityProfile:
    t = text or ""
    return InformalityProfile(
        repeated_chars=len(_REPEATED_CHAR.findall(t)),
        repeat_marks=len(_REPEAT_MARK.findall(t)),
        laughs=len(_LAUGH.findall(t)),
        polite_particles=len(_POLITE_PARTICLE.findall(t)),
        formal_markers=len(_FORMAL_MARKER.findall(t)),
        hashtags=len(_HASHTAG.findall(t)),
        urls=len(_URL.findall(t)),
    )


# ── ตัวห่อ PyThaiNLP (โหลดตอนใช้จริง ไม่มีก็ยังทำงานได้) ──

_pythainlp: Dict[str, Any] = {}


def _load(name: str):
    """โหลดฟังก์ชันของ pythainlp แบบ lazy และจำผลไว้

    ถ้าไม่มี pythainlp จะคืน None แล้วให้ผู้เรียก fallback
    (เหมือน `core/embeddings.py` — ไม่ควรพังทั้งระบบเพราะ optional dep)
    """
    if name in _pythainlp:
        return _pythainlp[name]
    fn = None
    try:
        if name == "normalize":
            from pythainlp.util import normalize as fn  # type: ignore
        elif name == "word_tokenize":
            from pythainlp.tokenize import word_tokenize as fn  # type: ignore
        elif name == "sent_tokenize":
            from pythainlp.tokenize import sent_tokenize as fn  # type: ignore
        elif name == "pos_tag":
            from pythainlp.tag import pos_tag as fn  # type: ignore
    except ImportError:
        logger.warning("ไม่พบ pythainlp — view %r จะใช้วิธีสำรอง", name)
    _pythainlp[name] = fn
    return fn


@dataclass
class TextViews:
    """หลายมุมมองของข้อความชิ้นเดียว

    `raw` เป็น source of truth เสมอ — ทุก view คำนวณจากมันและ **ไม่แทนที่มัน**
    คำนวณแบบ lazy เพราะคลังหลักหมื่นชิ้นไม่ควรจ่ายค่า POS tagging ถ้าไม่ได้ใช้
    """

    raw: str
    _extra: Dict[str, Any] = field(default_factory=dict, repr=False)

    @cached_property
    def normalized(self) -> str:
        """สระซ้ำ/วรรณยุกต์ผิดตำแหน่ง/ช่องว่างเกิน — แต่ยังอ่านเป็นข้อความเดิม"""
        collapsed = " ".join((self.raw or "").split())
        fn = _load("normalize")
        if fn is None:
            return collapsed
        try:
            return fn(collapsed)
        except Exception:  # noqa: BLE001
            return collapsed

    @cached_property
    def sentences(self) -> List[str]:
        fn = _load("sent_tokenize")
        if fn is None:
            return [s for s in re.split(r"[\n\.!?]+", self.normalized) if s.strip()]
        try:
            return [s for s in fn(self.normalized, engine="crfcut") if s.strip()]
        except Exception:  # noqa: BLE001
            return [self.normalized]

    @cached_property
    def tokens(self) -> List[str]:
        """ตัดคำ — ภาษาไทยไม่มีช่องว่างระหว่างคำ จึงเป็น view ที่ขาดไม่ได้"""
        fn = _load("word_tokenize")
        if fn is None:
            return self.normalized.split()
        try:
            return [t for t in fn(self.normalized, engine="newmm") if t.strip()]
        except Exception:  # noqa: BLE001
            return self.normalized.split()

    @cached_property
    def pos(self) -> List[Tuple[str, str]]:
        fn = _load("pos_tag")
        if fn is None:
            return [(t, "UNK") for t in self.tokens]
        try:
            return fn(self.tokens, corpus="orchid_ud")
        except Exception:  # noqa: BLE001
            return [(t, "UNK") for t in self.tokens]

    @cached_property
    def year_mentions(self) -> List[YearMention]:
        return detect_be_years(self.raw)

    @cached_property
    def informality(self) -> InformalityProfile:
        return profile_informality(self.raw)

    @cached_property
    def thai_ratio(self) -> float:
        """สัดส่วนอักขระไทย — ใช้กรองข้อความที่ไม่ใช่ไทยออกจากคลัง"""
        if not self.raw:
            return 0.0
        return round(len(_THAI_CHARS.findall(self.raw)) / len(self.raw), 3)

    def to_dict(self, heavy: bool = False) -> Dict[str, Any]:
        """`heavy=False` ข้าม POS ซึ่งเป็นตัวที่แพงที่สุด"""
        d: Dict[str, Any] = {
            "normalized": self.normalized,
            "tokens": self.tokens,
            "sentences": self.sentences,
            "thai_ratio": self.thai_ratio,
            "informality": {
                **vars(self.informality),
                "score": self.informality.informality_score,
            },
            "year_mentions": [vars(m) for m in self.year_mentions],
        }
        if heavy:
            d["pos"] = self.pos
        return d
