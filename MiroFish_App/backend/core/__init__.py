"""
MiroFish TH (DEEDY) — เครื่องยนต์จำลองความเห็นและพฤติกรรมของสังคมไทย

โครงสร้าง (ดู PLAN.md):
    config.py      ตั้งค่าจาก .env
    llm.py         เรียก LLM ผ่าน openai SDK ปิด chain-of-thought (D2, D8)
    actions.py     action space ระดับสังคม รวมพฤติกรรมออฟไลน์ (C2)
    expression.py  แปลงความคิดเป็นการกระทำ ด้วยโค้ด ไม่ใช่ LLM (D10)
    memory_stream.py  ความจำ + RAG
    agent.py       agent สองชั้น private_opinion / public_expression (C1, D7)
    environment.py เครือข่ายและการแพร่อารมณ์
"""

__all__ = [
    "actions",
    "agent",
    "config",
    "environment",
    "expression",
    "llm",
    "memory_stream",
]
