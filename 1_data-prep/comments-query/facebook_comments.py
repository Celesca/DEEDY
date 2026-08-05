#!/usr/bin/env python3
"""Query public Facebook posts and collect visible comments with Crawl4AI.

The crawler reuses a browser profile created by the user with Crawl4AI's
profile manager. It does not accept Facebook passwords or raw cookie values,
and it does not attempt to solve checkpoints or CAPTCHAs.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import html
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import parse_qsl, quote_plus, urlencode, urljoin, urlsplit, urlunsplit

FACEBOOK_ORIGIN = "https://www.facebook.com"
DEFAULT_OUTPUT = Path(__file__).resolve().parent / "output" / "facebook_comments.jsonl"

POST_PATH_PATTERNS = (
    re.compile(r"/[^/?#]+/posts/(?:pfbid)?[A-Za-z0-9_-]+", re.IGNORECASE),
    re.compile(r"/groups/[^/?#]+/posts/[A-Za-z0-9_-]+", re.IGNORECASE),
    re.compile(r"/permalink\.php", re.IGNORECASE),
    re.compile(r"/story\.php", re.IGNORECASE),
    re.compile(r"/photo(?:\.php|/)", re.IGNORECASE),
    re.compile(r"/(?:watch|videos|reel)/", re.IGNORECASE),
)

UI_ONLY_LINES = {
    "like",
    "reply",
    "share",
    "edited",
    "see translation",
    "view more replies",
    "ถูกใจ",
    "ตอบกลับ",
    "แชร์",
    "แก้ไขแล้ว",
    "ดูคำแปล",
    "ดูการตอบกลับเพิ่มเติม",
}

TIME_LINE = re.compile(
    r"^(?:\d+\s*(?:s|m|h|d|w|y|sec|min|hr|day|week|year)s?|"
    r"\d+\s*(?:วินาที|นาที|ชม\.?|ชั่วโมง|วัน|สัปดาห์|เดือน|ปี)|"
    r"just now|เมื่อสักครู่)$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ExtractedComment:
    text: str
    raw_text: str
    author: str | None
    permalink: str | None


class FacebookPageParser(HTMLParser):
    """Collect links, the title, and the injected JSON payload from a page."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[str] = []
        self.title_parts: list[str] = []
        self.payload_parts: list[str] = []
        self._in_title = False
        self._in_payload = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "a" and attributes.get("href"):
            self.links.append(str(attributes["href"]))
        elif tag == "title":
            self._in_title = True
        elif tag == "script" and attributes.get("id") == "deedy-facebook-payload":
            self._in_payload = True

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False
        elif tag == "script" and self._in_payload:
            self._in_payload = False

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title_parts.append(data)
        if self._in_payload:
            self.payload_parts.append(data)

    @property
    def title(self) -> str:
        return " ".join(part.strip() for part in self.title_parts if part.strip())

    @property
    def payload(self) -> str:
        return "".join(self.payload_parts).strip()


def parse_page(page_html: str) -> FacebookPageParser:
    parser = FacebookPageParser()
    parser.feed(page_html or "")
    parser.close()
    return parser


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def canonicalize_facebook_url(raw_url: str) -> str | None:
    """Return a stable Facebook post URL, or None for non-post links."""
    if not raw_url:
        return None

    raw_url = html.unescape(raw_url.strip())
    absolute = urljoin(FACEBOOK_ORIGIN, raw_url)
    parts = urlsplit(absolute)
    host = parts.netloc.lower().split(":", 1)[0]
    if host not in {"facebook.com", "www.facebook.com", "m.facebook.com"}:
        return None
    if parts.path.startswith(("/login", "/checkpoint", "/l.php")):
        return None
    if not any(pattern.search(parts.path) for pattern in POST_PATH_PATTERNS):
        return None

    kept_query: list[tuple[str, str]] = []
    allowed_keys = {"story_fbid", "id", "fbid", "v", "set"}
    for key, value in parse_qsl(parts.query, keep_blank_values=False):
        if key in allowed_keys:
            kept_query.append((key, value))

    path = re.sub(r"/{2,}", "/", parts.path).rstrip("/") or "/"
    return urlunsplit(("https", "www.facebook.com", path, urlencode(kept_query), ""))


