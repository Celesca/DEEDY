"""
Embedding สำหรับความจำภาษาไทย (Phase 2 / D4, D5)

ทำไมต้องเปลี่ยนจากค่าปริยายของ ChromaDB:
  ChromaDB ใช้ all-MiniLM-L6-v2 ซึ่งเป็นโมเดลภาษาอังกฤษ วัดจริงแล้วได้ MRR แค่ 0.51
  และคืนความจำชุดเดิมแทบทุกคำถาม เช่นถาม "อยากวิจารณ์รัฐบาลแต่กลัวโดนคดี"
  กลับได้เรื่องค่าไฟกับไหว้พระ ไม่ได้เรื่องรุ่นพี่โดนสอบสวนเลย
  แปลว่าความจำของ agent แทบไม่มีผลต่อการตัดสินใจ

  หลังเปลี่ยนเป็น multilingual-e5-small: MRR = 1.00 (ดู scripts/eval_embeddings_th.py)

D5: รันในเครื่องทั้งหมด ไม่ส่งข้อความขึ้น cloud เพราะข้อมูลที่ scrape มามี PII
"""
import logging
import os
import threading
from typing import List, Optional

logger = logging.getLogger("mirofish.core.embeddings")

# ── ความปลอดภัยเมื่อรันหลายเธรด ──
# เจอตอนรันเคส PARAMETER: broadcast_event_async ยิง agent พร้อมกัน 30 เธรด
# แล้วพังสองแบบคนละสาเหตุ
#
#   1) ตอน "โหลด" — สองเธรดโหลดซ้อนกัน ได้
#      "Cannot copy out of meta tensor; no data!"
#      แก้ด้วย _model_lock + double-checked locking
#
#   2) ตอน "ใช้งาน" — เรียก .encode() บนโมเดลตัวเดียวกันพร้อมกัน แล้ว
#      **segfault ที่ modeling_bert.py forward** (torch/OpenMP บน macOS)
#      แก้ด้วย _encode_lock คือ serialize การ encode
#
# ยอมทิ้ง parallelism ตรงนี้ได้ เพราะ encode ใช้เวลาระดับมิลลิวินาที
# ขณะที่การเรียก LLM เป็นวินาที — คอขวดจริงไม่ได้อยู่ที่นี่
_model_lock = threading.Lock()
_encode_lock = threading.Lock()

DEFAULT_MODEL = os.environ.get("EMBEDDING_MODEL", "intfloat/multilingual-e5-small")

# โมเดลตระกูล e5 ต้องใส่ prefix ไม่งั้นคุณภาพตกอย่างมีนัยสำคัญ
_E5_QUERY_PREFIX = "query: "
_E5_PASSAGE_PREFIX = "passage: "


def _needs_e5_prefix(model_name: str) -> bool:
    return "e5" in model_name.lower()


