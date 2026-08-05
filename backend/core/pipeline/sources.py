"""
ทะเบียนแหล่งข้อมูลและสิทธิ์การใช้ (Phase 3.2 / O2)

ทำไมเรื่องนี้ต้องเป็น "โค้ด" ไม่ใช่ "ตารางในเอกสาร":
  ข้อจำกัดที่อยู่ในเอกสารจะถูกลืมตอนเขียน collector ตัวที่สาม
  ส่วนข้อจำกัดที่อยู่ในโค้ดจะหยุด pipeline ให้เอง

**หลักการ fail-closed**: โดเมนที่ยังไม่ได้ขึ้นทะเบียน = เก็บไม่ได้
เพราะการเผลอเก็บแล้วมาลบทีหลังแก้ปัญหาทางกฎหมายไม่ได้

── สิ่งที่ตรวจแล้วจริงเมื่อ 2026-08-01 ──

`nidapoll.nida.ac.th/robots.txt`:
    User-agent: *
    Content-Signal: search=yes, ai-train=no, use=reference
    Allow: /
    (แต่ Disallow: / สำหรับ ClaudeBot, GPTBot, CCBot, Google-Extended,
     Bytespider, Amazonbot, Applebot-Extended, meta-externalagent)

  แปลว่า **ตัวเลขโพลใช้เป็นเกณฑ์เทียบผลได้ (reference) แต่ใช้เทรนโมเดลไม่ได้**
  และการไล่เก็บอัตโนมัติไม่เหมาะสม -> ขึ้นทะเบียนเป็น `manual_entry`
  คือให้คนคัดตัวเลขมาใส่พร้อมลิงก์อ้างอิง ซึ่งพอเพียงอยู่แล้วเพราะ
  โพลหนึ่งรอบมีตัวเลขไม่กี่สิบตัว (ทดลองดึงจริงได้ HTTP 403 ด้วย)

`nationthailand.com/robots.txt`: มาตรฐาน ห้ามแค่ `/search` และไฟล์ `.php/.htm`
  เนื้อข่าวเก็บได้
"""
import logging
from dataclasses import dataclass, field
from typing import Dict, FrozenSet, Optional
from urllib.parse import urlparse

logger = logging.getLogger("mirofish.pipeline.sources")

# วันที่ตรวจ robots.txt ครั้งล่าสุด — **ต้องตรวจซ้ำก่อนเก็บข้อมูลรอบใหญ่**
# เพราะเว็บเปลี่ยนเงื่อนไขได้ตลอด และการอ้างว่า "ตอนนั้นเก็บได้" ต้องมีวันที่กำกับ
ROBOTS_CHECKED = "2026-08-01"


class SourceNotAllowed(PermissionError):
    """แหล่งนี้เก็บไม่ได้ หรือเก็บได้แต่ใช้แบบที่ขอไม่ได้"""


# วิธีใช้ข้อมูล — แยกให้ชัดเพราะแหล่งเดียวกันอนุญาตไม่เท่ากัน
USE_REFERENCE = "reference"   # อ้างอิง/เทียบผล เช่น เอาตัวเลขโพลมาวัด correspondence
USE_ANALYSIS = "analysis"     # วิเคราะห์เชิงสถิติ นับความถี่ ดูการกระจาย
USE_TRAIN = "train"           # เทรน/fine-tune โมเดล หรือใช้เป็น few-shot example


@dataclass(frozen=True)
class SourcePolicy:
    """เงื่อนไขการใช้ของแหล่งหนึ่ง"""

    domain: str
    license: str
    source_type: str
    allowed_uses: FrozenSet[str]
    crawl_allowed: bool = True
    manual_entry_only: bool = False
    min_delay_seconds: float = 2.0
    robots_checked: str = ROBOTS_CHECKED
    notes: str = ""
    extra: Dict[str, str] = field(default_factory=dict)

    def allows(self, use: str) -> bool:
        return use in self.allowed_uses


# ── ทะเบียน ──
# เพิ่มโดเมนใหม่ได้ **ก็ต่อเมื่ออ่าน robots.txt และ ToS ของมันแล้วเท่านั้น**
# และต้องเขียน notes ว่าอ่านแล้วเจออะไร

