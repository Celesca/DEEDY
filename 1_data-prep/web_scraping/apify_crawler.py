import os
import json
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from apify_client import ApifyClient

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
    - TikTok Actor: 'clockworks/tiktok-comments-scraper'
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
            # Apify FB payload mapping
            comment_id = item.get("id") or str(hash(item.get("text", "")))
            author = item.get("profileName") or item.get("owner", {}).get("name", "FB_User")
            text = item.get("text", "").strip()

            if text:
                extracted_comments.append(
                    ExtractedComment(
                        comment_id=str(comment_id),
                        platform="Facebook",
                        post_url=post_url,
                        author=author,
                        text=text,
                        likes_count=item.get("likesCount", 0),
                        parent_comment_id=str(item.get("parentId")) if item.get("parentId") else None,
                        timestamp=item.get("date", "")
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
            # Apify IG payload mapping
            text = item.get("text", "").strip()
            author = item.get("ownerUsername") or item.get("owner", {}).get("username", "IG_User")

            if text:
                extracted_comments.append(
                    ExtractedComment(
                        comment_id=str(item.get("id", "")),
                        platform="Instagram",
                        post_url=post_url,
                        author=author,
                        text=text,
                        likes_count=item.get("likesCount", 0),
                        parent_comment_id=str(item.get("parentCommentId")) if item.get("parentCommentId") else None,
                        timestamp=item.get("timestamp", "")
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
            # Apify TikTok payload mapping
            text = item.get("text", "").strip()
            
            author = (
                item.get("uniqueId")
                or item.get("nickname")
                or (item.get("user", {}).get("uniqueId") if isinstance(item.get("user"), dict) else None)
                or (item.get("user", {}).get("nickname") if isinstance(item.get("user"), dict) else None)
                or "TikTok_User"
            )

            comment_id = item.get("id") or item.get("cid") or item.get("commentId") or str(hash(text))
            likes_count = item.get("diggCount") or item.get("likesCount") or item.get("likeCount") or 0
            parent_id = item.get("replyToCommentId") or item.get("parentCommentId") or item.get("parentId")
            timestamp = str(item.get("createTimeISO") or item.get("createTime") or item.get("timestamp") or "")

            if text:
                extracted_comments.append(
                    ExtractedComment(
                        comment_id=str(comment_id),
                        platform="TikTok",
                        post_url=post_url,
                        author=author,
                        text=text,
                        likes_count=int(likes_count),
                        parent_comment_id=str(parent_id) if parent_id else None,
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

# ==========================================
# 3. Execution Pipeline Example
# ==========================================

if __name__ == "__main__":
    crawler = ApifySocialCommentCrawler()

    ref_file_path = "./data/topic_social_ref.json"
    if not os.path.exists(ref_file_path):
        print(f"[!] Reference file not found: {ref_file_path}")
        exit(1)

    with open(ref_file_path, "r", encoding="utf-8") as f:
        target_social_posts = json.load(f)

    all_results = []

    for item in target_social_posts:
        topic = item.get("topic", "")
        url = item.get("ref", "").strip()

        if not url:
            print(f"[-] Skipping topic with no reference URL: {topic[:40]}...")
            continue

        platform = detect_platform(url)

        if platform == "Facebook":
            res = crawler.scrape_facebook_comments(url, topic, max_comments=50)
        elif platform == "Instagram":
            res = crawler.scrape_instagram_comments(url, topic, max_comments=50)
        elif platform == "TikTok":
            res = crawler.scrape_tiktok_comments(url, topic, max_comments=50)
        else:
            print(f"[-] Unsupported or unrecognized platform URL: {url}")
            continue

        print(f"  └─ Fetched {res.total_comments} comments from {platform}")
        all_results.append(res.model_dump())

    # Export to JSONL format ready for summarizer / OpenRouter Ensemble
    output_file = "./data/social_comments_crawled.jsonl"
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        for result in all_results:
            f.write(json.dumps(result, ensure_ascii=False) + "\n")

    print(f"[✔] Finished social comment extraction via Apify! Results saved to {output_file}")