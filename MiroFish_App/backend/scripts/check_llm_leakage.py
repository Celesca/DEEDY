import argparse
import sys
import os

# Add backend directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.llm import get_client

def probe_leakage(event_description: str, simulated_date: str):
    """
    Test if the LLM has pre-existing knowledge of the event that would constitute leakage.
    (Phase 7.7)
    """
    client = get_client()
    
    system_prompt = (
        f"คุณต้องตอบโดยอ้างอิงความรู้และบริบทสังคมถึงแค่ช่วงเวลา {simulated_date} เท่านั้น "
        f"ห้ามใช้ข้อมูลที่เกิดขึ้นหลังจากนี้เด็ดขาด"
    )
    
    user_prompt = f"คุณรู้ผลลัพธ์ของเหตุการณ์ต่อไปนี้หรือไม่? ถ้ามีข้อมูล ช่วยสรุปให้ฟังหน่อย:\n\n{event_description}"
    
    print(f"=== LEAKAGE PROBE ===")
    print(f"Cutoff Date: {simulated_date}")
    print(f"Event: {event_description}\n")
    print("Querying LLM...")
    
    try:
        response = client.complete(system_prompt=system_prompt, user_prompt=user_prompt)
        print("\n--- LLM RESPONSE ---")
        print(response)
        print("--------------------")
    except Exception as e:
        print(f"Error querying LLM: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Probe LLM for Temporal Leakage (Phase 7.7)")
    parser.add_argument("--event", type=str, required=True, help="Description of the event to test")
    parser.add_argument("--date", type=str, required=True, help="Simulated date cutoff (e.g. 'ตุลาคม 2563')")
    args = parser.parse_args()
    
    probe_leakage(args.event, args.date)
