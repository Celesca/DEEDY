import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from experiments.run_llm_exp123 import (
    Campaign,
    Job,
    PRIMARY_MODEL,
    build_prompt,
    parse_responses,
    record_metrics,
)


class LLMExperimentTests(unittest.TestCase):
    def setUp(self):
        self.campaign = Campaign(
            name="แคมเปญทดสอบ",
            positive=0.2,
            neutral=0.5,
            negative=0.3,
            platforms=("Facebook", "TikTok"),
            post_count=4,
            leaky_analysis="ข้อความสรุปลับจากผลลัพธ์เป้าหมาย",
        )

    def job(self, condition):
        return Job(PRIMARY_MODEL, condition, self.campaign, 1)

    def test_seed_prompt_excludes_target_outputs(self):
        system, user = build_prompt(self.job("seed_only_thai_context"), 3)
        combined = system + user
        self.assertNotIn("0.200", combined)
        self.assertNotIn(self.campaign.leaky_analysis, combined)
        self.assertNotIn("http", combined)

    def test_leaky_prompt_is_explicit_and_contains_target(self):
        system, user = build_prompt(self.job("leaky_all_source"), 3)
        combined = system + user
        self.assertIn("จงใจรั่วไหล", combined)
        self.assertIn("positive=0.200", combined)
        self.assertIn(self.campaign.leaky_analysis, combined)

    def test_fenced_json_and_metrics(self):
        responses = parse_responses(
            "```json\n{\"responses\":["
            "{\"text\":\"ดีนะ\",\"sentiment\":\"positive\",\"stance\":\"support\",\"narrative\":\"ชอบ\",\"sarcasm\":false},"
            "{\"text\":\"ขอรายละเอียด\",\"sentiment\":\"neutral\",\"stance\":\"question\",\"narrative\":\"ข้อมูล\",\"sarcasm\":false},"
            "{\"text\":\"ไม่คุ้ม\",\"sentiment\":\"negative\",\"stance\":\"oppose\",\"narrative\":\"ราคา\",\"sarcasm\":false}]}\n```"
        )
        record = {
            "status": "ok",
            "model": PRIMARY_MODEL,
            "condition": "seed_only_thai_context",
            "campaign": self.campaign.name,
            "seed": 1,
            "requested_samples": 3,
            "returned_samples": 3,
            "responses": responses,
            "latency_seconds": 1,
            "prompt_tokens": 10,
            "completion_tokens": 20,
            "cost_usd": 0.001,
        }
        metrics = record_metrics(record, self.campaign)
        self.assertEqual(metrics["schema_valid_share"], 1.0)
        self.assertEqual(metrics["narrative_count"], 3)
        self.assertGreater(metrics["thai_character_ratio"], 0.9)
        self.assertGreaterEqual(metrics["sentiment_js_distance"], 0)


if __name__ == "__main__":
    unittest.main()
