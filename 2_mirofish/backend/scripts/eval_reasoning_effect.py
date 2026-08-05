#!/usr/bin/env python3
"""
วัดว่า "ปิด chain-of-thought" ทำให้คำตอบแย่ลงจริงหรือไม่

งานนี้ไม่มีคำตอบถูก (ไม่ใช่ QA) จึงวัด 4 อย่างที่มีความหมายกับงานจำลองสังคมแทน:

  1. GROUNDING  - ใช้ความทรงจำที่ป้อนให้จริงมั้ย หรือตอบลอยๆ
  2. MECHANISM  - กลไก fear -> เลือกช่องทางเสี่ยงน้อยลง ยังทำงานมั้ย
                  (นี่คือแก่นของงานวิจัย ถ้าพังคือปิด reasoning ไม่ได้)
  3. DIVERSITY  - คำตอบหลากหลายพอมั้ย ถ้าเหมือนกันหมดจะจำลองสังคมไม่ได้
  4. INVENTION  - แต่งตัวเลข/เหตุการณ์ที่ไม่ได้ให้มามั้ย (= หลอนของจริง)

ใช้:
    python scripts/eval_reasoning_effect.py --runs 6
"""
import argparse
import json
import math
import os
import re
import sys
import time
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

ENV_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env"
)


def load_env():
    if not os.path.exists(ENV_PATH):
        return
    with open(ENV_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


SYSTEM_PROMPT = (
    "คุณกำลังสวมบทบาทเป็นคนไทยคนหนึ่งในการจำลองสังคม "
    "ตอบกลับเป็น JSON เท่านั้น ใช้ภาษาไทยแบบที่คนไทยพิมพ์จริง"
)

# ความทรงจำ 3 อัน — ใช้ตรวจ grounding ว่าโมเดลหยิบไปใช้จริงมั้ย
MEMORIES = [
    ("รุ่นพี่โดนสอบสวน", ["รุ่นพี่", "สอบสวน", "กรรมการ", "วิจารณ์"]),
    ("ค่าไฟขึ้น", ["ค่าไฟ", "ไฟฟ้า"]),
    ("ลูกเข้ามหาลัย", ["ลูก", "มหาวิทยาลัย", "มหาลัย", "ค่าเทอม"]),
]

# เรียงจากเสี่ยงมากไปเสี่ยงน้อย — ใช้วัดกลไก fear
ACTION_EXPOSURE = {
    "โพสต์สาธารณะ": 5,
    "ลงชื่อคัดค้าน": 4,
    "ร้องเรียน": 4,
    "ส่งในกลุ่มไลน์": 3,
    "คุยกับคนในบ้าน": 2,
    "เงียบ": 1,
}


def build_prompt(fear: int) -> str:
    return f"""ข้อมูลของคุณ:
- อายุ 47 ปี อาชีพ ข้าราชการ อาศัยอยู่ภาคอีสาน การศึกษา ปริญญาตรี
- บุคลิก: รักสงบ ไม่ชอบมีเรื่อง แต่แอบอึดอัดกับระบบเส้นสาย
- ช่องทางรับข่าว: ทีวี และกลุ่มไลน์ครอบครัว (ไม่เล่นทวิตเตอร์)

สภาพอารมณ์ตอนนี้ (0-100):
- ความโกรธ 55 | ความกลัวโดนสอบสวน/ถูกฟ้อง {fear} | ความเบื่อ 20

ความทรงจำที่นึกขึ้นได้:
- เมื่อปีก่อน รุ่นพี่ที่ทำงานโพสต์วิจารณ์นโยบายกระทรวง แล้วโดนตั้งกรรมการสอบสวน
- เดือนนี้ค่าไฟขึ้นอีก เงินเดือนเท่าเดิม
- ลูกเพิ่งเข้ามหาวิทยาลัย ค่าใช้จ่ายเพิ่มขึ้นมาก

เหตุการณ์: รัฐบาลประกาศขึ้นภาษีมูลค่าเพิ่มเป็น 10% เริ่มเดือนหน้า

ตอบเป็น JSON เท่านั้น ห้ามแต่งข้อมูลที่ไม่ได้ให้มา:
{{
  "private_opinion": "สิ่งที่คุณคิดจริงๆ ในใจ",
  "opinion_stance": "supportive | opposing | neutral",
  "public_action": "เลือก 1 อย่างจาก: โพสต์สาธารณะ | ลงชื่อคัดค้าน | ร้องเรียน | ส่งในกลุ่มไลน์ | คุยกับคนในบ้าน | เงียบ",
  "public_content": "ข้อความที่จะพูดออกไปจริง (ถ้าเงียบ ใส่ค่าว่าง)",
  "reason": "ทำไมถึงเลือกแบบนั้น"
}}"""


def call(model, api_key, base_url, fear, reasoning):
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_prompt(fear)},
        ],
        "temperature": 0.8,
        "max_tokens": 900,
        "response_format": {"type": "json_object"},
    }
    if not reasoning:
        payload["reasoning"] = {"enabled": False}

    req = urllib.request.Request(
        f"{base_url.rstrip('/')}/chat/completions",
        data=json.dumps(payload).encode(),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
    )
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=240) as r:
        resp = json.load(r)
    elapsed = time.time() - t0
    msg = resp["choices"][0].get("message") or {}
    text = msg.get("content") or msg.get("reasoning") or ""
    try:
        return json.loads(text), elapsed
    except (json.JSONDecodeError, TypeError):
        return None, elapsed


