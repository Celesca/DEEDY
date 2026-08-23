import os
import json
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from apify_client import ApifyClient
from dotenv import load_dotenv

load_dotenv()

import sys

# Ensure UTF-8 output encoding for Windows terminal compatibility
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# ==========================================
# 1. Pydantic Output Schemas
# ==========================================

class ExtractedComment(BaseModel):
    comment_id: str
    platform: str
    post_url: str
    author: str
    text: str
    likes_count: int = 0
    parent_comment_id: Optional[str] = None
    timestamp: str

class SocialPostCommentsResult(BaseModel):
    topic: str
    platform: str
    post_url: str
    total_comments: int
    comments: List[ExtractedComment]

# ==========================================
# Helper Functions
# ==========================================

def safe_str(val: Any, default: str = "") -> str:
    """
    Safely converts any raw input value (including dicts, lists, None) 
    to a sanitized string primitive, avoiding Pydantic 'Object receive' warnings/errors.
    """
    if val is None:
        return default
    if isinstance(val, str):
        return val.strip()
    if isinstance(val, (int, float, bool)):
        return str(val).strip()
    if isinstance(val, dict):
        for k in ("name", "uniqueId", "nickname", "username", "id", "text", "val", "value"):
            if k in val and isinstance(val[k], (str, int)):
                return str(val[k]).strip()
        return default
    return default

def safe_int(val: Any, default: int = 0) -> int:
    """Safely converts any raw input value to an integer."""
    if val is None:
        return default
    if isinstance(val, int):
        return val
    if isinstance(val, float):
        return int(val)
    if isinstance(val, str):
        val_clean = val.replace(",", "").strip()
        if val_clean.isdigit():
            return int(val_clean)
        try:
            return int(float(val_clean))
        except (ValueError, TypeError):
            return default
    if isinstance(val, dict):
        for k in ("count", "diggCount", "likesCount", "likeCount", "value"):
            if k in val:
                return safe_int(val[k], default)
    return default

def detect_platform(url: str) -> Optional[str]:
    """Detects platform based on URL string."""
    url_lower = url.lower()
    if "facebook.com" in url_lower or "fb.watch" in url_lower or "fb.com" in url_lower:
        return "Facebook"
    elif "instagram.com" in url_lower:
        return "Instagram"
    elif "tiktok.com" in url_lower:
        return "TikTok"
    return None

# ==========================================
# 2. Apify Crawler Wrapper Class
# ==========================================

