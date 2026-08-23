"""
Weak Annotation (Phase 3.5 / O2)

ติดป้าย stance, emotion, topic, และ informality ให้กับ Document

หลักการ:
  - ทุก annotation **ต้อง**มี confidence score ห้ามให้ป้ายแบบมั่นใจเต็มร้อย
  - ใช้ LLM เป็นหนึ่งใน labeling function ไม่ใช่ตัวเดียว
    (อนาคตเพิ่ม heuristic labeler แล้วรวมเสียง)
  - annotation ที่ล้มเหลวไม่ทำให้ pipeline หยุด แต่ติดป้าย unknown ไว้
"""
import logging
from typing import Any, Dict

from ..llm import get_client, LLMError
from .provenance import Document
from .views import profile_informality

logger = logging.getLogger("mirofish.pipeline.annotate")

# ค่าที่ยอมรับ — ถ้า LLM ตอบนอกชุดนี้จะ fallback เป็น unknown
_VALID_STANCES = {"supportive", "opposing", "neutral"}
_VALID_EMOTIONS = {"anger", "joy", "fear", "sadness", "surprise", "disgust", "neutral"}


def _validate_annotation(response: Dict[str, Any]) -> Dict[str, Any]:
    """ตรวจสอบค่าที่ LLM ตอบมา — ไม่ไว้ใจว่าจะถูกเสมอ"""
    stance = response.get("stance", "")
    if stance not in _VALID_STANCES:
        stance = "unknown"

    emotion = response.get("emotion", "")
    if emotion not in _VALID_EMOTIONS:
        emotion = "unknown"

    try:
        confidence = float(response.get("confidence_score", 0))
        confidence = max(0.0, min(1.0, confidence))
    except (TypeError, ValueError):
        confidence = 0.0

    return {
        "stance": stance,
        "emotion": emotion,
        "confidence_score": round(confidence, 3),
        "annotation_reason": str(response.get("reason", "")),
        "annotator": "llm",
    }


def annotate_document(doc: Document, topic_context: str = "") -> Document:
    """วิเคราะห์ข้อความเพื่อหา Stance และ Emotion

    เพิ่ม informality profile จาก views.py ด้วย (ไม่ต้องใช้ LLM)
    """
    # ── Heuristic annotation: informality (ไม่เสีย LLM call) ──
    profile = profile_informality(doc.raw_text)
    doc.annotations["informality_score"] = profile.informality_score

    # ── LLM annotation: stance + emotion ──
    system_prompt = (
        "คุณคือผู้ช่วยวิเคราะห์ข้อความภาษาไทย "
        "วิเคราะห์จุดยืน (stance) และอารมณ์ (emotion) ของข้อความ "
        "ให้คะแนนความมั่นใจ (confidence_score) ด้วย"
    )

    # ตัดข้อความยาวเกินเพื่อประหยัด token
    text_preview = doc.raw_text[:500]
    user_prompt = (
        f'ข้อความ: "{text_preview}"\n'
        f'บริบทหัวข้อ: "{topic_context}"\n\n'
        "ตอบเป็น JSON เท่านั้น:\n"
        '{"stance": "supportive|opposing|neutral", '
        '"emotion": "anger|joy|fear|sadness|surprise|disgust|neutral", '
        '"confidence_score": 0.0-1.0, '
        '"reason": "เหตุผลสั้นๆ"}'
    )

    client = get_client()
    try:
        response = client.complete_json(
            system=system_prompt,
            user=user_prompt,
            required_fields=["stance", "emotion", "confidence_score"],
        )
        validated = _validate_annotation(response)
        doc.annotations.update(validated)
    except LLMError:
        logger.exception("Annotation failed for doc %s", doc.doc_id)
        doc.annotations.update({
            "stance": "unknown",
            "emotion": "unknown",
            "confidence_score": 0.0,
            "annotator": "llm_failed",
        })

    return doc
