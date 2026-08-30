import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from experiments.run_llm_exp45 import (
    Job,
    PRIMARY_MODEL,
    Scenario,
    build_jobs,
    build_prompt,
    load_targets,
    markdown_cell,
    parse_agents,
    record_metrics,
    record_is_complete,
)


class LLMExperiment45Tests(unittest.TestCase):
    def test_markdown_cell_escapes_table_separator(self):
        self.assertEqual(markdown_cell("วิ่งแลกแว่น | Top Charoen"), "วิ่งแลกแว่น \\| Top Charoen")

    def setUp(self):
        self.scenario = Scenario(
            name="Parameter Gelato",
            baseline_message="ข้อความแคมเปญที่ไม่มีผลตอบรับจริง",
            clarity_message="ข้อความแคมเปญแบบชัดเจนที่ไม่มีผลตอบรับจริง",
            scenario_details={"category": "gelato"},
            source_urls=("https://example.com/source",),
        )

    def test_registered_matrix_has_eight_conditions_per_campaign_seed_model(self):
        jobs = build_jobs([PRIMARY_MODEL, "comparison/model"], [self.scenario], 2)
        self.assertEqual(len(jobs), 32)
        self.assertEqual(sum(job.experiment == "exp4_social_mechanism" for job in jobs), 24)
        self.assertEqual(sum(job.experiment == "exp5_application" for job in jobs), 8)

    def test_prompt_excludes_ground_truth(self):
        job = Job(
            "exp4_social_mechanism",
            PRIMARY_MODEL,
            self.scenario,
            1,
            "interest",
            "post_affiliation_proxy",
            "baseline",
        )
        system, user = build_prompt(job, 3)
        combined = system + user
        self.assertNotIn("0.162", combined)
        self.assertNotIn("Sentiment_Direction_Analysis", combined)
        self.assertNotIn("ความคิดเห็นจริง", self.scenario.baseline_message)
        self.assertIn("ห้ามอ้างว่าเห็นความคิดเห็นจริง", system)

    def test_parse_and_score_agents(self):
        agents = parse_agents(
            json.dumps(
                {
                    "agents": [
                        {
                            "agent_id": 1,
                            "persona": "ผู้ใช้หนึ่ง",
                            "action": "comment",
                            "text": "น่าสนใจ",
                            "sentiment": "positive",
                            "stance": "support",
                            "narrative": "value",
                            "rationale_summary": "ข้อมูลตรงกับความสนใจ",
                            "confidence": "medium",
                        },
                        {
                            "agent_id": 2,
                            "persona": "ผู้ใช้สอง",
                            "action": "silence",
                            "text": "",
                            "sentiment": "neutral",
                            "stance": "unclear",
                            "narrative": "details",
                            "rationale_summary": "ยังต้องการรายละเอียดเพิ่ม",
                            "confidence": "low",
                        },
                        {
                            "agent_id": 3,
                            "persona": "ผู้ใช้สาม",
                            "action": "share",
                            "text": "ส่งให้เพื่อนดู",
                            "sentiment": "negative",
                            "stance": "question",
                            "narrative": "conditions",
                            "rationale_summary": "เงื่อนไขยังไม่ชัดเจน",
                            "confidence": "medium",
                        },
                    ]
                },
                ensure_ascii=False,
            ),
            3,
        )
        record = {
            "experiment": "exp5_application",
            "model": PRIMARY_MODEL,
            "campaign": self.scenario.name,
            "seed": 1,
            "feed": "interest",
            "network": "post_affiliation_proxy",
            "variant": "baseline",
            "requested_agents": 3,
            "agents": agents,
        }
        metrics = record_metrics(record, (1 / 3, 1 / 3, 1 / 3))
        self.assertAlmostEqual(metrics["sentiment_js_distance"], 0.0)
        self.assertAlmostEqual(metrics["visible_action_rate"], 2 / 3)
        self.assertEqual(metrics["schema_valid_share"], 1.0)
        record["status"] = "ok"
        record["returned_agents"] = 3
        self.assertTrue(record_is_complete(record, 3))

    def test_target_loader_ignores_analysis_columns(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "summary.csv"
            path.write_text(
                "Topic,Positive_Ratio,Neutral_Ratio,Negative_Ratio,Sentiment_Direction_Analysis\n"
                "A,0.2,0.5,0.3,secret\nB,0.3,0.4,0.3,secret\nC,0.4,0.3,0.3,secret\n"
                "D,0.1,0.8,0.1,secret\nE,0.5,0.2,0.3,secret\n",
                encoding="utf-8",
            )
            targets = load_targets(path)
            self.assertEqual(targets["A"], (0.3, 0.5, 0.2))


if __name__ == "__main__":
    unittest.main()