class ApifySocialCommentCrawler:
    """
    Wrapper for Apify Actors to scrape Facebook, Instagram, and TikTok comments.
    - Facebook Actor: 'apify/facebook-comments-scraper'
    - Instagram Actor: 'apify/instagram-comment-scraper'
    - TikTok Actor: 'clockworks/tiktok-comments-scraper' (or 'clockworks/tiktok-scraper')
    """

    def __init__(self, api_token: Optional[str] = None):
        token = api_token or os.getenv("APIFY_API_TOKEN")
        if not token:
            raise ValueError("Missing APIFY_API_TOKEN environment variable.")
        self.client = ApifyClient(token)

    def scrape_facebook_comments(
        self, post_url: str, topic: str, max_comments: int = 100
    ) -> SocialPostCommentsResult:
        """Scrapes Facebook post comments using Apify's official FB Comments Scraper Actor."""
        print(f"[+] Launching Apify Actor for FB Post: {post_url[:50]}...")

        run_input = {
            "startUrls": [{"url": post_url}],
            "resultsLimit": max_comments,
            "includeReplies": True,
        }

        # Call the Facebook Comments Scraper Actor
        run = self.client.actor("apify/facebook-comments-scraper").call(run_input=run_input)
        
        extracted_comments = []
        dataset_items = self.client.dataset(run["defaultDatasetId"]).iterate_items()

        for item in dataset_items:
            if not isinstance(item, dict):
                continue

            if item.get("errorCode") or item.get("error"):
                error_msg = safe_str(item.get("error") or item.get("errorCode"))
                print(f"[-] Apify FB scraper returned error item: {error_msg}")
                continue

            text = safe_str(item.get("text"))
            if not text:
                continue

            author = safe_str(item.get("profileName"))
            if not author and isinstance(item.get("owner"), dict):
                author = safe_str(item.get("owner", {}).get("name")) or safe_str(item.get("owner", {}).get("username"))
            if not author:
                author = safe_str(item.get("owner")) or "FB_User"

            comment_id = safe_str(item.get("id")) or str(hash(text))
            likes_count = safe_int(item.get("likesCount"))
            parent_id_raw = item.get("parentId")
            parent_id = safe_str(parent_id_raw) if parent_id_raw else None
            timestamp = safe_str(item.get("date") or item.get("createdTime") or item.get("timestamp"))

            extracted_comments.append(
                ExtractedComment(
                    comment_id=comment_id,
                    platform="Facebook",
                    post_url=post_url,
                    author=author,
                    text=text,
                    likes_count=likes_count,
                    parent_comment_id=parent_id,
                    timestamp=timestamp
                )
            )

        return SocialPostCommentsResult(
            topic=topic,
            platform="Facebook",
            post_url=post_url,
            total_comments=len(extracted_comments),
            comments=extracted_comments
        )

    def scrape_instagram_comments(
        self, post_url: str, topic: str, max_comments: int = 100
    ) -> SocialPostCommentsResult:
        """Scrapes Instagram post/reel comments using Apify's Instagram Comment Scraper Actor."""
        print(f"[+] Launching Apify Actor for IG Post: {post_url[:50]}...")

        run_input = {
            "directUrls": [post_url],
            "resultsLimit": max_comments,
        }

        # Call the Instagram Comment Scraper Actor
        run = self.client.actor("apify/instagram-comment-scraper").call(run_input=run_input)

        extracted_comments = []
        dataset_items = self.client.dataset(run["defaultDatasetId"]).iterate_items()

        for item in dataset_items:
            if not isinstance(item, dict):
                continue

            if item.get("errorCode") or item.get("error"):
                error_msg = safe_str(item.get("error") or item.get("errorCode"))
                print(f"[-] Apify IG scraper returned error item: {error_msg}")
                continue

            text = safe_str(item.get("text"))
            if not text:
                continue

            author = safe_str(item.get("ownerUsername"))
            if not author and isinstance(item.get("owner"), dict):
                author = safe_str(item.get("owner", {}).get("username")) or safe_str(item.get("owner", {}).get("name"))
            if not author:
                author = safe_str(item.get("owner")) or "IG_User"

            comment_id = safe_str(item.get("id")) or str(hash(text))
            likes_count = safe_int(item.get("likesCount"))
            parent_id_raw = item.get("parentCommentId") or item.get("parentId")
            parent_id = safe_str(parent_id_raw) if parent_id_raw else None
            timestamp = safe_str(item.get("timestamp") or item.get("createdTime"))

            extracted_comments.append(
                ExtractedComment(
                    comment_id=comment_id,
                    platform="Instagram",
                    post_url=post_url,
                    author=author,
                    text=text,
                    likes_count=likes_count,
                    parent_comment_id=parent_id,
                    timestamp=timestamp
                )
            )

        return SocialPostCommentsResult(
            topic=topic,
            platform="Instagram",
            post_url=post_url,
            total_comments=len(extracted_comments),
            comments=extracted_comments
        )

    def scrape_tiktok_comments(
        self, post_url: str, topic: str, max_comments: int = 100
    ) -> SocialPostCommentsResult:
        """Scrapes TikTok video comments using Apify's TikTok Comments Scraper Actor."""
        print(f"[+] Launching Apify Actor for TikTok Video: {post_url[:50]}...")

        run_input = {
            "postURLs": [post_url],
            "commentsPerPost": max_comments,
            "maxRepliesPerComment": 0,
        }

        # Call the TikTok Comments Scraper Actor
        run = self.client.actor("clockworks/tiktok-comments-scraper").call(run_input=run_input)

        extracted_comments = []
        dataset_items = self.client.dataset(run["defaultDatasetId"]).iterate_items()

        for item in dataset_items:
            if not isinstance(item, dict):
                continue

            # Skip Apify dataset error items (e.g. POST_NOT_FOUND_OR_PRIVATE, PROFILE_PRIVATE)
            if item.get("errorCode") or item.get("error"):
                error_msg = safe_str(item.get("error") or item.get("errorCode"))
                url_msg = safe_str(item.get("url") or item.get("input") or post_url)
                print(f"[-] Apify TikTok scraper returned error item for {url_msg}: {error_msg}")
                continue

            # Apify TikTok payload mapping
            text = safe_str(item.get("text"))
            if not text:
                continue

            # Extract author safely (supports clockworks/tiktok-comments-scraper & clockworks/tiktok-scraper)
            author = ""
            if isinstance(item.get("authorMeta"), dict):
                author = safe_str(item.get("authorMeta", {}).get("name")) or safe_str(item.get("authorMeta", {}).get("nickName"))
            if not author and isinstance(item.get("user"), dict):
                author = safe_str(item.get("user", {}).get("uniqueId")) or safe_str(item.get("user", {}).get("nickname"))
            if not author and isinstance(item.get("author"), dict):
                author = safe_str(item.get("author", {}).get("uniqueId")) or safe_str(item.get("author", {}).get("nickname"))
            if not author:
                author = (
                    safe_str(item.get("uniqueId"))
                    or safe_str(item.get("nickname"))
                    or safe_str(item.get("uid"))
                    or "TikTok_User"
                )

            comment_id = (
                safe_str(item.get("cid"))
                or safe_str(item.get("id"))
                or safe_str(item.get("commentId"))
                or str(hash(text))
            )

            likes_count = safe_int(
                item.get("diggCount")
                or item.get("likesCount")
                or item.get("likeCount")
            )

            parent_id_raw = (
                item.get("replyToCommentId")
                or item.get("replyToReplyId")
                or item.get("parentCommentId")
                or item.get("parentId")
            )
            parent_id = safe_str(parent_id_raw) if parent_id_raw else None

            timestamp = safe_str(
                item.get("createTimeISO")
                or item.get("createTime")
                or item.get("timestamp")
            )

            extracted_comments.append(
                ExtractedComment(
                    comment_id=comment_id,
                    platform="TikTok",
                    post_url=post_url,
                    author=author,
                    text=text,
                    likes_count=likes_count,
                    parent_comment_id=parent_id,
                    timestamp=timestamp
                )
            )

        return SocialPostCommentsResult(
            topic=topic,
            platform="TikTok",
            post_url=post_url,
            total_comments=len(extracted_comments),
            comments=extracted_comments
        )

    def scrape_topic(
        self,
        topic: str,
        urls: List[str],
        target_max_comments: int = 1000,
        existing_crawled_urls: Optional[set] = None,
        existing_topic_comments: int = 0
    ) -> List[SocialPostCommentsResult]:
        """
        Scrapes comments across multiple post URLs for a given topic.
        Skips URLs that have already been crawled (passed via existing_crawled_urls).
        Terminates once `target_max_comments` (default 1000) is reached for the topic.
        """
        topic_results = []
        topic_comments_count = existing_topic_comments
        crawled_urls = set(existing_crawled_urls) if existing_crawled_urls is not None else set()

        if topic_comments_count >= target_max_comments:
            print(f"[->] Topic '{topic}' already reached target comment limit ({topic_comments_count}/{target_max_comments}). Skipping topic.")
            return topic_results

        for url in urls:
            url = url.strip() if isinstance(url, str) else ""
            if not url:
                continue

            if url in crawled_urls:
                print(f"[->] Skipping already scraped URL for topic '{topic}': {url[:60]}...")
                continue

            if topic_comments_count >= target_max_comments:
                print(f"[!] Topic '{topic}' reached comment limit ({topic_comments_count}/{target_max_comments}). Terminating scraping for this topic.")
                break

            platform = detect_platform(url)
            if not platform:
                print(f"[-] Unsupported or unrecognized platform URL: {url}")
                continue

            remaining_needed = target_max_comments - topic_comments_count
            print(f"[+] Scraping [{platform}] for topic '{topic}' ({topic_comments_count}/{target_max_comments} comments fetched): {url[:60]}...")

            try:
                if platform == "Facebook":
                    res = self.scrape_facebook_comments(url, topic, max_comments=remaining_needed)
                elif platform == "Instagram":
                    res = self.scrape_instagram_comments(url, topic, max_comments=remaining_needed)
                elif platform == "TikTok":
                    res = self.scrape_tiktok_comments(url, topic, max_comments=remaining_needed)
                else:
                    continue

                topic_results.append(res)
                fetched_count = res.total_comments
                topic_comments_count += fetched_count
                crawled_urls.add(url)
                print(f"  |- Fetched {fetched_count} comments from {platform} (Total topic comments: {topic_comments_count}/{target_max_comments})")

            except Exception as e:
                print(f"[!] Error scraping URL {url}: {e}")

            if topic_comments_count >= target_max_comments:
                print(f"[!] Topic '{topic}' reached comment limit ({topic_comments_count}/{target_max_comments}). Terminating scraping for this topic.")
                break

        return topic_results

