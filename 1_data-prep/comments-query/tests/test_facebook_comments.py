import importlib.util
import json
import sys
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "facebook_comments.py"
SPEC = importlib.util.spec_from_file_location("facebook_comments", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class FacebookCommentsTests(unittest.TestCase):
    def test_detects_login_dialog_on_public_page_shell(self):
        page = """
        <html><head><title>Facebook</title></head><body>
          <form><input name="email"><input name="pass" type="password"></form>
        </body></html>
        """
        self.assertTrue(
            MODULE.is_authentication_page(
                "https://www.facebook.com/parameterthailand/posts/123", page
            )
        )

    def test_canonicalize_post_url(self):
        actual = MODULE.canonicalize_facebook_url(
            "https://m.facebook.com/example/posts/123/?fbclid=tracking"
        )
        self.assertEqual(actual, "https://www.facebook.com/example/posts/123")

    def test_canonicalize_story_url_keeps_identifiers(self):
        actual = MODULE.canonicalize_facebook_url(
            "https://www.facebook.com/story.php?story_fbid=99&id=42&fbclid=x"
        )
        self.assertEqual(
            actual,
            "https://www.facebook.com/story.php?story_fbid=99&id=42",
        )

    def test_rejects_non_facebook_or_non_post_url(self):
        self.assertIsNone(MODULE.canonicalize_facebook_url("https://example.com/posts/1"))
        self.assertIsNone(MODULE.canonicalize_facebook_url("https://facebook.com/login"))

    def test_discover_post_urls_deduplicates(self):
        page = """
        <a href="/page/posts/123?fbclid=a">one</a>
        <a href="https://m.facebook.com/page/posts/123">duplicate</a>
        <a href="https://example.com/news">external</a>
        <a href="/story.php?story_fbid=9&id=8">two</a>
        """
        self.assertEqual(
            MODULE.discover_post_urls(page, 10),
            [
                "https://www.facebook.com/page/posts/123",
                "https://www.facebook.com/story.php?story_fbid=9&id=8",
            ],
        )

    def test_extract_comments_from_injected_payload(self):
        payload = {
            "post_text": "ข่าวตัวอย่าง",
            "comments": [
                {
                    "raw_text": "สมชาย\nเห็นด้วยครับ\nถูกใจ\nตอบกลับ\n2 ชม.",
                    "author": "สมชาย",
                    "permalink": "https://facebook.com/page/posts/123?fbclid=x",
                },
                {
                    "raw_text": "สมชาย\nเห็นด้วยครับ\nถูกใจ",
                    "author": "สมชาย",
                    "permalink": "",
                },
            ],
        }
        encoded = json.dumps(payload, ensure_ascii=False).replace("<", "\\u003c")
        page = f'<script id="deedy-facebook-payload" type="application/json">{encoded}</script>'
        post_text, comments = MODULE.extract_comments(page, 100)
        self.assertEqual(post_text, "ข่าวตัวอย่าง")
        self.assertEqual(len(comments), 1)
        self.assertEqual(comments[0].text, "เห็นด้วยครับ")
        self.assertEqual(comments[0].author, "สมชาย")


if __name__ == "__main__":
    unittest.main()
