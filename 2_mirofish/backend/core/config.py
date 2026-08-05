"""
ตั้งค่ากลางของเครื่องยนต์จำลอง — อ่านจาก .env ทั้งหมด ห้าม hardcode

ดู PLAN.md:
  D2  ใช้ openai SDK ตรงๆ ไม่ใช้ LangChain
  D8  ปิด chain-of-thought ทุก request
  D9  ใช้ Qwen เป็นหลัก
"""
import os
from dataclasses import dataclass, field
from typing import Optional


def _load_dotenv() -> None:
    """อ่าน .env จาก root ของโปรเจกต์ (ไม่ทับค่าที่ตั้งไว้ใน environment แล้ว)"""
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    path = os.path.join(root, ".env")
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


_load_dotenv()


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


@dataclass
class LLMConfig:
    api_key: Optional[str] = field(default_factory=lambda: (
        os.environ.get("LLM_API_KEY") or os.environ.get("OPENAI_API_KEY")
    ))
    base_url: str = field(default_factory=lambda: os.environ.get(
        "LLM_BASE_URL", "https://openrouter.ai/api/v1"
    ))
    model: str = field(default_factory=lambda: os.environ.get(
        "LLM_MODEL_NAME", "qwen/qwen3-30b-a3b-instruct-2507"
    ))
    temperature: float = field(default_factory=lambda: _env_float("LLM_TEMPERATURE", 0.85))
    max_tokens: int = field(default_factory=lambda: _env_int("LLM_MAX_TOKENS", 700))
    timeout: int = field(default_factory=lambda: _env_int("LLM_TIMEOUT", 120))
    max_retries: int = field(default_factory=lambda: _env_int("LLM_MAX_RETRIES", 3))

    # D8 — ปิด chain-of-thought
    disable_reasoning: bool = field(
        default_factory=lambda: _env_bool("LLM_DISABLE_REASONING", True)
    )

    # จำนวน request พร้อมกันสูงสุด (ตัวกำหนดเวลารันจริง)
    concurrency: int = field(default_factory=lambda: _env_int("LLM_CONCURRENCY", 30))

    def is_configured(self) -> bool:
        return bool(self.api_key) and "your_" not in (self.api_key or "")


@dataclass
class SimulationConfig:
    # ทำให้ผลลัพธ์ reproduce ได้ (Phase 6)
    seed: int = field(default_factory=lambda: _env_int("SIM_SEED", 42))
    # สัดส่วน agent ที่ถูกกระตุ้นให้คิดในแต่ละรอบ
    # คนส่วนใหญ่ไม่ตอบสนองต่อทุกเรื่อง — เป็นทั้งเรื่องความสมจริงและต้นทุน
    activation_rate: float = field(
        default_factory=lambda: _env_float("SIM_ACTIVATION_RATE", 0.15)
    )
    data_dir: str = field(default_factory=lambda: os.environ.get(
        "SIM_DATA_DIR",
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data"),
    ))


LLM = LLMConfig()
SIM = SimulationConfig()
