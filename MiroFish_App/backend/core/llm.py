"""
ตัวเรียก LLM — ใช้ openai SDK ตรงๆ (D2) และปิด chain-of-thought (D8)

ทำไมไม่ใช้ LangChain:
  camel-ai ต้องการ openai<2 แต่ langchain-openai ต้องการ openai>=2.45
  อยู่ venv เดียวกันไม่ได้ และเราใช้ LangChain แค่เรียก chat completion จุดเดียว

ทำไมปิด reasoning (วัดจริงแล้ว ดู C4 ใน PLAN.md):
  - โมเดลสาย reasoning เผา token จนตอบไม่ออก (qwen3.5-9b: 13.8s ตอบไม่ออก -> 1.2s ตอบครบ)
  - ไม่ได้ทำให้หลอนน้อยลง (ไม่มีการแต่งข้อมูลทั้งสองเงื่อนไข)
  - ทำให้คำตอบเหมือนกันมากขึ้น ซึ่งทำลายความหลากหลายที่งานจำลองประชากรต้องการ
  - และเราจำลองปฏิกิริยาฉับพลันของคนเลื่อนฟีด ไม่ใช่บทวิเคราะห์
"""
import json
import logging
import random
import time
from typing import Any, Dict, List, Optional

from openai import OpenAI

from .config import LLM

logger = logging.getLogger("mirofish.core.llm")


class LLMError(RuntimeError):
    pass


class _Truncated(LLMError):
    """โมเดลตอบไม่จบเพราะโควตา token หมด — ต่างจากพังแบบอื่นตรงที่ retry เฉย ๆ ไม่ช่วย"""

    def __init__(self, budget: int):
        self.budget = budget
        super().__init__(f"คำตอบถูกตัดกลางคัน (โควตา {budget} token ไม่พอ)")


class LLMClient:
    """หุ้ม openai SDK พร้อม retry และการบังคับ JSON"""

    def __init__(self, config=None):
        self.config = config or LLM
        self._client: Optional[OpenAI] = None

    @property
    def client(self) -> OpenAI:
        if self._client is None:
            if not self.config.is_configured():
                raise LLMError(
                    "ยังไม่ได้ตั้งค่า API key — ใส่ LLM_API_KEY ใน .env"
                )
            self._client = OpenAI(
                api_key=self.config.api_key,
                base_url=self.config.base_url,
                timeout=self.config.timeout,
                max_retries=0,  # จัดการ retry เอง จะได้คุม backoff ได้
            )
        return self._client

    def is_available(self) -> bool:
        return self.config.is_configured()

    def complete_json(
        self,
        system: str,
        user: str,
        *,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        required_fields: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """เรียก LLM แล้วคืน dict — โยน LLMError ถ้าไม่สำเร็จหลัง retry ครบ"""
        extra_body: Dict[str, Any] = {}
        if self.config.disable_reasoning:
            # ฟิลด์นี้เป็นของ OpenRouter ผู้ให้บริการอื่นจะเมินไปเอง
            extra_body["reasoning"] = {"enabled": False}

        budget = max_tokens or self.config.max_tokens
        last_error = None
        for attempt in range(self.config.max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.config.model,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    temperature=temperature if temperature is not None else self.config.temperature,
                    max_tokens=budget,
                    response_format={"type": "json_object"},
                    extra_body=extra_body or None,
                )
                self._check_truncated(response, budget)
                parsed = self._parse(response)
                if required_fields:
                    missing = [f for f in required_fields if f not in parsed]
                    if missing:
                        raise LLMError(f"คำตอบขาดฟิลด์: {missing}")
                return parsed

            except _Truncated as e:
                # ตอบไม่จบเพราะโควตา token หมด — ลองใหม่ด้วยคำเดิมได้ผลเท่าเดิม
                # ต้องเพิ่มโควตาให้ ไม่ใช่แค่ retry
                last_error = e
                if attempt < self.config.max_retries - 1:
                    budget = int(budget * 1.6)
                    logger.warning(
                        "คำตอบถูกตัดกลางคัน (โควตา %d token ไม่พอ) — ลองใหม่ด้วย %d",
                        e.budget, budget,
                    )
                continue

            except Exception as e:  # noqa: BLE001 - ต้องจับทุกอย่างเพื่อ retry
                last_error = e
                if attempt < self.config.max_retries - 1:
                    backoff = (2 ** attempt) + random.random()
                    logger.warning(
                        "เรียก LLM ไม่สำเร็จ (ครั้งที่ %d/%d): %s — รอ %.1fs",
                        attempt + 1, self.config.max_retries, e, backoff,
                    )
                    time.sleep(backoff)

        raise LLMError(f"เรียก LLM ไม่สำเร็จหลังลอง {self.config.max_retries} ครั้ง: {last_error}")

    @staticmethod
    def _check_truncated(response, budget: int) -> None:
        """จับกรณีโมเดลตอบไม่จบเพราะ token หมด

        เจอบ่อยมากกับภาษาไทย เพราะไทยกินโทเคนมากกว่าอังกฤษราว 1.4 เท่า
        JSON ที่ถูกตัดกลางคันจะ parse ไม่ผ่านแล้วไป retry ด้วยคำสั่งเดิม
        ซึ่งได้ผลเหมือนเดิมทุกครั้ง — เสียเวลาและเงินฟรี 3 รอบ
        ต้องแยกออกมาเพื่อ **เพิ่มโควตา** ไม่ใช่แค่ลองใหม่
        """
        try:
            reason = response.choices[0].finish_reason
        except (AttributeError, IndexError):
            return
        if reason == "length":
            raise _Truncated(budget)

    @staticmethod
    def _parse(response) -> Dict[str, Any]:
        choice = response.choices[0]
        message = choice.message
        text = getattr(message, "content", None)

        # บางโมเดล (สาย reasoning) คืน content เป็น null แล้วเก็บคำตอบไว้ที่อื่น
        if not text:
            for attr in ("reasoning_content", "reasoning"):
                text = getattr(message, attr, None)
                if text:
                    break

        if not text:
            raise LLMError(f"คำตอบว่างเปล่า (finish_reason={choice.finish_reason})")

        text = text.strip()
        if text.startswith("```"):  # เผื่อโมเดลห่อ markdown มาแม้สั่ง json_object
            parts = text.split("```")
            if len(parts) >= 2:
                text = parts[1].removeprefix("json").strip()

        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as e:
            raise LLMError(f"คำตอบไม่ใช่ JSON: {text[:200]}") from e

        if not isinstance(parsed, dict):
            raise LLMError(f"คำตอบไม่ใช่ object: {type(parsed).__name__}")
        return parsed


_default_client: Optional[LLMClient] = None


def get_client() -> LLMClient:
    global _default_client
    if _default_client is None:
        _default_client = LLMClient()
    return _default_client