SOURCE_REGISTRY: Dict[str, SourcePolicy] = {
    "nidapoll.nida.ac.th": SourcePolicy(
        domain="nidapoll.nida.ac.th",
        license="research-only",
        source_type="poll",
        # ai-train=no จึงตัด USE_TRAIN ออก
        allowed_uses=frozenset({USE_REFERENCE, USE_ANALYSIS}),
        crawl_allowed=False,
        manual_entry_only=True,
        notes=(
            "Content-Signal: ai-train=no, use=reference. "
            "บล็อก ClaudeBot/GPTBot/CCBot/Google-Extended ฯลฯ. "
            "ดึงตรงได้ HTTP 403. ใช้เป็นเกณฑ์เทียบ (Phase 7) เท่านั้น "
            "และต้องกรอกมือพร้อมลิงก์อ้างอิงทุกตัวเลข"
        ),
    ),
    "www.nationthailand.com": SourcePolicy(
        domain="www.nationthailand.com",
        license="public-web",
        source_type="news",
        allowed_uses=frozenset({USE_REFERENCE, USE_ANALYSIS}),
        crawl_allowed=True,
        min_delay_seconds=3.0,
        notes="robots.txt มาตรฐาน ห้ามแค่ /search และ *.php/*.htm",
    ),
}


def _domain_of(url: str) -> str:
    return (urlparse(url).netloc or "").lower()


def get_policy(url: str) -> Optional[SourcePolicy]:
    return SOURCE_REGISTRY.get(_domain_of(url))


def assert_collectable(url: str) -> SourcePolicy:
    """ตรวจก่อนยิง request — โดเมนที่ไม่รู้จักต้องหยุด ไม่ใช่ลองดูก่อน"""
    domain = _domain_of(url)
    policy = SOURCE_REGISTRY.get(domain)

    if policy is None:
        raise SourceNotAllowed(
            f"โดเมน {domain!r} ยังไม่ได้ขึ้นทะเบียน — "
            f"ต้องอ่าน robots.txt/ToS แล้วเพิ่มลง SOURCE_REGISTRY ก่อน "
            f"(เก็บก่อนแล้วมาลบทีหลังแก้ปัญหาทางกฎหมายไม่ได้)"
        )

    if policy.manual_entry_only:
        raise SourceNotAllowed(
            f"{domain} ขึ้นทะเบียนเป็น manual_entry_only — {policy.notes}"
        )

    if not policy.crawl_allowed:
        raise SourceNotAllowed(f"{domain} ไม่อนุญาตให้เก็บอัตโนมัติ — {policy.notes}")

    return policy


def assert_use_allowed(url: str, use: str) -> SourcePolicy:
    """ตรวจก่อน**ใช้**ข้อมูล ไม่ใช่แค่ก่อนเก็บ

    แยกจาก `assert_collectable` เพราะแหล่งที่เก็บได้ ไม่ได้แปลว่าเอาไปทำอะไรก็ได้
    เคสจริง: ตัวเลขนิด้าโพลเอามาเทียบผลได้ แต่เอาไปเทรนโมเดลไม่ได้
    """
    policy = SOURCE_REGISTRY.get(_domain_of(url))
    if policy is None:
        raise SourceNotAllowed(f"โดเมน {_domain_of(url)!r} ยังไม่ได้ขึ้นทะเบียน")
    if not policy.allows(use):
        raise SourceNotAllowed(
            f"{policy.domain} ไม่อนุญาตการใช้แบบ {use!r} "
            f"(อนุญาต: {sorted(policy.allowed_uses)}) — {policy.notes}"
        )
    return policy


def registry_report() -> str:
    """ตารางสรุปไว้แปะในรายงาน/ภาคผนวก"""
    lines = [
        f"ตรวจ robots.txt ครั้งล่าสุด: {ROBOTS_CHECKED}",
        "",
        f"{'โดเมน':<32} {'ชนิด':<8} {'เก็บอัตโนมัติ':<14} {'ใช้ได้':<24} สัญญาอนุญาต",
        "-" * 100,
    ]
    for p in sorted(SOURCE_REGISTRY.values(), key=lambda x: x.domain):
        crawl = "ได้" if p.crawl_allowed and not p.manual_entry_only else "ไม่ได้ (กรอกมือ)"
        lines.append(
            f"{p.domain:<32} {p.source_type:<8} {crawl:<14} "
            f"{','.join(sorted(p.allowed_uses)):<24} {p.license}"
        )
    return "\n".join(lines)
