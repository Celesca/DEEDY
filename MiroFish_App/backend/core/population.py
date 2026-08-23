"""
ประชากรสังเคราะห์ — ภาพแทนสังคมไทย ไม่ใช่แค่คนเล่นโซเชียล (Phase 4 / O2)

หลักการ:
  1. สุ่มคุณสมบัติตามสัดส่วนประชากรจริง (NSO) ไม่ใช่สุ่มอิสระ
  2. คนที่ไม่ใช้โซเชียล **ต้องมี** ตามสัดส่วน ไม่งั้นตัวอย่างเอียง
  3. สร้างแบบ archetype ไม่เลียนบุคคลจริง (PDPA)
  4. reproduce ได้ด้วย seed เดียวกัน

⚠️ ตัวเลขสัดส่วนเป็น **ค่าชั่วคราว** จาก NSO 2023 และ ETDA 2023
   ต้องกำกับชัดเจนเมื่ออ้างอิงในรายงาน และแทนที่ด้วยตัวเลขปีที่ถูกต้องก่อนตีพิมพ์
"""
import json
import logging
import random
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .agent import AgentProfile
from .expression import MediaAccess

logger = logging.getLogger("mirofish.core.population")

# ──────────────────────────────────────────────────────────────────────
# สัดส่วนประชากรไทย (ค่าชั่วคราว)
#
# แหล่ง:
#   - อายุ/ภูมิภาค: สำมะโนประชากร NSO 2023 (ประมาณ)
#   - อาชีพ: สำรวจแรงงาน NSO 2023 Q3
#   - การเข้าถึงสื่อ: ETDA Thailand Internet User Behavior 2023
#
# ⚠️ ตัวเลขเหล่านี้เป็นค่าประมาณ ยังไม่ได้ตรวจสอบกับแหล่งต้นฉบับ
#    ห้ามอ้างอิงในรายงานโดยไม่กำกับว่าเป็นค่าชั่วคราว
# ──────────────────────────────────────────────────────────────────────

# (ค่า, น้ำหนัก) — น้ำหนักไม่ต้องรวมเป็น 1.0 โค้ดจะ normalize เอง

AGE_DISTRIBUTION: List[Tuple[Tuple[int, int], float]] = [
    ((18, 24), 0.12),   # วัยรุ่น-นักศึกษา
    ((25, 34), 0.17),   # วัยทำงานต้น
    ((35, 44), 0.16),   # วัยทำงานกลาง
    ((45, 54), 0.15),   # วัยทำงานปลาย
    ((55, 64), 0.14),   # ใกล้เกษียณ
    ((65, 80), 0.13),   # สูงอายุ
]

REGION_DISTRIBUTION: List[Tuple[str, float]] = [
    ("กรุงเทพฯ และปริมณฑล", 0.22),
    ("ภาคกลาง", 0.15),
    ("ภาคเหนือ", 0.14),
    ("ภาคอีสาน", 0.28),
    ("ภาคใต้", 0.13),
    ("ภาคตะวันออก", 0.08),
]

OCCUPATION_DISTRIBUTION: List[Tuple[str, float]] = [
    ("เกษตรกร", 0.18),
    ("รับจ้างทั่วไป/แรงงาน", 0.15),
    ("พนักงานบริษัทเอกชน", 0.18),
    ("ข้าราชการ/รัฐวิสาหกิจ", 0.10),
    ("ค้าขาย/เจ้าของกิจการ", 0.14),
    ("นักเรียน/นักศึกษา", 0.10),
    ("แม่บ้าน/ไม่ได้ทำงาน", 0.08),
    ("เกษียณ", 0.07),
]

EDUCATION_DISTRIBUTION: List[Tuple[str, float]] = [
    ("ประถม", 0.25),
    ("มัธยม/ปวช.", 0.30),
    ("ปวส./อนุปริญญา", 0.12),
    ("ปริญญาตรี", 0.25),
    ("สูงกว่าปริญญาตรี", 0.08),
]

INCOME_DISTRIBUTION: List[Tuple[str, float]] = [
    ("low", 0.35),
    ("middle", 0.45),
    ("high", 0.20),
]