class ThaiMultilingualEmbedding:
    """Embedding function สำหรับ ChromaDB ที่เข้าใจภาษาไทย

    รองรับ ChromaDB EmbeddingFunction protocol และแยก prefix ระหว่าง
    เอกสารกับคำค้นให้อัตโนมัติสำหรับโมเดลตระกูล e5
    """

    def __init__(self, model_name: str = DEFAULT_MODEL, normalize_thai: bool = True):
        self.model_name = model_name
        self.normalize_thai = normalize_thai
        self._model = None
        self._use_prefix = _needs_e5_prefix(model_name)

    # ── ตาม protocol ของ ChromaDB รุ่นใหม่ ──
    # ต้องมีครบทั้ง 4 อย่างนี้ ไม่งั้น chroma จะถือเป็น legacy แล้วเตือนทุกครั้ง
    # และบันทึกค่าตั้งลง collection ไม่ได้ ทำให้เปิดไฟล์เก่าขึ้นมาใช้ผิดโมเดล

    @staticmethod
    def is_legacy() -> bool:
        return False

    @staticmethod
    def name() -> str:
        return "thai_multilingual"

    @staticmethod
    def supported_spaces() -> List[str]:
        # เวกเตอร์ถูก normalize แล้ว จึงใช้ cosine เป็นหลัก
        return ["cosine", "l2", "ip"]

    @staticmethod
    def default_space() -> str:
        return "cosine"

    def get_config(self) -> dict:
        return {"model_name": self.model_name, "normalize_thai": self.normalize_thai}

    @staticmethod
    def build_from_config(config: dict) -> "ThaiMultilingualEmbedding":
        return ThaiMultilingualEmbedding(
            model_name=config.get("model_name", DEFAULT_MODEL),
            normalize_thai=config.get("normalize_thai", True),
        )

    def validate_config(self, config: dict) -> None:  # noqa: D102
        return None

    @staticmethod
    def validate_config_update(old_config: dict, new_config: dict) -> None:  # noqa: D102
        return None

    @property
    def model(self):
        # double-checked locking — เช็คนอก lock ก่อนเพื่อไม่ให้ทุก call ต้องรอ
        # แต่ต้องเช็คซ้ำใน lock ไม่งั้นสองเธรดที่ผ่านด่านแรกพร้อมกันจะโหลดซ้อนกัน
        if self._model is None:
            with _model_lock:
                if self._model is None:
                    from sentence_transformers import SentenceTransformer

                    # จำกัดเธรดของ torch เป็น 1 — เราขนานที่ระดับ agent อยู่แล้ว
                    # ปล่อยให้ torch แตกเธรดซ้อนอีกชั้นทำให้ OpenMP ชนกันบน macOS
                    try:
                        import torch

                        torch.set_num_threads(1)
                    except Exception:  # noqa: BLE001
                        pass

                    logger.info("โหลดโมเดล embedding: %s", self.model_name)
                    self._model = SentenceTransformer(self.model_name)
        return self._model

    def warmup(self) -> "ThaiMultilingualEmbedding":
        """บังคับโหลดโมเดลตอนนี้เลย

        เรียกก่อนเข้าส่วนที่รันหลายเธรด จะได้ไม่ต้องไปแย่งกันโหลดตอนนั้น
        (lock กันพังได้ก็จริง แต่ทำให้ทุกเธรดหยุดรอพร้อมกันตอนเริ่ม)
        """
        _ = self.model
        return self

    def _prepare(self, texts: List[str], is_query: bool) -> List[str]:
        out = texts
        if self.normalize_thai:
            out = [normalize_thai_text(t) for t in out]
        if self._use_prefix:
            prefix = _E5_QUERY_PREFIX if is_query else _E5_PASSAGE_PREFIX
            out = [prefix + t for t in out]
        return out

    def __call__(self, input: List[str]) -> List[List[float]]:  # noqa: A002 - ชื่อตาม protocol
        """ChromaDB เรียกตัวนี้ทั้งตอนเก็บและตอนค้น

        เก็บกับค้นใช้ prefix ต่างกันไม่ได้ผ่านทางนี้ จึงใช้ passage เป็นค่าปริยาย
        ส่วนฝั่งค้นจะเรียก embed_query() เองผ่าน MemoryStream
        """
        return self.embed_documents(list(input))

    def _encode(self, texts: List[str]) -> List[List[float]]:
        model = self.model  # โหลดให้เสร็จนอก lock ของการ encode
        with _encode_lock:
            return model.encode(texts, normalize_embeddings=True).tolist()

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return self._encode(self._prepare(texts, is_query=False))

    def embed_query(self, text: str) -> List[float]:
        return self._encode(self._prepare([text], is_query=True))[0]


_thai_processor_checked = False
_thai_normalize = None


def normalize_thai_text(text: str) -> str:
    """ทำความสะอาดข้อความไทยก่อน embed

    ใช้ PyThaiNLP ถ้ามี (จัดการสระซ้ำ วรรณยุกต์ผิดตำแหน่ง ฯลฯ)
    ถ้าไม่มีก็แค่ตัดช่องว่างส่วนเกิน จะได้ไม่พังตอนยังไม่ได้ลง
    """
    global _thai_processor_checked, _thai_normalize

    if not text:
        return ""

    if not _thai_processor_checked:
        _thai_processor_checked = True
        try:
            from pythainlp.util import normalize as _norm

            _thai_normalize = _norm
        except ImportError:
            logger.warning("ไม่พบ pythainlp — ข้ามการ normalize ภาษาไทย")

    cleaned = " ".join(text.split())
    if _thai_normalize is not None:
        try:
            cleaned = _thai_normalize(cleaned)
        except Exception:  # noqa: BLE001
            pass
    return cleaned


_default: Optional[ThaiMultilingualEmbedding] = None
_default_lock = threading.Lock()


def get_embedding_function() -> ThaiMultilingualEmbedding:
    global _default
    if _default is None:
        with _default_lock:
            if _default is None:
                _default = ThaiMultilingualEmbedding()
    return _default