def analyse(parsed):
    """คืน (จำนวนความทรงจำที่ถูกใช้, exposure ของ action, ตัวเลขที่แต่งขึ้น)"""
    blob = " ".join(str(v) for v in parsed.values())

    hits = sum(1 for _, kws in MEMORIES if any(k in blob for k in kws))

    act = str(parsed.get("public_action", "")).strip()
    exposure = None
    for name, lvl in ACTION_EXPOSURE.items():
        if name in act:
            exposure = lvl
            break

    # ตัวเลขที่ปรากฏในคำตอบแต่ไม่มีในโจทย์ = สัญญาณการแต่งข้อมูล
    allowed = {"10", "47", "55", "20", "0", "100"}
    nums = {n for n in re.findall(r"\d+", blob) if n not in allowed}

    return hits, exposure, nums


def run_condition(model, api_key, base_url, reasoning, fears, runs):
    jobs = [(f, i) for f in fears for i in range(runs)]

    def one(job):
        fear, _ = job
        try:
            parsed, el = call(model, api_key, base_url, fear, reasoning)
        except Exception as e:
            return fear, None, 0.0, str(e)[:80]
        return fear, parsed, el, None

    with ThreadPoolExecutor(max_workers=6) as ex:
        return list(ex.map(one, jobs))


def report(label, results, fears):
    ok = [(f, p, e) for f, p, e, err in results if isinstance(p, dict)]
    fails = len(results) - len(ok)
    if not ok:
        print(f"\n{label}: ล้มเหลวทั้งหมด ({fails} ครั้ง)")
        return None

    grounding, invented, lat = [], set(), []
    per_fear = {f: [] for f in fears}
    actions = Counter()

    for f, p, e in ok:
        hits, exposure, nums = analyse(p)
        grounding.append(hits)
        invented |= nums
        lat.append(e)
        actions[str(p.get("public_action", "?")).strip()] += 1
        if exposure is not None:
            per_fear[f].append(exposure)

    # ความหลากหลาย = entropy ของการกระจาย action
    total = sum(actions.values())
    ent = -sum((c / total) * math.log2(c / total) for c in actions.values())

    print(f"\n{'─'*72}")
    print(f"{label}   (สำเร็จ {len(ok)}/{len(results)}, เฉลี่ย {sum(lat)/len(lat):.1f}s)")
    print(f"{'─'*72}")
    print(f"  GROUNDING  ใช้ความทรงจำเฉลี่ย {sum(grounding)/len(grounding):.2f} / 3 อัน")
    print(f"  DIVERSITY  entropy ของ action = {ent:.2f} (ยิ่งสูงยิ่งหลากหลาย)")
    print(f"  INVENTION  ตัวเลขที่ไม่ได้ให้มา: {sorted(invented) if invented else 'ไม่มี'}")
    print(f"  MECHANISM  ค่า exposure เฉลี่ย (1=เงียบ ... 5=โพสต์สาธารณะ)")
    means = {}
    for f in fears:
        vals = per_fear[f]
        if vals:
            means[f] = sum(vals) / len(vals)
            bar = "█" * int(round(means[f] * 4))
            print(f"               fear={f:3d} -> {means[f]:.2f}  {bar}")
    print(f"  ACTIONS    {dict(actions)}")
    return means


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=None)
    ap.add_argument("--runs", type=int, default=6, help="ยิงกี่ครั้งต่อระดับ fear")
    args = ap.parse_args()

    load_env()
    api_key = os.environ.get("LLM_API_KEY") or os.environ.get("OPENAI_API_KEY")
    base_url = os.environ.get("LLM_BASE_URL", "https://openrouter.ai/api/v1")
    model = args.model or os.environ.get("LLM_MODEL_NAME", "qwen/qwen3-30b-a3b-instruct-2507")
    if not api_key or "your_" in api_key:
        sys.exit("ไม่พบ API key ใน .env")

    fears = [15, 50, 85]
    print(f"โมเดล: {model}")
    print(f"ยิง {args.runs} ครั้ง x fear {fears} x 2 เงื่อนไข = {args.runs*len(fears)*2} calls")

    off = run_condition(model, api_key, base_url, False, fears, args.runs)
    on = run_condition(model, api_key, base_url, True, fears, args.runs)

    m_off = report("ปิด reasoning  (D8 ที่เสนอไว้)", off, fears)
    m_on = report("เปิด reasoning", on, fears)

    print(f"\n{'='*72}")
    print("สรุป: กลไก fear -> ความกล้าแสดงออก ทำงานในเงื่อนไขไหนบ้าง")
    print("='*72" if False else "=" * 72)
    for label, m in (("ปิด reasoning", m_off), ("เปิด reasoning", m_on)):
        if not m or len(m) < 2:
            print(f"  {label:16} ข้อมูลไม่พอสรุป")
            continue
        lo, hi = m.get(min(fears)), m.get(max(fears))
        if lo is None or hi is None:
            print(f"  {label:16} ข้อมูลไม่พอสรุป")
            continue
        drop = lo - hi
        verdict = "✅ ทำงาน" if drop > 0.3 else ("⚠️ อ่อน" if drop > 0 else "❌ ไม่ทำงาน")
        print(f"  {label:16} fear ต่ำ={lo:.2f} -> fear สูง={hi:.2f}  ต่างกัน {drop:+.2f}  {verdict}")


if __name__ == "__main__":
    main()