def _weighted_choice(
    rng: random.Random, distribution: List[Tuple[Any, float]]
) -> Any:
    """สุ่มตามน้ำหนัก — ใช้ rng ที่ seed ได้เพื่อ reproduce"""
    items, weights = zip(*distribution)
    return rng.choices(items, weights=weights, k=1)[0]


def _generate_media_access(
    rng: random.Random, age: int, region: str, occupation: str
) -> MediaAccess:
    """สร้าง media_access ตามสัดส่วนจริงของคนไทย

    ข้อมูลจาก ETDA 2023:
      - โซเชียลมีเดีย: ~80% ของคนไทยอายุ 18-34, ~55% ของ 35-54, ~25% ของ 55+
      - LINE: แทบทุกคนที่มีสมาร์ทโฟน (~88%)
      - ทีวี: ยังเป็นช่องหลักของ 45+ (~90%) แต่ลดลงในคนรุ่นใหม่ (~50%)
      - ชุมชน: สูงในต่างจังหวัด (~60%) ต่ำในกรุงเทพ (~20%)
    """
    # โซเชียล — ขึ้นกับอายุเป็นหลัก
    if age < 25:
        social_prob = 0.85
    elif age < 35:
        social_prob = 0.78
    elif age < 45:
        social_prob = 0.60
    elif age < 55:
        social_prob = 0.45
    elif age < 65:
        social_prob = 0.30
    else:
        social_prob = 0.15

    # เกษตรกร/เกษียณ ลดลงอีก
    if occupation in ("เกษตรกร", "เกษียณ"):
        social_prob *= 0.7

    # LINE — ทุกกลุ่มสูง
    line_prob = 0.88 if age < 65 else 0.55

    # ทีวี — สูงในคนอายุมาก
    tv_prob = 0.50 if age < 35 else (0.75 if age < 55 else 0.92)

    # ชุมชน — สูงนอกกรุงเทพ
    if region == "กรุงเทพฯ และปริมณฑล":
        community_prob = 0.20
    else:
        community_prob = 0.55 if age < 45 else 0.70

    return MediaAccess(
        social_media=rng.random() < social_prob,
        line=rng.random() < line_prob,
        tv=rng.random() < tv_prob,
        community=rng.random() < community_prob,
    )


def _generate_deference(rng: random.Random, age: int, occupation: str) -> int:
    """เกรงใจ — สูงในข้าราชการและคนอายุมาก"""
    base = 30
    if age > 50:
        base += 20
    elif age > 35:
        base += 10
    if occupation in ("ข้าราชการ/รัฐวิสาหกิจ",):
        base += 15
    elif occupation in ("นักเรียน/นักศึกษา",):
        base -= 10
    # jitter ±10
    return max(5, min(95, base + rng.randint(-10, 10)))


def _generate_seniority_pressure(
    rng: random.Random, age: int, occupation: str
) -> int:
    """แรงกดดันจากระบบอาวุโส"""
    base = 25
    if occupation in ("ข้าราชการ/รัฐวิสาหกิจ",):
        base += 25
    elif occupation in ("พนักงานบริษัทเอกชน",):
        base += 10
    elif occupation in ("เกษตรกร", "ค้าขาย/เจ้าของกิจการ"):
        base -= 5
    if age > 55:
        base -= 10  # คนอายุมากกลัวอาวุโสน้อยกว่า เพราะตัวเองก็อาวุโส
    return max(5, min(95, base + rng.randint(-10, 10)))


