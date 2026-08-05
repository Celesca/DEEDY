#!/usr/bin/env python3
"""
เทียบโมเดลบน OpenRouter ด้วยงานจริงของโปรเจกต์ (ภาษาไทย)

วัด 4 อย่างที่ใช้ตัดสินใจจริง:
  1. คุณภาพภาษาไทย  - อ่านแล้วเป็นคนไทยพิมพ์ หรือเป็นภาษาแปล
  2. ทำตามสคีมาได้มั้ย - คืน JSON ครบฟิลด์หรือไม่
  3. ราคาต่อการเรียก  - คำนวณจากราคาจริงของ OpenRouter
  4. เวลาตอบ         - ตัวกำหนดว่ารัน 1000 agent จะใช้เวลาเท่าไหร่

ใช้:
    python scripts/eval_models_th.py                # รันชุด default
    python scripts/eval_models_th.py --models a,b   # ระบุเอง
    python scripts/eval_models_th.py --runs 3       # ยิงซ้ำเพื่อดูความเสถียร
"""
import argparse
import json
import os
import statistics
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ── โหลด .env แบบไม่พึ่ง dependency ──
def load_env():
    env_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env"
    )
    if not os.path.exists(env_path):
        return
    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())


DEFAULT_MODELS = [
    "google/gemini-2.5-flash-lite",
    "google/gemini-2.5-flash",
    "openai/gpt-4o-mini",
    "qwen/qwen3.5-flash-02-23",
    "amazon/nova-lite-v1",
    "google/gemma-3-12b-it",
    "mistralai/mistral-nemo",
]

SYSTEM_PROMPT = (
    "คุณกำลังสวมบทบาทเป็นคนไทยคนหนึ่งในการจำลองสังคม "
    "ตอบกลับเป็น JSON เท่านั้น ห้ามมีข้อความอื่นนอก JSON "
    "ใช้ภาษาไทยแบบที่คนไทยพิมพ์จริงในชีวิตประจำวัน ไม่ใช่ภาษาแปล"
)

# ใช้โจทย์แบบ Phase 1 คือต้องแยกความเห็นส่วนตัวออกจากสิ่งที่แสดงออก
USER_PROMPT = """ข้อมูลของคุณ:
- อายุ 47 ปี อาชีพ ข้าราชการ อาศัยอยู่ภาคอีสาน การศึกษา ปริญญาตรี
- บุคลิก: รักสงบ ไม่ชอบมีเรื่อง แต่แอบอึดอัดกับระบบเส้นสาย
- ช่องทางรับข่าว: ทีวี และกลุ่มไลน์ครอบครัว (ไม่เล่นทวิตเตอร์)

สภาพอารมณ์ตอนนี้ (0-100):
- ความโกรธ 55 | ความกลัวโดนสอบสวน/ถูกฟ้อง 75 | ความเบื่อ 20

ความทรงจำที่นึกขึ้นได้:
- เมื่อปีก่อน รุ่นพี่ที่ทำงานโพสต์วิจารณ์นโยบายกระทรวง แล้วโดนตั้งกรรมการสอบสวน
- เดือนนี้ค่าไฟขึ้นอีก เงินเดือนเท่าเดิม
- ลูกเพิ่งเข้ามหาวิทยาลัย ค่าใช้จ่ายเพิ่มขึ้นมาก

เหตุการณ์: รัฐบาลประกาศขึ้นภาษีมูลค่าเพิ่มเป็น 10% เริ่มเดือนหน้า

ตอบเป็น JSON ตามนี้เท่านั้น:
{
  "private_opinion": "สิ่งที่คุณคิดจริงๆ ในใจ (พูดตรงไปตรงมา)",
  "opinion_stance": "supportive | opposing | neutral",
  "public_action": "โพสต์สาธารณะ | ส่งในกลุ่มไลน์ | คุยกับคนในบ้าน | เงียบ | ร้องเรียน | ลงชื่อคัดค้าน",
  "public_content": "ข้อความที่คุณจะพูดออกไปจริง (ถ้าเลือกเงียบ ให้ใส่ค่าว่าง)",
  "reason": "ทำไมถึงเลือกแสดงออกแบบนั้น"
}"""

REQUIRED_FIELDS = ["private_opinion", "opinion_stance", "public_action", "public_content", "reason"]


def get_pricing():
    try:
        with urllib.request.urlopen("https://openrouter.ai/api/v1/models", timeout=30) as r:
            data = json.load(r)
        return {
            m["id"]: (float(m["pricing"]["prompt"]), float(m["pricing"]["completion"]))
            for m in data["data"]
        }
    except Exception as e:
        print(f"เตือน: ดึงราคาไม่ได้ ({e}) จะไม่แสดงค่าใช้จ่าย")
        return {}


