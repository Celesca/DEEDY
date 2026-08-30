import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from experiments.run_llm_exp45 import Scenario
from experiments.run_llm_judge_exp45 import (
    DIMENSIONS,
    JudgeJob,
    PairJob,
    parse_judgment,
    record_complete,
    sanitize_comment,
)


class LLMJudgeExperiment45Tests(unittest.TestCase):
    def make_pair(self):
        return PairJob(
            pair_id="pair-1",
            synthetic_job_key="synthetic-1",
            experiment="exp5_application",
            generator_model="generator/model",
            campaign="Parameter Gelato",
            seed=1,
            feed="interest",
            network="post_affiliation_proxy",
            variant="baseline",
            real_platform="Facebook",
            real_text="ของจริงน่าสนใจ",
            real_comment_sha256="r" * 64,
            real_locator_sha256="l" * 64,
            synthetic_text="ข้อความจำลอง",
            synthetic_text_sha256="s" * 64,
            synthetic_action="comment",
            synthetic_agent_id="1",
            scenario=Scenario(
                name="Parameter Gelato",
                baseline_message="ข้อมูลแคมเปญ",
                clarity_message="ข้อมูลชัดเจน",
                scenario_details={"category": "gelato"},
                source_urls=(),
            ),
        )

    def test_sanitizer_redacts_direct_identifiers(self):
        value, truncated = sanitize_comment(
            "ทัก @someone โทร 081-234-5678 test@example.com https://example.com"
        )
        self.assertFalse(truncated)
        self.assertNotIn("@someone", value)
        self.assertNotIn("081-234-5678", value)
        self.assertNotIn("test@example.com", value)
        self.assertNotIn("https://", value)
        self.assertIn("[MENTION]", value)
        self.assertIn("[PHONE]", value)
        self.assertIn("[EMAIL]", value)
        self.assertIn("[URL]", value)

    def test_orientations_reverse_sources(self):
        pair = self.make_pair()
        first = JudgeJob(pair, 0)
        second = JudgeJob(pair, 1)
        self.assertNotEqual(first.a_source, second.a_source)
        self.assertEqual(first.a_source, second.b_source)

    def test_parse_maps_preference_to_source(self):
        job = JudgeJob(self.make_pair(), 0)
        block = {
            **{dimension: 4 for dimension in DIMENSIONS},
            "sentiment": "neutral",
            "stance": "question",
        }
        parsed = parse_judgment(
            json.dumps(
                {
                    "comment_a": block,
                    "comment_b": block,
                    "more_likely_real": "A",
                    "evidence_summary": "A uses more colloquial wording without quoting it.",
                }
            ),
            job,
        )
        self.assertEqual(parsed["mapped_preference"], job.a_source)
        record = {"status": "ok", **parsed}
        self.assertTrue(record_complete(record))

    def test_parse_rejects_out_of_range_score(self):
        job = JudgeJob(self.make_pair(), 0)
        block = {
            **{dimension: 4 for dimension in DIMENSIONS},
            "sentiment": "neutral",
            "stance": "question",
        }
        block["thai_naturalness"] = 7
        with self.assertRaises(ValueError):
            parse_judgment(
                json.dumps(
                    {
                        "comment_a": block,
                        "comment_b": {**block, "thai_naturalness": 4},
                        "more_likely_real": "tie",
                        "evidence_summary": "The observable cues are similar.",
                    }
                ),
                job,
            )

    def test_mixed_sentiment_maps_to_neutral(self):
        job = JudgeJob(self.make_pair(), 0)
        block = {
            **{dimension: 4 for dimension in DIMENSIONS},
            "sentiment": "mixed",
            "stance": "mixed",
        }
        parsed = parse_judgment(
            json.dumps(
                {
                    "comment_a": block,
                    "comment_b": block,
                    "more_likely_real": "tie",
                    "evidence_summary": "Both contain mixed observable cues.",
                }
            ),
            job,
        )
        self.assertEqual(parsed["scores"]["real"]["sentiment"], "neutral")
        self.assertTrue(parsed["scores"]["real"]["sentiment_was_mixed"])


if __name__ == "__main__":
    unittest.main()
