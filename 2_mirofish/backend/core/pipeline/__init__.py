"""
Pipeline ข้อมูลไทยครบวงจร (Phase 3 / O2)

    discover -> collect -> clean -> provenance -> views -> annotate -> graph

หลักที่ยึดทั้ง pipeline:
  - **ของดิบไม่เปลี่ยน** ทุกการแปลงเป็น view หรือ annotation ที่ต่อเพิ่ม
  - **ไม่มีที่มา = ไม่รับเข้า** (ดู `provenance.py`)
  - ทุก annotation ต้องมีคะแนนความมั่นใจ ห้ามให้ป้ายแบบมั่นใจเต็มร้อยโดยไม่มีหลักฐาน
"""
from .provenance import (
    COLLECTOR_VERSION,
    Document,
    Provenance,
    ProvenanceError,
    compute_content_hash,
    dedupe,
)
from .sources import (
    SOURCE_REGISTRY,
    USE_ANALYSIS,
    USE_REFERENCE,
    USE_TRAIN,
    SourceNotAllowed,
    SourcePolicy,
    assert_collectable,
    assert_use_allowed,
    get_policy,
    registry_report,
)
from .views import (
    InformalityProfile,
    TextViews,
    YearMention,
    detect_be_years,
    profile_informality,
    text_with_ce_years,
)

__all__ = [
    "COLLECTOR_VERSION",
    "Document",
    "Provenance",
    "ProvenanceError",
    "compute_content_hash",
    "dedupe",
    "SOURCE_REGISTRY",
    "USE_ANALYSIS",
    "USE_REFERENCE",
    "USE_TRAIN",
    "SourceNotAllowed",
    "SourcePolicy",
    "assert_collectable",
    "assert_use_allowed",
    "get_policy",
    "registry_report",
    "InformalityProfile",
    "TextViews",
    "YearMention",
    "detect_be_years",
    "profile_informality",
    "text_with_ce_years",
]
