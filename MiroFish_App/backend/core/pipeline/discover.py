"""
Topic discovery — หาหัวข้อย่อยและคีย์เวิร์ดที่เกี่ยวข้องจาก seed เริ่มต้น (Phase 3.1 / O2)

ใช้ LLM (Qwen) แตกหัวข้อใหญ่เป็นประเด็นย่อยที่กำลังถูกพูดถึง
พร้อม search query สำหรับป้อนให้ collector ไปดึงข้อมูล
"""
import logging
from dataclasses import dataclass, field
from typing import List

from ..llm import get_client, LLMError

logger = logging.getLogger("mirofish.pipeline.discover")


@dataclass
class TopicCluster:
    """กลุ่มหัวข้อที่ได้จากการขยายผลจาก seed"""

    seed: str
    subtopic_name: str
    search_queries: List[str] = field(default_factory=list)
    description: str = ""


def discover_topics(seed_keyword: str, max_topics: int = 5) -> List[TopicCluster]:
    """ใช้ LLM หาหัวข้อย่อยและ query ที่จะใช้ดึงข้อมูลจาก seed

    คืน list ว่างเปล่าถ้า LLM ล้มเหลวหรือตอบผิดรูปแบบ
    ไม่โยน exception เพราะ caller ควรทำงานต่อได้แม้ discovery ล้ม
    """
    system_prompt = (
        "คุณคือผู้เชี่ยวชาญด้านข่าวสารและการวิเคราะห์สังคมไทย "
        "หน้าที่ของคุณคือแตกหัวข้อใหญ่ออกเป็นประเด็นย่อยที่กำลังถูกพูดถึง "
        "แต่ละประเด็นต้องมีคำค้นหาภาษาไทยที่เจาะจงพอจะใช้ค้นข่าวได้"
    )

    user_prompt = (
        f'วิเคราะห์หัวข้อ: "{seed_keyword}"\n'
        f"แยกเป็นหัวข้อย่อยที่เกี่ยวข้อง ไม่เกิน {max_topics} หัวข้อ\n\n"
        "ตอบเป็น JSON เท่านั้น:\n"
        '{"topics": [{"subtopic_name": "...", "description": "...", '
        '"search_queries": ["...", "...", "..."]}]}'
    )

    client = get_client()
    try:
        response = client.complete_json(
            system=system_prompt,
            user=user_prompt,
            required_fields=["topics"],
        )
    except LLMError:
        logger.exception("Topic discovery failed for seed '%s'", seed_keyword)
        return []

    raw_topics = response.get("topics")
    if not isinstance(raw_topics, list):
        logger.warning(
            "LLM returned topics as %s instead of list — skipping",
            type(raw_topics).__name__,
        )
        return []

    clusters: List[TopicCluster] = []
    for item in raw_topics:
        if not isinstance(item, dict):
            continue
        name = item.get("subtopic_name", "")
        if not name:
            continue
        queries = item.get("search_queries", [])
        if not isinstance(queries, list):
            queries = []
        clusters.append(
            TopicCluster(
                seed=seed_keyword,
                subtopic_name=name,
                description=item.get("description", ""),
                search_queries=[q for q in queries if isinstance(q, str)],
            )
        )

    logger.info("Discovered %d subtopics for seed '%s'", len(clusters), seed_keyword)
    return clusters
