import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "llm_comment_analysis.py"
SPEC = importlib.util.spec_from_file_location("llm_comment_analysis", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class LLMCommentAnalysisTests(unittest.TestCase):
    def test_parse_json_fenced_response(self):
        self.assertEqual(MODULE.parse_json_response("```json\n{\"annotations\": []}\n```"), {"annotations": []})

    def test_validate_annotation_normalizes_invalid_labels(self):
        value = MODULE.validate_annotation(
            {
                "id": "x",
                "sentiment": "unknown",
                "stance": "unknown",
                "cluster": "unknown",
                "emotions": ["not-an-emotion", "joy"],
                "sentiment_score": 9,
                "confidence": -1,
            },
            {"x"},
        )
        assert value is not None
        self.assertEqual(value["sentiment"], "neutral")
        self.assertEqual(value["stance"], "neutral")
        self.assertEqual(value["cluster"], "general_reaction")
        self.assertEqual(value["emotions"], ["joy"])
        self.assertEqual(value["sentiment_score"], 1.0)
        self.assertEqual(value["confidence"], 0.0)

    def test_load_records_deduplicates(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "comments.jsonl"
            record = {"id": "1", "post_url": "https://facebook.com/x", "comment_text": "อร่อย"}
            path.write_text(json.dumps(record, ensure_ascii=False) + "\n" + json.dumps(record, ensure_ascii=False) + "\n", encoding="utf-8")
            records, errors = MODULE.load_records(path)
            self.assertEqual(errors, 0)
            self.assertEqual(len(records), 1)


if __name__ == "__main__":
    unittest.main()
