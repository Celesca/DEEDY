"""
Provenance — ที่มาของข้อความทุกชิ้น (Phase 3.3 / O2)

หลักการเดียวที่ห้ามยืดหยุ่น:
    **ไม่มีที่มา = ไม่รับเข้าคลัง**

เหตุผลไม่ใช่แค่ความเรียบร้อย แต่เพราะ:
  1. O4 ต้องวัด "content correspondence" คือเทียบข้อความที่ agent เขียนกับข้อความจริง
     ถ้าย้อนไม่ได้ว่าข้อความจริงมาจากไหน ก็อ้างอิงในรายงานไม่ได้
  2. Temporal cutoff (Phase 7.1) ต้องรู้ `published_at` ที่เชื่อถือได้
     ไม่งั้นกัน leakage ไม่ได้เลย
  3. PDPA (D5) ต้องรู้ว่าข้อมูลชิ้นไหนมาจากแหล่งไหน เผื่อต้องลบย้อนหลัง
  4. ต้องรู้ว่าเก็บด้วยโค้ดเวอร์ชันไหน เพราะ collector ที่แก้แล้วอาจได้ผลต่างกัน

`content_hash` ใช้กันเก็บซ้ำ — คิดจากข้อความที่ normalize ช่องว่างแล้ว
เพื่อให้ข่าวชิ้นเดียวกันที่ต่างกันแค่การจัดหน้า ถือเป็นชิ้นเดียวกัน
"""
import hashlib
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

# เวอร์ชันของตัวเก็บข้อมูล — **ต้องเพิ่มเลขทุกครั้งที่แก้ตรรกะการเก็บ/แปลง**
# ไม่งั้นจะแยกไม่ออกว่าข้อมูลสองชุดที่ต่างกันเป็นเพราะแหล่งเปลี่ยนหรือโค้ดเปลี่ยน
COLLECTOR_VERSION = "0.1.0"

_REQUIRED = ("source_url", "publisher", "fetched_at", "collector", "license")

# สัญญาอนุญาตที่ยอมรับได้ — ต้องระบุชัด ห้ามเดา
KNOWN_LICENSES = {
    "public-web",       # หน้าเว็บสาธารณะ เก็บได้ตาม robots.txt/ToS ของแหล่งนั้น
    "cc-by",
    "cc-by-sa",
    "cc0",
    "gov-open-data",    # ข้อมูลเปิดภาครัฐ
    "api-tos",          # ได้มาผ่าน API อย่างเป็นทางการ อยู่ใต้ ToS ของผู้ให้บริการ
    "research-only",    # ได้รับอนุญาตเฉพาะการวิจัย ห้ามเผยแพร่ต่อ
}


class ProvenanceError(ValueError):
    """ที่มาไม่ครบหรือไม่ถูกต้อง — ต้องทำให้ pipeline หยุด ไม่ใช่เตือนแล้วปล่อยผ่าน"""


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def compute_content_hash(text: str) -> str:
    """แฮชของเนื้อหาสำหรับกันเก็บซ้ำ

    ยุบช่องว่างก่อน เพื่อให้ข่าวชิ้นเดียวกันที่จัดหน้าต่างกันได้แฮชเดียวกัน
    แต่ไม่แตะอักขระไทย เพราะการ normalize สระ/วรรณยุกต์เป็นคนละเรื่อง
    (ถ้ายุบตรงนั้นด้วย ข้อความที่สะกดต่างกันจริงจะกลายเป็นชิ้นเดียวกัน)
    """
    collapsed = " ".join((text or "").split())
    return hashlib.sha256(collapsed.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class Provenance:
    """ที่มาของข้อความหนึ่งชิ้น

    `published_at` เป็น Optional เพราะบางแหล่ง (เว็บบอร์ดเก่า) ไม่บอกจริง ๆ
    แต่ **ชิ้นที่ไม่มี `published_at` จะใช้ใน Phase 7 ไม่ได้** เพราะกัน leakage ไม่ได้
    จึงต้องแยกออกได้ด้วย `usable_for_temporal_cutoff`
    """

    source_url: str
    publisher: str
    license: str
    collector: str
    fetched_at: str = field(default_factory=_utcnow)
    published_at: Optional[str] = None
    collector_version: str = COLLECTOR_VERSION
    source_type: str = "unknown"       # news / forum / social / gov / other
    author_ref: Optional[str] = None   # ตัวอ้างอิงแบบไม่ระบุตัวตน ห้ามเก็บชื่อจริง (D5)
    extra: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        missing = [f for f in _REQUIRED if not getattr(self, f, None)]
        if missing:
            raise ProvenanceError(f"ที่มาไม่ครบ ขาด: {', '.join(missing)}")

        if not re.match(r"^https?://", self.source_url):
            raise ProvenanceError(f"source_url ต้องเป็น http(s): {self.source_url!r}")

        if self.license not in KNOWN_LICENSES:
            raise ProvenanceError(
                f"license {self.license!r} ไม่อยู่ในรายการที่ยอมรับ — "
                f"ต้องตัดสินใจเรื่องสิทธิ์ก่อนเก็บ ไม่ใช่หลังเก็บ "
                f"(ที่ยอมรับ: {sorted(KNOWN_LICENSES)})"
            )

        for fname in ("fetched_at", "published_at"):
            v = getattr(self, fname)
            if v is not None:
                try:
                    datetime.fromisoformat(v)
                except (TypeError, ValueError) as e:
                    raise ProvenanceError(f"{fname} ไม่ใช่ ISO-8601: {v!r}") from e

    @property
    def usable_for_temporal_cutoff(self) -> bool:
        """ใช้ใน Phase 7 ได้มั้ย — ต้องรู้วันที่เผยแพร่จริงเท่านั้น"""
        return self.published_at is not None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Provenance":
        known = {f for f in cls.__dataclass_fields__}  # noqa: SLF001
        return cls(**{k: v for k, v in d.items() if k in known})


@dataclass
class Document:
    """ข้อความหนึ่งชิ้นในคลัง

    `raw_text` คือของดิบ **ห้ามแก้** — มุมมองอื่น ๆ (ตัดคำ/normalize/ปีไทย)
    ไปอยู่ใน `views` แทน ดู `views.py` ว่าทำไมถึงห้ามเขียนทับ
    """

    raw_text: str
    provenance: Provenance
    doc_id: str = ""
    content_hash: str = ""
    annotations: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.raw_text or not self.raw_text.strip():
            raise ProvenanceError("raw_text ว่าง")
        if not self.content_hash:
            self.content_hash = compute_content_hash(self.raw_text)
        if not self.doc_id:
            self.doc_id = self.content_hash[:16]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "doc_id": self.doc_id,
            "content_hash": self.content_hash,
            "raw_text": self.raw_text,
            "provenance": self.provenance.to_dict(),
            "annotations": self.annotations,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Document":
        return cls(
            raw_text=d["raw_text"],
            provenance=Provenance.from_dict(d["provenance"]),
            doc_id=d.get("doc_id", ""),
            content_hash=d.get("content_hash", ""),
            annotations=d.get("annotations", {}) or {},
        )


def dedupe(documents: List[Document]) -> List[Document]:
    """ตัดชิ้นซ้ำโดยดูจาก content_hash คงลำดับเดิมไว้

    เก็บชิ้น**แรก**ที่เจอ เพราะปกติคือชิ้นที่เก็บมาก่อน (ใกล้เวลาเผยแพร่กว่า)
    """
    seen: set = set()
    out: List[Document] = []
    for doc in documents:
        if doc.content_hash in seen:
            continue
        seen.add(doc.content_hash)
        out.append(doc)
    return out