def generate_demographic(
    rng: random.Random, agent_id: str
) -> Dict[str, Any]:
    """สุ่มคุณสมบัติทางประชากรหนึ่งชุด — ยังไม่มี personality (ต้องใช้ LLM)"""
    age_range = _weighted_choice(rng, AGE_DISTRIBUTION)
    age = rng.randint(age_range[0], age_range[1])
    region = _weighted_choice(rng, REGION_DISTRIBUTION)
    occupation = _weighted_choice(rng, OCCUPATION_DISTRIBUTION)
    education = _weighted_choice(rng, EDUCATION_DISTRIBUTION)
    income = _weighted_choice(rng, INCOME_DISTRIBUTION)

    # ปรับอาชีพให้สอดคล้องกับอายุ
    if age < 23 and occupation not in ("นักเรียน/นักศึกษา",):
        occupation = "นักเรียน/นักศึกษา"
    if age > 65 and occupation not in ("เกษียณ", "เกษตรกร", "ค้าขาย/เจ้าของกิจการ"):
        occupation = "เกษียณ"

    media = _generate_media_access(rng, age, region, occupation)
    deference = _generate_deference(rng, age, occupation)
    seniority = _generate_seniority_pressure(rng, age, occupation)

    return {
        "agent_id": agent_id,
        "age": age,
        "region": region,
        "occupation": occupation,
        "education": education,
        "income_level": income,
        "media": asdict(media),
        "deference": deference,
        "seniority_pressure": seniority,
    }


def demographics_to_profile(demo: Dict[str, Any]) -> AgentProfile:
    """แปลง dict จาก JSON กลับเป็น AgentProfile"""
    media_dict = demo.get("media", {})
    return AgentProfile(
        agent_id=demo["agent_id"],
        age=demo["age"],
        occupation=demo["occupation"],
        region=demo["region"],
        base_personality=demo.get("base_personality", ""),
        education=demo.get("education", ""),
        income_level=demo.get("income_level", ""),
        media=MediaAccess(**media_dict),
        deference=demo.get("deference", 40),
        seniority_pressure=demo.get("seniority_pressure", 30),
        influence=demo.get("influence", 1.0),
        is_kol=demo.get("is_kol", False),
        follower_count=demo.get("follower_count", 50),
    )


def load_population(path: str) -> List[AgentProfile]:
    """โหลดประชากรจากไฟล์ JSON ที่ bootstrap_population.py สร้าง"""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"ไม่พบไฟล์ประชากร: {path}")
    with open(p, encoding="utf-8") as f:
        data = json.load(f)
    agents = data if isinstance(data, list) else data.get("agents", [])
    profiles = [demographics_to_profile(d) for d in agents]
    logger.info("Loaded %d agents from %s", len(profiles), path)
    return profiles


def save_population(agents: List[Dict[str, Any]], path: str, metadata: Optional[Dict] = None) -> None:
    """บันทึกประชากรเป็น JSON ที่ commit ได้"""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "metadata": metadata or {},
        "agents": agents,
    }
    with open(p, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    logger.info("Saved %d agents to %s", len(agents), path)


def validate_distribution(
    agents: List[Dict[str, Any]],
    tolerance: float = 0.10,
) -> Dict[str, List[str]]:
    """ตรวจว่าการกระจายตรงกับเป้า ±tolerance

    คืน dict ของปัญหาที่เจอ — ว่างเปล่า = ผ่าน
    """
    n = len(agents)
    if n == 0:
        return {"error": ["ไม่มี agent เลย"]}

    issues: Dict[str, List[str]] = {}

    # ตรวจภูมิภาค
    region_counts: Dict[str, int] = {}
    for a in agents:
        r = a.get("region", "unknown")
        region_counts[r] = region_counts.get(r, 0) + 1

    region_issues = []
    for region, target_weight in REGION_DISTRIBUTION:
        actual = region_counts.get(region, 0) / n
        target = target_weight / sum(w for _, w in REGION_DISTRIBUTION)
        if abs(actual - target) > tolerance:
            region_issues.append(
                f"{region}: ได้ {actual:.1%} เป้า {target:.1%}"
            )
    if region_issues:
        issues["region"] = region_issues

    # ตรวจ media_access — ต้องมีคนไม่เล่นโซเชียล
    no_social = sum(
        1 for a in agents if not a.get("media", {}).get("social_media", True)
    )
    if no_social == 0:
        issues["media_access"] = ["ไม่มี agent ที่ไม่เล่นโซเชียลเลย — ตัวอย่างเอียง"]
    else:
        pct = no_social / n
        if pct < 0.10:
            issues["media_access"] = [
                f"คนไม่เล่นโซเชียลมีแค่ {pct:.1%} — ต่ำเกินไป"
            ]

    return issues
