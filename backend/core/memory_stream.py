"""
ความจำของ agent — บันทึกสิ่งที่รับรู้ และดึงเรื่องที่เกี่ยวข้องกลับมาตอนตัดสินใจ

Phase 2 (D4, D5) แก้ครบสามข้อแล้ว:
  1. embedding เป็น multilingual (ค่าปริยายของ ChromaDB เป็นโมเดลอังกฤษ วัดแล้ว MRR 0.51
     คืนความจำชุดเดิมแทบทุกคำถาม -> เปลี่ยนเป็น multilingual-e5-small ได้ MRR 1.00)
  2. เก็บลงดิสก์ได้ (PersistentClient) ไม่ใช่หายเมื่อปิดโปรแกรม
  3. จัดอันดับด้วย relevance + recency + importance ไม่ใช่ similarity อย่างเดียว
     (`importance` ที่บันทึกไว้แต่เดิมไม่เคยถูกใช้เลย)

ทำไมไม่ใช้ Zep Cloud สำหรับชั้นนี้:
  - ต้องทำซ้ำได้ (Phase 6) แต่ Zep สร้างกราฟด้วย LLM ซึ่งไม่ deterministic
  - ต้องคุม embedding เองได้ ซึ่งเป็นตัวชี้ขาดคุณภาพภาษาไทย
  - 1000 agent x 72 รอบ = การอ่าน/เขียนความจำหลักหมื่นครั้งต่อการรันหนึ่งครั้ง
  - PDPA (D5) ข้อมูลที่มี PII ไม่ควรออกนอกเครื่อง
  Zep เหมาะกับ "ความรู้เกี่ยวกับเหตุการณ์" ที่สร้างครั้งเดียวแล้วแช่ไว้ ไม่ใช่ชั้นนี้
"""
import logging
import math
import os
import threading
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

from .embeddings import get_embedding_function, normalize_thai_text

logger = logging.getLogger("mirofish.core.memory")

# น้ำหนักการจัดอันดับ — ปรับได้ผ่าน env เพื่อทดลอง
W_RELEVANCE = float(os.environ.get("MEM_W_RELEVANCE", 1.0))
W_RECENCY = float(os.environ.get("MEM_W_RECENCY", 0.35))
W_IMPORTANCE = float(os.environ.get("MEM_W_IMPORTANCE", 0.45))

# ครึ่งชีวิตของความทรงจำ (ชั่วโมงจำลอง) — ยิ่งนานยิ่งจำได้นาน
RECENCY_HALFLIFE_HOURS = float(os.environ.get("MEM_RECENCY_HALFLIFE", 72.0))

# ── การให้คะแนน relevance ของภาษาไทย ──
#
# ปัญหาที่วัดเจอจริง: multilingual-e5-small ให้ cosine ของประโยคไทยกระจุกอยู่
# แถบแคบมาก (0.77-0.88) แม้แต่ประโยคที่ไม่เกี่ยวกันเลยก็ยังได้ ~0.78
# แปลว่าค่าดิบใช้ตัดสินตรง ๆ ไม่ได้ ต้องดูว่า "ในชุดผู้สมัครนี้ ห่างกันแค่ไหน"
#
# เคยลองสองแบบแล้วพังทั้งคู่:
#   - สเกลคงที่ (floor .80/ceil .90): ถาม "การเดินทางไปทำงาน" ได้ 0.8066 ซึ่งชิดพื้น
#     relevance เหลือ 0.07 แล้ว importance 0.9 ของเรื่องรุ่นพี่โดนสอบสวนแซงขึ้นที่ 1
#   - min-max ล้วน: ยืดทุกกรณีเต็ม 0-1 เท่ากัน แยกไม่ออกระหว่าง "ต่างกันจริง"
#     (ห่าง 0.034) กับ "พอ ๆ กัน" (ห่าง 0.0028) ทำให้ importance ไม่ได้ตัดสินตอนเสมอ
#
# วิธีที่ใช้: min-max เพื่อ "จัดอันดับ" + ถ่วงด้วย "ความมั่นใจ" ที่มาจากระยะห่างดิบ
#   ห่างมาก  -> relevance มีน้ำหนักเต็ม กลบ importance
#   ห่างน้อย -> relevance แทบไม่มีน้ำหนัก ปล่อยให้ importance/recency ตัดสิน
# ค่านี้คือระยะห่าง cosine ที่ถือว่า "แยกออกจากกันชัดแล้ว"
REL_DISCRIMINATION = float(os.environ.get("MEM_REL_DISCRIMINATION", 0.03))