# ==========================================
# 3. Execution Pipeline Example
# ==========================================

if __name__ == "__main__":
    crawler = ApifySocialCommentCrawler()

    ref_file_path = "./data/topic_ref.json"
    output_file = "./data/social_comments_crawled.jsonl"

    if not os.path.exists(ref_file_path):
        print(f"[!] Reference file not found: {ref_file_path}")
        exit(1)

    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    # Check existing dataset to enable resuming and URL-level deduplication
    crawled_urls = set()
    topic_comment_counts = {}

    if os.path.exists(output_file):
        with open(output_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        record = json.loads(line)
                        topic = record.get("topic")
                        post_url = record.get("post_url")
                        total_comments = record.get("total_comments", 0)

                        if post_url:
                            crawled_urls.add(post_url.strip())
                        if topic:
                            topic_comment_counts[topic] = topic_comment_counts.get(topic, 0) + total_comments
                    except Exception:
                        pass
        if crawled_urls:
            print(f"[*] Found {len(crawled_urls)} previously scraped URL(s) across {len(topic_comment_counts)} topic(s) in {output_file}.")

    with open(ref_file_path, "r", encoding="utf-8") as f:
        target_topics = json.load(f)

    total_scraped_posts = 0

    for item in target_topics:
        topic = item.get("topic", "")
        refs = item.get("ref", [])

        if isinstance(refs, str):
            refs = [refs]

        if not refs:
            print(f"[-] Skipping topic with no reference URLs: {topic[:40]}...")
            continue

        existing_comments = topic_comment_counts.get(topic, 0)
        print(f"\n==========================================")
        print(f"[*] Processing Topic: '{topic}' ({existing_comments}/1000 existing comments) with {len(refs)} reference URL(s)")
        print(f"==========================================")

        topic_results = crawler.scrape_topic(
            topic=topic,
            urls=refs,
            target_max_comments=1000,
            existing_crawled_urls=crawled_urls,
            existing_topic_comments=existing_comments
        )

        # Immediately save results after each topic completes
        if topic_results:
            with open(output_file, "a", encoding="utf-8") as f:
                for res in topic_results:
                    f.write(json.dumps(res.model_dump(), ensure_ascii=False) + "\n")
                    crawled_urls.add(res.post_url)
                    topic_comment_counts[topic] = topic_comment_counts.get(topic, 0) + res.total_comments
            
            total_scraped_posts += len(topic_results)
            print(f"  [OK] Saved {len(topic_results)} new post result(s) for topic '{topic}' to {output_file}")
        else:
            print(f"  [-] No new comments extracted for topic '{topic}'.")

    print(f"\n[OK] Finished social comment extraction via Apify! Results flushed & updated in {output_file}")