def call_model(model: str, api_key: str, base_url: str, reasoning: bool = False):
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": USER_PROMPT},
        ],
        "temperature": 0.8,
        "max_tokens": 700,
        "response_format": {"type": "json_object"},
    }
    if not reasoning:
        # สำคัญมากสำหรับโมเดลสาย reasoning (GLM, Qwen3.5-9b ฯลฯ)
        # ถ้าไม่ปิด มันจะเผา token ไปกับ chain-of-thought จนไม่เหลือให้ตอบ
        # (finish_reason=length) ทั้งช้ากว่าและแพงกว่าหลายเท่า
        # อีกทั้งมันคิดเป็นภาษาอังกฤษ ซึ่งไม่เหมาะกับการจำลองปฏิกิริยาฉับพลันของคนไทย
        payload["reasoning"] = {"enabled": False}
    body = json.dumps(payload).encode()

    req = urllib.request.Request(
        f"{base_url.rstrip('/')}/chat/completions",
        data=body,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
    )
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=180) as r:
        payload = json.load(r)
    elapsed = time.time() - t0

    msg = payload["choices"][0].get("message") or {}
    # บางโมเดล (โดยเฉพาะสาย reasoning) คืน content เป็น null
    # แล้วเก็บคำตอบไว้ใน reasoning/reasoning_content แทน
    text = msg.get("content") or msg.get("reasoning_content") or msg.get("reasoning") or ""
    if isinstance(text, list):  # บาง provider คืนเป็น content block
        text = "".join(b.get("text", "") for b in text if isinstance(b, dict))
    usage = payload.get("usage", {})
    return text, usage, elapsed


def thai_ratio(text: str) -> float:
    """สัดส่วนอักษรไทย - ใช้จับกรณีโมเดลหลุดไปตอบภาษาอื่น"""
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return 0.0
    return sum(1 for c in letters if "฀" <= c <= "๿") / len(letters)


def evaluate(model, api_key, base_url, pricing, runs, reasoning=False):
    lat, costs, results = [], [], []
    errors = []

    for _ in range(runs):
        try:
            text, usage, elapsed = call_model(model, api_key, base_url, reasoning)
        except Exception as e:
            errors.append(str(e)[:120])
            continue
        lat.append(elapsed)
        pin, pout = pricing.get(model, (0, 0))
        costs.append(usage.get("prompt_tokens", 0) * pin + usage.get("completion_tokens", 0) * pout)
        parsed = None
        if isinstance(text, str) and text.strip():
            raw = text.strip()
            if raw.startswith("```"):  # เผื่อโมเดลห่อ markdown มาแม้สั่ง json_object
                raw = raw.split("```", 2)[1].removeprefix("json").strip()
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError:
                parsed = None
        results.append((text, parsed))

    if not results:
        return {"model": model, "ok": False, "errors": errors}

    valid = [p for _, p in results if isinstance(p, dict)]
    complete = [p for p in valid if all(f in p for f in REQUIRED_FIELDS)]
    sample_text, sample_parsed = results[0]
    body = " ".join(str(v) for v in sample_parsed.values()) if isinstance(sample_parsed, dict) else sample_text

    return {
        "model": model,
        "ok": True,
        "json_ok": f"{len(valid)}/{len(results)}",
        "schema_ok": f"{len(complete)}/{len(results)}",
        "latency": statistics.mean(lat),
        "cost": statistics.mean(costs) if costs else 0.0,
        "thai": thai_ratio(body),
        "sample": sample_parsed if isinstance(sample_parsed, dict) else {"raw": sample_text[:300]},
        "errors": errors,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", help="รายชื่อโมเดลคั่นด้วย comma")
    ap.add_argument("--runs", type=int, default=2, help="ยิงกี่ครั้งต่อโมเดล (default 2)")
    ap.add_argument("--reasoning", action="store_true", help="เปิด chain-of-thought (default ปิด)")
    args = ap.parse_args()

    load_env()
    api_key = os.environ.get("LLM_API_KEY") or os.environ.get("OPENAI_API_KEY")
    base_url = os.environ.get("LLM_BASE_URL", "https://openrouter.ai/api/v1")
    if not api_key or "your_" in api_key:
        sys.exit("ไม่พบ API key ที่ใช้ได้ใน .env (ต้องมี LLM_API_KEY หรือ OPENAI_API_KEY)")

    models = args.models.split(",") if args.models else DEFAULT_MODELS
    pricing = get_pricing()

    print(f"ทดสอบ {len(models)} โมเดล x {args.runs} ครั้ง ผ่าน {base_url}\n")

    with ThreadPoolExecutor(max_workers=4) as ex:
        reports = list(ex.map(lambda m: evaluate(m, api_key, base_url, pricing, args.runs, args.reasoning), models))

    ok = [r for r in reports if r["ok"]]
    ok.sort(key=lambda r: -r["thai"])

    print("=" * 100)
    print(f"{'model':<34}{'JSON':>7}{'สคีมา':>8}{'ไทย%':>8}{'วินาที':>9}{'$/call':>11}{'$/1000ag':>11}")
    print("=" * 100)
    for r in ok:
        # 1000 agent x 72 รอบ x activation 15%
        bulk = r["cost"] * 1000 * 72 * 0.15
        print(f"{r['model']:<34}{r['json_ok']:>7}{r['schema_ok']:>8}"
              f"{r['thai']*100:>7.0f}%{r['latency']:>9.1f}{r['cost']:>11.6f}{bulk:>11.2f}")

    for r in reports:
        if not r["ok"]:
            print(f"\n❌ {r['model']}: {r['errors'][:1]}")

    print("\n" + "=" * 100)
    print("ตัวอย่างคำตอบ (ตัดสินคุณภาพภาษาไทยด้วยตาตัวเอง อย่าดูแค่ตัวเลข)")
    print("=" * 100)
    for r in ok:
        print(f"\n──── {r['model']} ────")
        s = r["sample"]
        for k in ("private_opinion", "opinion_stance", "public_action", "public_content"):
            if k in s:
                print(f"  {k:17}: {s[k]}")


if __name__ == "__main__":
    main()