@dataclass
class ScoredMemory:
    text: str
    relevance: float
    recency: float
    importance: float
    total: float
    sim_time: float


class MemoryStream:
    """ความจำต่อ agent หนึ่งคน

    สร้าง collection แบบ lazy — agent ที่ยังไม่เคยจำอะไรไม่กินทรัพยากรเลย
    ซึ่งสำคัญมากเมื่อรันหลักพันคน เพราะส่วนใหญ่ไม่ถูกกระตุ้นในแต่ละรอบ
    """

    _client = None
    _client_path: Optional[str] = None
    # chromadb สร้าง client/collection พร้อมกันหลายเธรดไม่ได้ — เจอตอนรัน
    # broadcast_event_async ซึ่งยิง agent พร้อมกัน 30 เธรด แล้วได้
    # "Could not connect to tenant default_tenant" / "'ephemeral'" / "bindings"
    _lock = threading.RLock()

    def __init__(
        self,
        agent_id: str,
        persist_dir: Optional[str] = None,
        embedding_fn=None,
    ):
        self.agent_id = agent_id
        self.persist_dir = persist_dir
        self.embedding_fn = embedding_fn or get_embedding_function()
        self._collection = None
        self._count = 0
        # เวลาในโลกจำลอง (ชั่วโมง) ใช้คิด recency แทนเวลาจริง
        # เพราะการจำลอง 72 ชั่วโมงอาจรันเสร็จใน 15 นาทีจริง
        self.sim_clock: float = 0.0

    # ── ตัว client ──

    @classmethod
    def _get_client(cls, persist_dir: Optional[str]):
        if cls._client is not None and cls._client_path == persist_dir:
            return cls._client

        with cls._lock:
            # เช็คซ้ำใน lock — เธรดอื่นอาจสร้างเสร็จไปแล้วระหว่างที่รอ
            if cls._client is not None and cls._client_path == persist_dir:
                return cls._client

            import chromadb  # นำเข้าตอนใช้จริง เพราะ chromadb โหลดช้า

            if persist_dir:
                os.makedirs(persist_dir, exist_ok=True)
                client = chromadb.PersistentClient(path=persist_dir)
            else:
                client = chromadb.EphemeralClient()
            # ตั้งค่าให้ครบก่อนค่อยเผยแพร่ ไม่งั้นเธรดอื่นอาจเห็น client
            # ที่ยังจับคู่กับ path ผิด
            cls._client_path = persist_dir
            cls._client = client
            return cls._client

    @classmethod
    def reset_client(cls) -> None:
        """ใช้ในเทสต์เพื่อล้างสถานะระหว่างเคส"""
        with cls._lock:
            cls._client = None
            cls._client_path = None

    @classmethod
    def warmup(cls, persist_dir: Optional[str] = None) -> None:
        """เปิด client และโหลดโมเดล embedding ให้เสร็จก่อนเข้าส่วนหลายเธรด"""
        cls._get_client(persist_dir)
        fn = get_embedding_function()
        if hasattr(fn, "warmup"):
            fn.warmup()

    @property
    def collection(self):
        if self._collection is None:
            with self._lock:
                if self._collection is None:
                    client = self._get_client(self.persist_dir)
                    safe = "".join(
                        c if c.isalnum() or c in "-_" else "_" for c in self.agent_id
                    )
                    self._collection = client.get_or_create_collection(
                        name=f"mem_{safe}"[:60],
                        embedding_function=self.embedding_fn,
                        # ต้องระบุชัด ไม่งั้นได้ระยะแบบ L2 ซึ่งสูตรคิด relevance ด้านล่างจะผิด
                        metadata={"hnsw:space": "cosine"},
                    )
                    self._count = self._collection.count()
        return self._collection

    # ── เขียน ──

    def add_memory(
        self,
        observation: str,
        importance: int = 5,
        sim_time: Optional[float] = None,
    ) -> None:
        """บันทึกความทรงจำ

        importance 1-10 — เหตุการณ์ที่กระทบตัวเองโดยตรงควรสูง
        sim_time — เวลาในโลกจำลอง (ชั่วโมง) ถ้าไม่ระบุจะใช้นาฬิกาปัจจุบันของ agent
        """
        if not observation or not observation.strip():
            return

        text = normalize_thai_text(observation)
        t = self.sim_clock if sim_time is None else sim_time
        self._count += 1

        self.collection.add(
            documents=[text],
            metadatas=[{
                "sim_time": float(t),
                "importance": int(max(1, min(10, importance))),
                "wall_time": datetime.now().isoformat(),
            }],
            ids=[f"{self.agent_id}_{self._count}_{t:.3f}"],
        )
        logger.debug("[%s] จำ: %s", self.agent_id, text[:60])

    # ── อ่าน ──

    def retrieve_scored(
        self,
        query: str,
        n_results: int = 3,
        candidate_multiplier: int = 4,
    ) -> List[ScoredMemory]:
        """ดึงความจำโดยจัดอันดับด้วย relevance + recency + importance

        ChromaDB จัดอันดับด้วย similarity อย่างเดียว จึงดึงผู้สมัครมาเกินจำนวน
        แล้วมาจัดอันดับใหม่เอง — ไม่งั้นเรื่องเก่าที่คำคล้ายจะเบียดเรื่องสำคัญที่เพิ่งเกิด
        """
        if self._collection is None and self._count == 0:
            return []
        if self.collection.count() == 0:
            return []

        n_candidates = min(self.collection.count(), max(n_results * candidate_multiplier, n_results))

        try:
            results = self.collection.query(
                query_embeddings=[self.embedding_fn.embed_query(query)],
                n_results=n_candidates,
                include=["documents", "metadatas", "distances"],
            )
        except Exception as e:  # noqa: BLE001
            logger.warning("[%s] ค้นความจำล้มเหลว: %s", self.agent_id, e)
            return []

        docs = (results.get("documents") or [[]])[0]
        metas = (results.get("metadatas") or [[]])[0]
        dists = (results.get("distances") or [[]])[0]

        # collection ตั้ง space เป็น cosine ไว้ ระยะจึงเท่ากับ 1 - ความคล้าย
        sims = [1.0 - float(d) for d in dists]
        if not sims:
            return []

        lo, hi = min(sims), max(sims)
        spread = hi - lo
        # ชุดนี้แยกความต่างได้ชัดแค่ไหน (0 = เหมือนกันหมด, 1 = ต่างกันชัดเจน)
        confidence = min(1.0, spread / REL_DISCRIMINATION)
        span = max(1e-9, spread)

        scored: List[ScoredMemory] = []

        for doc, meta, sim in zip(docs, metas, sims):
            meta = meta or {}
            sim_time = float(meta.get("sim_time", 0.0))

            # อันดับภายในชุด แล้วลดทอนตามความมั่นใจ
            relevance = ((sim - lo) / span) * confidence

            age = max(0.0, self.sim_clock - sim_time)
            recency = math.pow(0.5, age / RECENCY_HALFLIFE_HOURS)
            importance = float(meta.get("importance", 5)) / 10.0

            scored.append(ScoredMemory(
                text=doc,
                relevance=relevance,
                recency=recency,
                importance=importance,
                total=(
                    W_RELEVANCE * relevance
                    + W_RECENCY * recency
                    + W_IMPORTANCE * importance
                ),
                sim_time=sim_time,
            ))

        scored.sort(key=lambda m: -m.total)
        return scored[:n_results]

    def retrieve_memories(self, query: str, n_results: int = 3) -> List[str]:
        return [m.text for m in self.retrieve_scored(query, n_results)]

    def advance_clock(self, hours: float) -> None:
        self.sim_clock += hours

    def __len__(self) -> int:
        # ต้องผ่าน property เพื่อให้ collection ถูกเปิดขึ้นมาก่อน
        # ไม่งั้นกรณีเปิดโปรแกรมใหม่แล้วยังไม่เคยเขียนอะไร จะได้ 0 ทั้งที่มีข้อมูลในดิสก์
        return self.collection.count()
