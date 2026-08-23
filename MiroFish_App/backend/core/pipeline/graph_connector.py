"""
Graph Connector (Phase 3.6 / O2)

เชื่อมต่อ Document ที่ผ่าน pipeline แล้วเข้าสู่ Graph Builder ของ MiroFish

ทำไม import GraphBuilderService แบบ lazy:
  `core/` กับ `app/` เป็นคนละ package ที่ไม่ได้ share __init__.py
  relative import ข้าม package ทำไม่ได้ ต้อง import ตอนเรียกใช้จริง
  ซึ่งหมายความว่าตอน import module นี้มาจะไม่พัง แม้ app/ ไม่ได้ถูก install
"""
import logging
from typing import Any, Dict, List, Optional

from .provenance import Document

logger = logging.getLogger("mirofish.pipeline.graph_connector")


def format_document_for_graph(doc: Document) -> str:
    """แปลง Document เป็นข้อความพร้อม metadata header ให้ Zep สกัด entity ได้"""
    stance = doc.annotations.get("stance", "unknown")
    emotion = doc.annotations.get("emotion", "unknown")
    source = doc.provenance.publisher
    published = doc.provenance.published_at or "unknown"

    header = f"[source={source} | published={published} | stance={stance} | emotion={emotion}]"
    return f"{header}\n{doc.raw_text}"


def push_to_graph(
    documents: List[Document],
    ontology: Dict[str, Any],
    graph_name: str = "MiroFish Pipeline Graph",
    api_key: Optional[str] = None,
) -> str:
    """ส่ง Document เข้า Graph Builder — คืน task_id

    Import GraphBuilderService ตอนเรียกจริง เพราะ:
      1. core/ กับ app/ เป็นคนละ package
      2. ไม่อยากบังคับให้ pipeline ทั้งหมดต้อง install zep_cloud แค่เพื่อ import
    """
    if not documents:
        logger.warning("No documents to push to graph")
        return ""

    logger.info("Preparing %d documents for Graph Builder...", len(documents))

    # Lazy import — ดู docstring ข้างบน
    try:
        from app.services.graph_builder import GraphBuilderService
    except ImportError as e:
        logger.error(
            "Cannot import GraphBuilderService — "
            "ตรวจสอบว่า app/ อยู่ใน sys.path หรือ zep_cloud ถูก install: %s", e,
        )
        raise

    combined_text = "\n\n---\n\n".join(
        format_document_for_graph(doc) for doc in documents
    )

    builder = GraphBuilderService(api_key=api_key)
    task_id = builder.build_graph_async(
        text=combined_text,
        ontology=ontology,
        graph_name=graph_name,
        chunk_size=1000,
        chunk_overlap=100,
    )

    logger.info("Graph build task started: %s", task_id)
    return task_id