def discover_post_urls(page_html: str, limit: int) -> list[str]:
    """Discover unique post permalinks from a rendered Facebook search page."""
    if limit <= 0:
        return []
    page = parse_page(page_html)
    discovered: list[str] = []
    seen: set[str] = set()
    for href in page.links:
        normalized = canonicalize_facebook_url(href)
        if normalized and normalized not in seen:
            seen.add(normalized)
            discovered.append(normalized)
            if len(discovered) >= limit:
                break
    return discovered


def _clean_lines(raw_text: str) -> list[str]:
    lines: list[str] = []
    for raw_line in raw_text.replace("\u200b", "").splitlines():
        line = re.sub(r"\s+", " ", raw_line).strip()
        if not line:
            continue
        lowered = line.casefold()
        if lowered in UI_ONLY_LINES or TIME_LINE.fullmatch(line):
            continue
        if re.fullmatch(r"[·•]\s*", line):
            continue
        lines.append(line)
    return lines


def clean_comment(raw_text: str, explicit_author: str | None = None) -> ExtractedComment | None:
    """Remove common Facebook action/time labels from an accessible text block."""
    lines = _clean_lines(raw_text)
    if not lines:
        return None

    author = re.sub(r"\s+", " ", explicit_author or "").strip() or None
    if author and lines and lines[0].casefold() == author.casefold():
        lines = lines[1:]
    elif not author and len(lines) >= 2 and len(lines[0]) <= 80:
        # Facebook's accessible comment block normally starts with the author.
        author = lines.pop(0)

    text = "\n".join(lines).strip()
    if not text or text.casefold() in UI_ONLY_LINES:
        return None
    return ExtractedComment(text=text, raw_text=raw_text.strip(), author=author, permalink=None)


def extract_comments(page_html: str, max_comments: int) -> tuple[str | None, list[ExtractedComment]]:
    """Read the JSON payload injected by the Crawl4AI interaction script."""
    encoded_payload = parse_page(page_html).payload
    if not encoded_payload:
        return None, []

    try:
        payload = json.loads(encoded_payload)
    except (TypeError, json.JSONDecodeError):
        return None, []

    post_text = payload.get("post_text") or None
    if max_comments <= 0:
        return post_text, []
    comments: list[ExtractedComment] = []
    seen: set[str] = set()
    for item in payload.get("comments", []):
        if not isinstance(item, dict):
            continue
        parsed = clean_comment(
            str(item.get("raw_text") or ""),
            explicit_author=str(item.get("author") or "") or None,
        )
        if parsed is None:
            continue
        permalink = canonicalize_facebook_url(str(item.get("permalink") or ""))
        key = re.sub(r"\s+", " ", parsed.text).casefold()
        if key in seen:
            continue
        seen.add(key)
        comments.append(
            ExtractedComment(
                text=parsed.text,
                raw_text=parsed.raw_text,
                author=parsed.author,
                permalink=permalink,
            )
        )
        if len(comments) >= max_comments:
            break
    return post_text, comments


