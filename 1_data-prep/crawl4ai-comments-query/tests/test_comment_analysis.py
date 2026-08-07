import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "comment_analysis.py"
SPEC = importlib.util.spec_from_file_location("comment_analysis", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class CommentAnalysisTests(unittest.TestCase):
    def test_sentiment_and_theme(self):
        result = MODULE.annotate_record(
            {
                "id": "1",
                "post_url": "https://www.facebook.com/example/posts/1",
                "comment_text": "แพงมาก ไม่คุ้ม แต่รสชาติอร่อย",
            }
        )
        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result["sentiment"]["label"], "negative")
        self.assertIn("price_value", result["themes"])
        self.assertIn("taste_quality", result["themes"])

    def test_quality_flag_preserves_but_excludes_merged_block(self):
        result = MODULE.annotate_record(
            {"id": "2", "post_url": "https://www.facebook.com/x/posts/2", "comment_text": "ก" * 2501}
        )
        self.assertIsNotNone(result)
        assert result is not None
        self.assertFalse(result["included_in_aggregate"])
        self.assertIn("possible_post_shell_or_merged_dom_block", result["quality_flags"])

    def test_run_writes_report_and_high_comment_subset(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "comments.jsonl"
            records = [
                {"id": str(i), "post_url": "https://www.facebook.com/page/posts/1", "comment_text": "อร่อย ชอบ"}
                for i in range(2)
            ]
            source.write_text("\n".join(json.dumps(record, ensure_ascii=False) for record in records) + "\n", encoding="utf-8")
            summary = MODULE.run(source, root / "analysis", min_high=2)
            self.assertEqual(summary["included_in_aggregate"], 2)
            self.assertTrue((root / "analysis/comments_report.md").exists())
            self.assertEqual(len((root / "analysis/comments_high_comment_annotated.jsonl").read_text().splitlines()), 2)


if __name__ == "__main__":
    unittest.main()
