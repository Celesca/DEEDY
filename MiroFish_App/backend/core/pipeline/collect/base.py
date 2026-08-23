"""
Base Collection Adapter (Phase 3.2 / O2)

คลาสแม่ของตัวเก็บข้อมูลทุกตัว — บังคับให้:
  1. เช็คสิทธิ์ผ่าน `sources.py` ก่อนเริ่มเก็บ
  2. คืน Document ที่มี Provenance ครบถ้วน

ห้ามสร้าง collector ที่ข้าม `assert_collectable` ได้
"""
import logging
from abc import ABC, abstractmethod
from typing import Generator, Optional

from ..provenance import Document, Provenance
from ..sources import assert_collectable, SourcePolicy

logger = logging.getLogger("mirofish.pipeline.collect.base")


class BaseCollector(ABC):
    """
    คลาสแม่สำหรับตัวดึงข้อมูลทั้งหมด

    การสร้าง instance จะเช็คสิทธิ์ทันที — ถ้าโดเมนยังไม่ได้ขึ้นทะเบียน
    หรือตั้งเป็น manual_entry_only จะโยน SourceNotAllowed ให้เลย
    """

    def __init__(self, base_url: str):
        self.base_url = base_url
        self.policy: SourcePolicy = assert_collectable(self.base_url)
        logger.info(
            "Initialized collector for %s (license=%s, delay=%.1fs)",
            self.policy.domain, self.policy.license, self.policy.min_delay_seconds,
        )

    @abstractmethod
    def fetch(self, query: str, limit: int = 10) -> Generator[Document, None, None]:
        """
        ดึงข้อมูลตามคำค้นหา (query) และจำกัดจำนวน (limit)
        ต้องคืนค่าเป็น Generator ของ Document
        """

    def create_document(
        self,
        raw_text: str,
        source_url: str,
        published_at: Optional[str] = None,
        author_ref: Optional[str] = None,
    ) -> Document:
        """Helper สำหรับสร้าง Document พร้อม Provenance แบบปลอดภัย"""
        prov = Provenance(
            source_url=source_url,
            publisher=self.policy.domain,
            license=self.policy.license,
            collector=self.__class__.__name__,
            published_at=published_at,
            source_type=self.policy.source_type,
            author_ref=author_ref,
        )
        return Document(raw_text=raw_text, provenance=prov)
