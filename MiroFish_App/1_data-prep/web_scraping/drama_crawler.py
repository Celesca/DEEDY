from tqdm import tqdm
import logging
import json
import os
import re

from typing import Dict, Optional
from markdownify import markdownify as md

import requests
from bs4 import BeautifulSoup

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# User-Agent headers to prevent basic blocking
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}

class ContentScraper:
    def __init__(self, output_file: str = "./data/scraped_content.jsonl"):
        self.output_file = output_file
        self.session = requests.Session()
        self.session.headers.update(HEADERS)

    def resolve_final_url(self, url: str) -> str:
        """Resolves redirects (e.g. Google News RSS links)."""
        try:
            response = self.session.get(url, allow_redirects=True, timeout=10)
            return response.url
        except Exception as e:
            logging.warning(f"Failed to resolve redirect for {url}: {e}")
            return url

    def fetch_via_wayback(self, url: str) -> Optional[str]:
        """Attempts to fetch the page content from Wayback Machine archive to bypass blocks."""
        logging.info(f"Attempting to fetch cached version of {url} from Wayback Machine...")
        api_url = f"https://archive.org/wayback/available?url={url}"
        try:
            resp = self.session.get(api_url, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                snapshots = data.get("archived_snapshots", {})
                if "closest" in snapshots:
                    closest_url = snapshots["closest"]["url"]
                    logging.info(f"Found archive snapshot: {closest_url}")
                    # Fetch from archive
                    archive_resp = self.session.get(closest_url, timeout=15)
                    if archive_resp.status_code == 200:
                        archive_resp.encoding = "utf-8"
                        return archive_resp.text
        except Exception as e:
            logging.warning(f"Failed to fetch from Wayback Machine for {url}: {e}")
        return None

    def scrape_google_news(self, url: str) -> Dict[str, str]:
        """Scrapes standard news article body text."""
        final_url = url
        if "news.google.com" in url:
            try:
                from googlenewsdecoder import gnewsdecoder
                decoded = gnewsdecoder(url)
                if decoded.get("status"):
                    final_url = decoded["decoded_url"]
            except Exception as e:
                logging.warning(f"googlenewsdecoder failed for {url}: {e}")
                final_url = self.resolve_final_url(url)
        else:
            final_url = self.resolve_final_url(url)

        try:
            resp = self.session.get(final_url, timeout=12)
            if resp.status_code == 403:
                html_text = self.fetch_via_wayback(final_url)
                if not html_text:
                    resp.raise_for_status()
            else:
                resp.raise_for_status()
                resp.encoding = resp.apparent_encoding or "utf-8"
                html_text = resp.text
            
            soup = BeautifulSoup(html_text, "html.parser")
            
            # Extract title
            title = soup.title.string.strip() if soup.title and soup.title.string else ""
            
            # Extract content in Markdown format
            articles = soup.find_all("article")
            if articles:
                markdown_contents = [md(str(article)).strip() for article in articles]
                clean_content = "\n\n---\n\n".join([c for c in markdown_contents if c])
            else:
                clean_content = md(str(soup.body or soup)).strip()
                
            clean_content = re.sub(r'\n{3,}', '\n\n', clean_content)
            
            return {
                "resolved_url": final_url,
                "title": title,
                "content": clean_content
            }
        except Exception as e:
            try:
                html_text = self.fetch_via_wayback(final_url)
                if html_text:
                    soup = BeautifulSoup(html_text, "html.parser")
                    title = soup.title.string.strip() if soup.title and soup.title.string else ""
                    articles = soup.find_all("article")
                    if articles:
                        markdown_contents = [md(str(article)).strip() for article in articles]
                        clean_content = "\n\n---\n\n".join([c for c in markdown_contents if c])
                    else:
                        clean_content = md(str(soup.body or soup)).strip()
                    clean_content = re.sub(r'\n{3,}', '\n\n', clean_content)
                    return {
                        "resolved_url": final_url,
                        "title": title,
                        "content": clean_content
                    }
            except Exception as e2:
                logging.error(f"Fallback to Wayback Machine also failed: {e2}")

            logging.error(f"Error scraping news source {final_url}: {e}")
            return {"resolved_url": final_url, "title": "", "content": ""}

    def scrape_pantip(self, url: str) -> Dict[str, str]:
        """Scrapes Pantip topic body and initial comments."""
        try:
            resp = self.session.get(url, timeout=10)
            resp.raise_for_status()
            resp.encoding = resp.apparent_encoding or "utf-8"
            
            soup = BeautifulSoup(resp.text, "html.parser")
            
            # Topic Title
            title_elem = soup.find("h2", class_="display-post-title") or soup.find("h3", class_="display-post-title")
            title = title_elem.get_text(strip=True) if title_elem else ""
            
            # Main Post & Comments Content in Markdown format
            stories = soup.find_all("div", class_="display-post-story")
            content_list = [md(str(story)).strip() for story in stories]
            content_list = [re.sub(r'\n{3,}', '\n\n', content) for content in content_list if content]
            
            full_content = "\n\n--- Comment / Section ---\n\n".join(content_list)
            
            return {
                "resolved_url": url,
                "title": title,
                "content": full_content
            }
        except Exception as e:
            logging.error(f"Error scraping Pantip {url}: {e}")
            return {"resolved_url": url, "title": "", "content": ""}

    def scrape_tiktok_search(self, url: str) -> Dict[str, str]:
        """
        Placeholder / Playwright hook for dynamic TikTok search pages.
        Note: Simple requests return empty raw JS.
        """
        logging.info(f"Skipping or routing to Playwright for TikTok: {url}")
        # In a full pipeline, dispatch this URL to Playwright/Selenium
        return {
            "resolved_url": url,
            "title": "TikTok Search Results",
            "content": "Requires Playwright/Selenium rendering for dynamic DOM extraction."
        }

    def process_item(self, platform: str, url: str) -> Dict[str, str]:
        """Routes URLs to their specific scraper handler."""
        platform_lower = platform.lower()
        if "google news" in platform_lower or "news" in platform_lower:
            return self.scrape_google_news(url)
        elif "pantip" in platform_lower:
            return self.scrape_pantip(url)
        elif "tiktok" in platform_lower:
            return self.scrape_tiktok_search(url)
        else:
            # General fallback scraper
            return self.scrape_google_news(url)

    def run(self, input_file: str):
        """Processes input JSON/JSONL file and writes output JSONL."""
        if not os.path.exists(input_file):
            logging.error(f"Input file {input_file} not found.")
            return

        with open(input_file, "r", encoding="utf-8-sig") as infile:
            lines = [line.strip() for line in infile if line.strip()]

        with open(self.output_file, "w", encoding="utf-8-sig") as outfile:
            for line in tqdm(lines, total=len(lines)):
                topic_entry = json.loads(line)
                topic = topic_entry.get("topic", "")
                refs = topic_entry.get("refs", [])
                
                logging.info(f"\nProcessing Topic: {topic[:50]}...")
                
                scraped_refs = []
                for ref in refs:
                    platform = ref.get("platform", "")
                    url = ref.get("url", "")
                    
                    # logging.info(f"[{platform}] Scraping: {url}")
                    scraped_data = self.process_item(platform, url)
                    
                    scraped_refs.append({
                        "platform": platform,
                        "title": scraped_data["title"],
                        "content": scraped_data["content"]
                    })
                
                # Output format matching your pipeline step
                out_item = {
                    "topic": topic,
                    "scraped_data": scraped_refs
                }
                
                outfile.write(json.dumps(out_item, ensure_ascii=False) + "\n")
                logging.info(f"Saved {len(scraped_refs)} scraped sources for topic.")


if __name__ == "__main__":
    # Point this to your generated drama_ref.jsonl file
    scraper = ContentScraper(output_file="../data/scraped_content02.jsonl")
    scraper.run(input_file="../data/drama_ref02.jsonl")