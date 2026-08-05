import json
import urllib.parse
from typing import Any, Dict, List, Set

import feedparser
import requests
from bs4 import BeautifulSoup
from pydantic import BaseModel
from tqdm import tqdm


class DiscoveredTarget(BaseModel):
    platform: str
    drama_tag: str
    url: str
    topic_id: str = ""
    comment_selector: str = ".comment-item-text"


class TargetDiscoverer:

    def __init__(self, drama_tag: str, keywords: List[str]):
        self.drama_tag = drama_tag
        self.keywords = keywords
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                " (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "th-TH,th;q=0.9,en;q=0.8",
        }
        self.seen_urls: Set[str] = set()

    def discover_google_news_targets(self) -> List[DiscoveredTarget]:
        """Discovers Thai news portal articles covering the drama via Google News RSS."""
        targets = []
        queries = self.keywords + [" ".join(self.keywords[:2])] if self.keywords else [self.drama_tag]

        for q in queries:
            encoded_query = urllib.parse.quote(q)
            rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=th&gl=TH&ceid=TH:th"

            feed = feedparser.parse(rss_url)

            for entry in feed.entries:
                article_url = entry.link
                if article_url not in self.seen_urls:
                    self.seen_urls.add(article_url)
                    targets.append(
                        DiscoveredTarget(
                            platform="Google News",
                            drama_tag=self.drama_tag,
                            url=article_url,
                            comment_selector="article, .comment-box, .reply-item",
                        )
                    )
            if len(targets) >= 25:
                break
        return targets

    def discover_pantip_targets(self) -> List[DiscoveredTarget]:
        """Searches Pantip directly via Pantip's native API endpoint instead of search engines."""
        targets = []
        queries_to_try = self.keywords + [" ".join(self.keywords[:2])] if self.keywords else [self.drama_tag]

        for search_keyword in queries_to_try:
            pantip_api_url = "https://pantip.com/api/forum-service/home/get_search"
            params = {
                "keyword": search_keyword,
                "page": 1,
                "limit": 10,
            }

            # Pantip API requires specific referer header
            headers = self.headers.copy()
            headers["Referer"] = (
                f"https://pantip.com/search?q={urllib.parse.quote(search_keyword)}"
            )

            try:
                resp = requests.get(
                    pantip_api_url, params=params, headers=headers, timeout=10
                )

                if resp.status_code == 200:
                    data = resp.json()
                    # Pantip returns search items under "data" array
                    items = data.get("data", [])
                    for item in items:
                        topic_id = str(item.get("id", ""))
                        if topic_id and topic_id.isdigit():
                            clean_url = f"https://pantip.com/topic/{topic_id}"
                            if clean_url not in self.seen_urls:
                                self.seen_urls.add(clean_url)
                                targets.append(
                                    DiscoveredTarget(
                                        platform="Pantip",
                                        drama_tag=self.drama_tag,
                                        url=clean_url,
                                        topic_id=topic_id,
                                    )
                                )
                else:
                    # Fallback to direct HTML search on Pantip if API response fails
                    fallback_url = f"https://pantip.com/search?q={urllib.parse.quote(search_keyword)}"
                    resp_fallback = requests.get(
                        fallback_url, headers=headers, timeout=10
                    )
                    if resp_fallback.status_code == 200:
                        soup = BeautifulSoup(resp_fallback.text, "html.parser")
                        li_items = soup.find_all("li", class_="pt-list-item")
                        for li in li_items:
                            # Skip skeleton loader element (which is hidden)
                            if li.get("style") and "display:none" in li.get("style").replace(" ", ""):
                                continue
                            
                            # Find the first link inside this list item pointing to a topic
                            topic_a = None
                            for a in li.find_all("a", href=True):
                                if "/topic/" in a["href"]:
                                    topic_a = a
                                    break
                            
                            if topic_a:
                                href = topic_a["href"]
                                topic_id = (
                                    href.split("/topic/")[-1]
                                    .split("?")[0]
                                    .split("/")[0]
                                )
                                clean_url = f"https://pantip.com/topic/{topic_id}"
                                if (
                                    clean_url not in self.seen_urls
                                    and topic_id.isdigit()
                                ):
                                    self.seen_urls.add(clean_url)
                                    targets.append(
                                        DiscoveredTarget(
                                            platform="Pantip",
                                            drama_tag=self.drama_tag,
                                            url=clean_url,
                                            topic_id=topic_id,
                                        )
                                    )
            except Exception as e:
                print(f"[!] Error fetching Pantip targets: {e}")
                
            # If we found any targets, we do not need to try fallback queries
            if targets:
                break

        return targets

    def discover_tiktok_targets(self) -> List[DiscoveredTarget]:
        """Discovers relevant TikTok video posts related to the drama."""
        targets = []
        search_keyword = " ".join(self.keywords)
        encoded_keyword = urllib.parse.quote(search_keyword)

        # TikTok Web Search URL
        tiktok_url = f"https://www.tiktok.com/search?q={encoded_keyword}"

        if tiktok_url not in self.seen_urls:
            self.seen_urls.add(tiktok_url)
            targets.append(
                DiscoveredTarget(
                    platform="TikTok",
                    drama_tag=self.drama_tag,
                    url=tiktok_url,
                    comment_selector='[data-e2e="comment-level-1"]',  # TikTok web comment selector
                )
            )

        return targets

    def build_targets_queue(self) -> List[Dict[str, Any]]:
        """Runs all discovery engines and formats the queue for the Crawler."""
        discovered = []

        # 1. Google News
        news_targets = self.discover_google_news_targets()
        discovered.extend([t.model_dump() for t in news_targets])

        # 2. Pantip
        pantip_targets = self.discover_pantip_targets()
        discovered.extend([t.model_dump() for t in pantip_targets])

        # 3. TikTok
        tiktok_targets = self.discover_tiktok_targets()
        discovered.extend([t.model_dump() for t in tiktok_targets])

        return discovered


# ==========================================
# Execution Example
# ==========================================
if __name__ == "__main__":
    with open("./data/topic.json", "r", encoding="utf-8-sig") as f:
        topic_data = json.load(f)

    search_results = []
    for drama_dict in tqdm(topic_data):
        drama_tag, keywords = drama_dict["topic"], drama_dict["keywords"]
        print(
            f"\nDiscovering targets for drama tag: {drama_tag} with keywords:"
            f" {keywords}"
        )
        discoverer = TargetDiscoverer(drama_tag=drama_tag, keywords=keywords)
        automated_targets_queue = discoverer.build_targets_queue()

        print(
            f"[+] Automatically discovered {len(automated_targets_queue)}"
            " target sources:"
        )

        search_results.append({
            "topic": drama_tag,
            "refs": [
                {"platform": target['platform'], "url": target['url']} for target in automated_targets_queue
            ]
        })
    
    with open("../data/drama_ref01.jsonl", "w", encoding="utf-8-sig") as f:
        for result in search_results:
            f.write(json.dumps(result, ensure_ascii=False) + "\n")
