"""
Clean & Filter (Phase 3.7 / O2)

สองหน้าที่ที่ต้องแยกให้ชัด:
  1. **กรอง spam/bot** — ตัดข้อความที่ไม่มีคุณค่าออกจาก pipeline
  2. **ลบ PII** — ทำลายข้อมูลส่วนบุคคล **ก่อน** บันทึกลงคลัง (D5/PDPA)

ทำไม PII ถึงเป็นข้อยกเว้นของหลัก "ของดิบไม่เปลี่ยน" (views.py):
  กฎหมายบังคับว่าต้องทำลาย — เก็บไว้แล้วมาลบทีหลังไม่ช่วยเรื่องกฎหมาย
  เพราะ "ประมวลผลไปแล้ว" ก่อนจะลบ ดังนั้น PII ต้องหายก่อนเข้าคลัง
"""
import re
import logging
from typing import List

from .provenance import Document, compute_content_hash

logger = logging.getLogger("mirofish.pipeline.clean")

# ── Regex สำหรับ PII ไทย ──
# เบอร์มือถือ: 08x/09x/06x ตามด้วย 7-8 หลัก อาจมี - หรือ space คั่น
_PHONE = re.compile(
    r"(?<!\d)"
    r"0[689]\d"           # 08x, 09x, 06x
    r"[-\s]?\d{3}"        # -xxx หรือ xxx
    r"[-\s]?\d{4}"        # -xxxx หรือ xxxx
    r"(?!\d)"
)

# อีเมล
_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")

# บัตรประชาชนไทย: x-xxxx-xxxxx-xx-x (13 หลัก อาจมี - คั่น)
_ID_CARD = re.compile(
    r"(?<!\d)"
    r"\d[-\s]?\d{4}[-\s]?\d{5}[-\s]?\d{2}[-\s]?\d"
    r"(?!\d)"
)


def remove_pii(text: str) -> str:
    """แทนที่ข้อมูล PII ด้วย placeholder

    ใช้ placeholder ที่อ่านออกเพื่อให้รู้ว่ามีการ redact เกิดขึ้น
    ไม่ใช่แค่ลบทิ้งเงียบ ๆ เพราะข้อมูลที่หายไปอาจเปลี่ยนความหมายของประโยค
    """
    if not text:
        return text

    cleaned = _PHONE.sub("[โทรศัพท์]", text)
    cleaned = _EMAIL.sub("[อีเมล]", cleaned)
    cleaned = _ID_CARD.sub("[เลขบัตร]", cleaned)
    return cleaned


def is_spam(doc: Document) -> bool:
    """ตรวจสอบเบื้องต้นว่าข้อความน่าจะเป็นสแปมหรือไม่

    เป็น heuristic แบบ conservative — ยอมรับ false negative
    ดีกว่า false positive ที่ตัดข้อมูลดีทิ้ง
    """
    text = doc.raw_text.strip()

    # ข้อความสั้นเกินไป
    if len(text) < 10:
        return True

    # URL มากกว่าเนื้อหา (ยิงลิงก์)
    url_count = len(re.findall(r"https?://", text))
    if url_count > 3 and len(text) < 100:
        return True

    # ข้อความซ้ำ ๆ (bot copy-paste)
    words = text.split()
    if len(words) > 5:
        unique_ratio = len(set(words)) / len(words)
        if unique_ratio < 0.3:
            return True

    return False


def clean_documents(docs: List[Document]) -> List[Document]:
    """กรองสแปมและลบ PII — คืนเฉพาะ Document ที่ผ่านเกณฑ์

    content_hash จะถูก recompute หลัง redact PII
    เพราะข้อความเปลี่ยน hash เดิมจะไม่ตรงกับของจริงอีกต่อไป
    """
    cleaned: List[Document] = []
    spam_count = 0

    for doc in docs:
        if is_spam(doc):
            spam_count += 1
            continue

        # ลบ PII แล้ว recompute hash
        redacted = remove_pii(doc.raw_text)
        if redacted != doc.raw_text:
            doc.raw_text = redacted
            doc.content_hash = compute_content_hash(redacted)

        cleaned.append(doc)

    if spam_count:
        logger.info("Filtered out %d spam document(s) from %d total", spam_count, len(docs))

    return cleaned