def make_interaction_script(scroll_rounds: int, click_rounds: int) -> str:
    """Build JavaScript that expands visible comment controls and serializes the DOM.

    Selectors use accessible roles, labels, and stable post-message attributes rather
    than Facebook's generated class names. Facebook changes its DOM frequently, so
    this script intentionally keeps the extraction payload simple and auditable.
    """
    return rf"""
return await (async () => {{
  const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
  const visible = (node) => {{
    const rect = node.getBoundingClientRect();
    const style = window.getComputedStyle(node);
    return rect.width > 0 && rect.height > 0 && style.visibility !== 'hidden';
  }};
  const expansionPattern = /(?:view|see|load|more|previous).*?(?:comment|repl)|(?:ดู|โหลด).*?(?:ความคิดเห็น|ความเห็น|การตอบกลับ)|ความคิดเห็นก่อนหน้า|^\s*\d[\d,.]*\s*(?:comments?|replies)\s*$|^\s*(?:ความคิดเห็น|ความเห็น|การตอบกลับ)\s*\d[\d,.]*\s*(?:รายการ)?\s*$/i;
  const moreTextPattern = /^(?:see more|more|ดูเพิ่มเติม|เพิ่มเติม)$/i;

  for (let round = 0; round < {int(click_rounds)}; round += 1) {{
    const controls = [...document.querySelectorAll('button, [role="button"]')]
      .filter((node) => visible(node) && expansionPattern.test((node.innerText || node.getAttribute('aria-label') || '').trim()))
      .slice(0, 12);
    if (!controls.length) break;
    for (const control of controls) {{
      try {{ control.click(); await sleep(450); }} catch (_) {{}}
    }}
    await sleep(900);
  }}

  for (const control of [...document.querySelectorAll('button, [role="button"]')]) {{
    const label = (control.innerText || control.getAttribute('aria-label') || '').trim();
    if (visible(control) && moreTextPattern.test(label)) {{
      try {{ control.click(); }} catch (_) {{}}
    }}
  }}

  for (let round = 0; round < {int(scroll_rounds)}; round += 1) {{
    window.scrollBy(0, Math.max(window.innerHeight * 0.85, 700));
    await sleep(800);
  }}

  const postMessage = document.querySelector('[data-ad-preview="message"], [data-ad-comet-preview="message"]');
  const comments = [];
  const articles = [...document.querySelectorAll('[role="article"]')];
  for (const article of articles) {{
    if (article === postMessage || article.contains(postMessage)) continue;
    const rawText = (article.innerText || '').trim();
    if (!rawText) continue;
    const aria = article.getAttribute('aria-label') || '';
    const parentArticle = article.parentElement && article.parentElement.closest('[role="article"]');
    const hasCommentPermalink = Boolean(article.querySelector('a[href*="comment_id="], a[href*="reply_comment_id="]'));
    // On direct post pages, Facebook now also renders top-level comments as
    // sibling articles without a useful aria-label. The post article was
    // excluded above, so remaining text-bearing articles are comment candidates.
    const looksLikeComment = Boolean(parentArticle) || hasCommentPermalink ||
      /comment|reply|ความคิดเห็น|ความเห็น|ตอบกลับ/i.test(aria) || Boolean(rawText);
    if (!looksLikeComment) continue;

    const profileLink = article.querySelector('a[role="link"] strong, a[role="link"] span');
    const permalinkNode = [...article.querySelectorAll('a[href]')].find((a) =>
      /\/posts\/|story_fbid=|\/permalink\.php|\/photo|\/videos\/|\/reel\//i.test(a.getAttribute('href') || '')
    );
    comments.push({{
      raw_text: rawText,
      author: profileLink ? (profileLink.innerText || '').trim() : '',
      permalink: permalinkNode ? permalinkNode.href : ''
    }});
  }}

  const payload = {{
    page_url: location.href,
    title: document.title,
    post_text: postMessage ? (postMessage.innerText || '').trim() : '',
    comments,
    diagnostics: {{
      article_count: articles.length,
      comment_permalink_count: document.querySelectorAll('a[href*="comment_id="], a[href*="reply_comment_id="]').length,
      dialog_count: document.querySelectorAll('[role="dialog"]').length,
      login_form_count: document.querySelectorAll('form[action*="login"], input[name="email"]').length
    }}
  }};
  document.querySelector('#deedy-facebook-payload')?.remove();
  const payloadNode = document.createElement('script');
  payloadNode.id = 'deedy-facebook-payload';
  payloadNode.type = 'application/json';
  payloadNode.textContent = JSON.stringify(payload).replace(/</g, '\u003c');
  document.body.appendChild(payloadNode);
}})();
"""


def is_authentication_page(url: str, page_html: str) -> bool:
    parts = urlsplit(url or "")
    if parts.path.startswith(("/login", "/checkpoint", "/recover")):
        return True
    title = parse_page(page_html).title.casefold()
    if title in {"log in to facebook", "เข้าสู่ระบบ facebook"}:
        return True
    # Facebook can show a public-page shell with a login dialog while keeping
    # the requested URL and a generic title. Detect stable login form fields.
    return bool(
        re.search(r'<input\b[^>]*\bname=["\']email["\']', page_html, re.IGNORECASE)
        and re.search(r'<input\b[^>]*\bname=["\']pass["\']', page_html, re.IGNORECASE)
    )


def record_id(post_url: str, comment_text: str) -> str:
    payload = f"{post_url}\0{re.sub(r'\s+', ' ', comment_text).strip()}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]


def load_seen_ids(path: Path) -> set[str]:
    seen: set[str] = set()
    if not path.exists():
        return seen
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            try:
                value = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(value, dict) and value.get("id"):
                seen.add(str(value["id"]))
    return seen


