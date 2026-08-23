"""
สคริปต์สร้างประชากรสังเคราะห์ (Phase 4.1-4.2 / O2)

การทำงาน:
  1. สุ่ม demographic ตามสัดส่วน NSO (ผ่าน `core.population.generate_demographic`)
  2. ใช้ LLM สร้าง `base_personality` (บุคลิกภาพ, ความเชื่อ, ลักษณะนิสัย) ให้สอดคล้องกับ demographic
  3. ตรวจสอบสัดส่วนว่าตรงเป้าหรือไม่ (validate_distribution)
  4. บันทึกลง JSON

วิธีรัน:
  python scripts/bootstrap_population.py --count 200 --out data/population_200.json
"""
import argparse
import logging
import random
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict

# นำเข้า core module ให้ได้
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from core.llm import get_client, LLMError
from core.population import (
    generate_demographic,
    save_population,
    validate_distribution,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("bootstrap")


def _generate_personality_for_agent(agent_data: Dict[str, Any]) -> Dict[str, Any]:
    """เรียก LLM เพื่อสร้างบุคลิกภาพให้กับ agent ตาม demographic ที่สุ่มได้"""
    
    system_prompt = (
        "คุณคือผู้เชี่ยวชาญด้านพฤติกรรมศาสตร์และสังคมวิทยาของประเทศไทย "
        "หน้าที่ของคุณคือการสร้าง 'Archetype' หรือภาพตัวแทนของประชากรไทยตามข้อมูลประชากรศาสตร์ที่ให้มา "
        "ห้ามเลียนแบบบุคคลที่มีอยู่จริง (เพื่อเคารพ PDPA) ให้สร้างเป็นตัวละครสมมติที่มีความสมจริง\n\n"
        "บุคลิกภาพ (base_personality) ต้องครอบคลุม:\n"
        "1. ลักษณะนิสัยพื้นฐานและการใช้ชีวิต\n"
        "2. ความเชื่อหรือทัศนคติที่มีต่อสังคมและการเมือง (แบบกว้างๆ)\n"
        "3. ความสนใจหลัก (เช่น ปากท้อง, สิทธิมนุษยชน, ศาสนา, บันเทิง)\n"
        "4. สไตล์การพูดหรือการแสดงออก (เช่น สุภาพเกรงใจ, โผงผางตรงไปตรงมา, ชอบใช้คำศัพท์วัยรุ่น)"
    )

    media_info = agent_data["media"]
    media_str = []
    if media_info.get("social_media"): media_str.append("ใช้โซเชียลมีเดีย")
    if media_info.get("line"): media_str.append("ใช้ LINE")
    if media_info.get("tv"): media_str.append("ดูทีวีเป็นหลัก")
    if media_info.get("community"): media_str.append("พูดคุยกับคนในชุมชน/เพื่อนบ้าน")
    if not media_str:
        media_str.append("ไม่ค่อยรับข่าวสาร")

    user_prompt = f"""
ข้อมูลประชากรศาสตร์ (Demographic):
- อายุ: {agent_data['age']} ปี
- ภูมิภาค: {agent_data['region']}
- อาชีพ: {agent_data['occupation']}
- ระดับการศึกษา: {agent_data['education']}
- ระดับรายได้: {agent_data['income_level']}
- ช่องทางรับสื่อ: {', '.join(media_str)}

จงสร้างบุคลิกภาพ (base_personality) ความยาวประมาณ 2-4 ประโยค ให้ตอบกลับเป็น JSON:
{{
  "base_personality": "คำอธิบายบุคลิกภาพ..."
}}
"""
    client = get_client()
    try:
        response = client.complete_json(
            system=system_prompt,
            user=user_prompt,
            required_fields=["base_personality"]
        )
        agent_data["base_personality"] = response.get("base_personality", "บุคลิกภาพทั่วไปตามวัยและอาชีพ")
    except LLMError as e:
        logger.warning(f"LLM Error for agent {agent_data['agent_id']}: {e}")
        agent_data["base_personality"] = f"คนไทยวัย {agent_data['age']} ปี อาชีพ{agent_data['occupation']} รักสงบ"
    
    return agent_data


def main():
    parser = argparse.ArgumentParser(description="Bootstrap Thai Population")
    parser.add_argument("--count", type=int, default=10, help="จำนวนประชากรที่ต้องการสร้าง")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--out", type=str, default="data/population_test.json", help="Output JSON file")
    parser.add_argument("--workers", type=int, default=5, help="จำนวน Threads สำหรับเรียก LLM")
    
    args = parser.parse_args()
    
    rng = random.Random(args.seed)
    
    logger.info(f"Generating {args.count} agents (seed={args.seed})...")
    
    # 1. สุ่ม demographic (รวดเร็ว)
    base_agents = []
    for i in range(args.count):
        agent_id = f"agent_{i:04d}"
        demo = generate_demographic(rng, agent_id)
        base_agents.append(demo)
        
    # ตรวจสอบสัดส่วนก่อนสร้าง personality
    issues = validate_distribution(base_agents)
    if issues:
        logger.warning("Demographic distribution issues found:")
        for k, v in issues.items():
            for msg in v:
                logger.warning(f" - {msg}")
    else:
        logger.info("Demographic distribution looks good.")

    # 2. สร้าง base_personality ผ่าน LLM (Parallel)
    logger.info(f"Calling LLM to generate personalities (workers={args.workers})...")
    final_agents = []
    
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        future_to_agent = {executor.submit(_generate_personality_for_agent, agent): agent for agent in base_agents}
        
        count = 0
        for future in as_completed(future_to_agent):
            count += 1
            try:
                final_agent = future.result()
                final_agents.append(final_agent)
                if count % 10 == 0:
                    logger.info(f"Progress: {count}/{args.count} agents generated")
            except Exception as e:
                agent = future_to_agent[future]
                logger.error(f"Failed to generate for {agent['agent_id']}: {e}")
                
    # Sort by ID to maintain order consistency
    final_agents.sort(key=lambda x: x["agent_id"])
    
    # 3. บันทึกผล
    out_path = Path(__file__).parent.parent / args.out
    metadata = {
        "count": args.count,
        "seed": args.seed,
        "source_data": "NSO 2023 / ETDA 2023 (Provisional)"
    }
    
    save_population(final_agents, str(out_path), metadata)
    logger.info(f"Population successfully saved to {out_path}")


if __name__ == "__main__":
    main()
