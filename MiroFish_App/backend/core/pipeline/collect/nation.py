"""
Nation Thailand Collector (Phase 3.2 / O2)

หมายเหตุ:
  - robots.txt ตรวจแล้ว 2026-08-01 ห้ามแค่ /search และ *.php/*.htm
  - min_delay = 3.0s ตามที่ขึ้นทะเบียนใน sources.py
  - ตอนนี้ยังเป็น **mock** อยู่ — ต้องแกะ DOM จริงก่อนใช้งานจริง
    เพราะ Nation เปลี่ยน layout บ่อย อาจต้องเขียน fallback หลาย selector
"""
import logging
import time
from typing import Generator, Optional

from .base import BaseCollector
from ..provenance import Document

logger = logging.getLogger("mirofish.pipeline.collect.nation")


class NationCollector(BaseCollector):
    def __init__(self) -> None:
        super().__init__(base_url="https://www.nationthailand.com")

    def _fetch_article(self, url: str) -> Optional[dict]:
        """ดึงเนื้อข่าวจาก URL จริง — ยังเป็น stub

        TODO: ติดตั้ง requests + beautifulsoup4 แล้วเปิดโค้ดจริง
        โครงสร้างที่ต้องแกะ:
          - เนื้อหา: div.article-content หรือ article > p
          - เวลา: <time datetime="...">
          - ผู้เขียน: span.author-name
        """
        # try:
        #     import requests
        #     from bs4 import BeautifulSoup
        #     resp = requests.get(url, timeout=15)
        #     resp.raise_for_status()
        #     soup = BeautifulSoup(resp.content, "html.parser")
        #     content_el = soup.select_one("div.article-content") or soup.select_one("article")
        #     time_el = soup.select_one("time[datetime]")
        #     return {
        #         "raw_text": content_el.get_text(separator="\n", strip=True) if content_el else "",
        #         "published_at": time_el["datetime"] if time_el else None,
        #     }
        # except Exception as e:
        #     logger.warning("Failed to fetch %s: %s", url, e)
        #     return None
        return None

    def fetch(self, query: str, limit: int = 10) -> Generator[Document, None, None]:
        delay = self.policy.min_delay_seconds
        logger.info("Fetching '%s' from %s (delay=%.1fs, limit=%d)", query, self.policy.domain, delay, limit)

        # ── Mock: สร้างข้อมูลสมมติสำหรับทดสอบ pipeline ──
        # เมื่อ _fetch_article พร้อมใช้จริง ให้เปลี่ยนมาเรียกมันแทน
        mock_articles = [
            {
                "url": f"https://www.nationthailand.com/news/{40000 + i}",
                "raw_text": f"[mock] เนื้อหาข่าวเรื่อง {query} — บทความที่ {i + 1}",
                "published_at": "2026-08-08T12:00:00+07:00",
            }
            for i in range(min(limit, 5))
        ]

        for article in mock_articles:
            time.sleep(delay)
            try:
                doc = self.create_document(
                    raw_text=article["raw_text"],
                    source_url=article["url"],
                    published_at=article["published_at"],
                )
                yield doc
            except Exception:
                logger.exception("Failed to create document for %s", article["url"])