def append_jsonl(path: Path, records: Iterable[dict[str, Any]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with path.open("a", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
            written += 1
        handle.flush()
    return written


async def open_crawler(profile: Path, headless: bool, verbose: bool):
    try:
        from crawl4ai import AsyncWebCrawler, BrowserConfig
    except ImportError as exc:
        raise RuntimeError(
            "Crawl4AI is not installed. Run: pip install -r requirements.txt && crawl4ai-setup"
        ) from exc

    config = BrowserConfig(
        browser_type="chromium",
        headless=headless,
        use_managed_browser=True,
        use_persistent_context=True,
        user_data_dir=str(profile),
        viewport_width=1440,
        viewport_height=1200,
        verbose=verbose,
        extra_args=["--disable-notifications"],
    )
    return AsyncWebCrawler(config=config)


async def crawl_page(
    crawler: Any,
    url: str,
    *,
    locale: str,
    scroll_rounds: int,
    click_rounds: int,
    verbose: bool,
) -> Any:
    from crawl4ai import CacheMode, CrawlerRunConfig

    config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        word_count_threshold=1,
        wait_until="domcontentloaded",
        page_timeout=90_000,
        delay_before_return_html=2.0,
        locale=locale,
        timezone_id="Asia/Bangkok",
        js_code=make_interaction_script(scroll_rounds, click_rounds),
        verbose=verbose,
    )
    return await crawler.arun(url=url, config=config)


async def check_auth(args: argparse.Namespace) -> int:
    crawler = await open_crawler(args.profile, args.headless, args.verbose)
    async with crawler:
        result = await crawl_page(
            crawler,
            f"{FACEBOOK_ORIGIN}/me",
            locale=args.locale,
            scroll_rounds=0,
            click_rounds=0,
            verbose=args.verbose,
        )
    final_url = str(getattr(result, "url", "") or "")
    page_html = str(getattr(result, "html", "") or "")
    if not getattr(result, "success", False) or is_authentication_page(final_url, page_html):
        print("Facebook authentication is not available in this profile.", file=sys.stderr)
        return 2
    print(f"Authentication profile is usable: {args.profile}")
    return 0


async def collect_post(
    crawler: Any,
    post_url: str,
    *,
    query: str | None,
    args: argparse.Namespace,
    seen_ids: set[str],
) -> tuple[int, int]:
    result = await crawl_page(
        crawler,
        post_url,
        locale=args.locale,
        scroll_rounds=args.scroll_rounds,
        click_rounds=args.click_rounds,
        verbose=args.verbose,
    )
    final_url = str(getattr(result, "url", "") or post_url)
    page_html = str(getattr(result, "html", "") or "")
    if not getattr(result, "success", False):
        message = str(getattr(result, "error_message", "crawl failed") or "crawl failed")
        raise RuntimeError(f"Failed to crawl {post_url}: {message}")
    if is_authentication_page(final_url, page_html):
        raise RuntimeError(
            "Facebook redirected to login/checkpoint. Recreate or refresh the Crawl4AI profile."
        )

    if args.verbose:
        parsed_page = parse_page(page_html)
        payload_count = 0
        diagnostics: dict[str, Any] = {}
        if parsed_page.payload:
            try:
                payload_data = json.loads(parsed_page.payload)
                payload_count = len(payload_data.get("comments", []))
                diagnostics = payload_data.get("diagnostics", {})
            except (AttributeError, json.JSONDecodeError):
                pass
        print(
            f"  extraction diagnostic: html_bytes={len(page_html)}; "
            f"payload_bytes={len(parsed_page.payload)}; candidates={payload_count}; "
            f"dom={diagnostics}"
        )

    post_text, comments = extract_comments(page_html, args.max_comments)
    collected_at = utc_now()
    records: list[dict[str, Any]] = []
    for index, comment in enumerate(comments, start=1):
        item_id = record_id(post_url, comment.text)
        if item_id in seen_ids:
            continue
        record: dict[str, Any] = {
            "id": item_id,
            "record_type": "facebook_comment",
            "query": query,
            "post_url": canonicalize_facebook_url(final_url) or post_url,
            "comment_permalink": comment.permalink,
            "comment_index": index,
            "comment_text": comment.text,
            "post_text": post_text,
            "collected_at": collected_at,
            "locale": args.locale,
            "collector": "crawl4ai",
        }
        if args.include_author:
            record["author_display_name"] = comment.author
        records.append(record)
        seen_ids.add(item_id)

    return len(comments), append_jsonl(args.output, records)


async def run_post(args: argparse.Namespace) -> int:
    post_url = canonicalize_facebook_url(args.post_url)
    if not post_url:
        print("--post-url must be a Facebook post/permalink/video/reel URL.", file=sys.stderr)
        return 2

    seen_ids = load_seen_ids(args.output)
    crawler = await open_crawler(args.profile, args.headless, args.verbose)
    async with crawler:
        found, written = await collect_post(
            crawler, post_url, query=None, args=args, seen_ids=seen_ids
        )
    print(f"Comments visible: {found}; new records written: {written}; output: {args.output}")
    return 0


async def run_search(args: argparse.Namespace) -> int:
    search_url = f"{FACEBOOK_ORIGIN}/search/posts/?q={quote_plus(args.query)}"
    seen_ids = load_seen_ids(args.output)
    crawler = await open_crawler(args.profile, args.headless, args.verbose)
    async with crawler:
        search_result = await crawl_page(
            crawler,
            search_url,
            locale=args.locale,
            scroll_rounds=args.search_scroll_rounds,
            click_rounds=0,
            verbose=args.verbose,
        )
        final_url = str(getattr(search_result, "url", "") or search_url)
        page_html = str(getattr(search_result, "html", "") or "")
        if not getattr(search_result, "success", False):
            message = str(getattr(search_result, "error_message", "search crawl failed"))
            raise RuntimeError(message)
        if is_authentication_page(final_url, page_html):
            raise RuntimeError(
                "Facebook redirected to login/checkpoint. Recreate or refresh the Crawl4AI profile."
            )

        post_urls = discover_post_urls(page_html, args.max_posts)
        if not post_urls:
            print(
                "No Facebook post permalinks were found. Try a more specific query, run with "
                "--show-browser, or verify that the profile can see Facebook search results.",
                file=sys.stderr,
            )
            return 1

        if args.discover_only:
            print(f"Posts discovered: {len(post_urls)}")
            for post_url in post_urls:
                print(post_url)
            return 0

        visible_total = 0
        written_total = 0
        failed = 0
        for position, post_url in enumerate(post_urls, start=1):
            print(f"[{position}/{len(post_urls)}] {post_url}")
            try:
                found, written = await collect_post(
                    crawler,
                    post_url,
                    query=args.query,
                    args=args,
                    seen_ids=seen_ids,
                )
            except RuntimeError as exc:
                failed += 1
                print(f"  warning: {exc}", file=sys.stderr)
                continue
            visible_total += found
            written_total += written
            print(f"  comments visible: {found}; new: {written}")

    print(
        f"Posts discovered: {len(post_urls)}; failed: {failed}; comments visible: "
        f"{visible_total}; new records written: {written_total}; output: {args.output}"
    )
    return 0 if written_total or visible_total else 1


async def run_page(args: argparse.Namespace) -> int:
    """Discover post permalinks from a Facebook Page and collect comments."""
    parts = urlsplit(args.page_url)
    host = parts.netloc.lower().split(":", 1)[0]
    if parts.scheme not in {"http", "https"} or host not in {
        "facebook.com",
        "www.facebook.com",
        "m.facebook.com",
    }:
        print("--page-url must be a Facebook Page URL.", file=sys.stderr)
        return 2

    page_url = urlunsplit(("https", "www.facebook.com", parts.path.rstrip("/"), "", ""))
    seen_ids = load_seen_ids(args.output)
    crawler = await open_crawler(args.profile, args.headless, args.verbose)
    async with crawler:
        page_result = await crawl_page(
            crawler,
            page_url,
            locale=args.locale,
            scroll_rounds=args.page_scroll_rounds,
            click_rounds=0,
            verbose=args.verbose,
        )
        final_url = str(getattr(page_result, "url", "") or page_url)
        page_html = str(getattr(page_result, "html", "") or "")
        if not getattr(page_result, "success", False):
            message = str(getattr(page_result, "error_message", "page crawl failed"))
            raise RuntimeError(message)
        if is_authentication_page(final_url, page_html):
            raise RuntimeError(
                "Facebook redirected to login/checkpoint. Recreate or refresh the Crawl4AI profile."
            )

        post_urls = discover_post_urls(page_html, args.max_posts)
        if not post_urls:
            print(
                "No Facebook post permalinks were found on the Page. Run with --show-browser "
                "or provide a known post URL with the post command.",
                file=sys.stderr,
            )
            return 1

        visible_total = 0
        written_total = 0
        failed = 0
        for position, post_url in enumerate(post_urls, start=1):
            print(f"[{position}/{len(post_urls)}] {post_url}")
            try:
                found, written = await collect_post(
                    crawler,
                    post_url,
                    query=page_url,
                    args=args,
                    seen_ids=seen_ids,
                )
            except RuntimeError as exc:
                failed += 1
                print(f"  warning: {exc}", file=sys.stderr)
                continue
            visible_total += found
            written_total += written
            print(f"  comments visible: {found}; new: {written}")

    print(
        f"Posts discovered: {len(post_urls)}; failed: {failed}; comments visible: "
        f"{visible_total}; new records written: {written_total}; output: {args.output}"
    )
    return 0 if written_total or visible_total else 1


def positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return parsed


def nonnegative_int(value: str) -> int:
    parsed = int(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("must be zero or greater")
    return parsed


def add_runtime_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--profile",
        type=lambda value: Path(value).expanduser().resolve(),
        required=True,
        help="Crawl4AI persistent profile directory containing a manual Facebook login.",
    )
    parser.add_argument(
        "--output",
        type=lambda value: Path(value).expanduser().resolve(),
        default=DEFAULT_OUTPUT,
        help=f"Append-only JSONL output (default: {DEFAULT_OUTPUT}).",
    )
    parser.add_argument("--locale", default="th-TH", help="Browser locale (default: th-TH).")
    parser.add_argument(
        "--show-browser",
        action="store_false",
        dest="headless",
        help="Show Chromium while crawling; useful when diagnosing selectors or login state.",
    )
    parser.set_defaults(headless=True)
    parser.add_argument("--verbose", action="store_true", help="Enable Crawl4AI logs.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Collect visible comments from Facebook posts related to a news query."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    auth_parser = subparsers.add_parser("check-auth", help="Verify the saved Facebook profile.")
    add_runtime_options(auth_parser)

    post_parser = subparsers.add_parser("post", help="Collect comments from one post URL.")
    add_runtime_options(post_parser)
    post_parser.add_argument("--post-url", required=True, help="Facebook post URL.")
    post_parser.add_argument("--max-comments", type=positive_int, default=100)
    post_parser.add_argument("--scroll-rounds", type=nonnegative_int, default=8)
    post_parser.add_argument("--click-rounds", type=nonnegative_int, default=6)
    post_parser.add_argument(
        "--include-author",
        action="store_true",
        help="Include visible display names. Disabled by default for data minimization.",
    )

    search_parser = subparsers.add_parser(
        "search", help="Search Facebook posts and collect their visible comments."
    )
    add_runtime_options(search_parser)
    search_parser.add_argument(
        "--query",
        required=True,
        help="News headline, keywords, or canonical news URL to search on Facebook.",
    )
    search_parser.add_argument("--max-posts", type=positive_int, default=5)
    search_parser.add_argument("--max-comments", type=positive_int, default=100)
    search_parser.add_argument("--search-scroll-rounds", type=nonnegative_int, default=6)
    search_parser.add_argument("--scroll-rounds", type=nonnegative_int, default=8)
    search_parser.add_argument("--click-rounds", type=nonnegative_int, default=6)
    search_parser.add_argument(
        "--discover-only",
        action="store_true",
        help="Print discovered post URLs without crawling comments.",
    )
    search_parser.add_argument(
        "--include-author",
        action="store_true",
        help="Include visible display names. Disabled by default for data minimization.",
    )

    page_parser = subparsers.add_parser(
        "page", help="Discover posts on a Facebook Page and collect their visible comments."
    )
    add_runtime_options(page_parser)
    page_parser.add_argument("--page-url", required=True, help="Facebook Page URL.")
    page_parser.add_argument("--max-posts", type=positive_int, default=10)
    page_parser.add_argument("--max-comments", type=positive_int, default=100)
    page_parser.add_argument("--page-scroll-rounds", type=nonnegative_int, default=8)
    page_parser.add_argument("--scroll-rounds", type=nonnegative_int, default=8)
    page_parser.add_argument("--click-rounds", type=nonnegative_int, default=6)
    page_parser.add_argument(
        "--include-author",
        action="store_true",
        help="Include visible display names. Disabled by default for data minimization.",
    )
    return parser


async def async_main(args: argparse.Namespace) -> int:
    if not args.profile.exists() or not args.profile.is_dir():
        print(f"Profile directory does not exist: {args.profile}", file=sys.stderr)
        return 2
    if args.command == "check-auth":
        return await check_auth(args)
    if args.command == "post":
        return await run_post(args)
    if args.command == "search":
        return await run_search(args)
    if args.command == "page":
        return await run_page(args)
    return 2


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return asyncio.run(async_main(args))
    except KeyboardInterrupt:
        print("Interrupted.", file=sys.stderr)
        return 130
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
