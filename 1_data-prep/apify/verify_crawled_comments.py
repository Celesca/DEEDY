import json
import os
import sys
from typing import Dict, List, Any, Set

# Ensure UTF-8 output encoding for Windows terminal compatibility
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def verify_crawled_comments(
    jsonl_path: str = "./data/social_comments_crawled.jsonl",
    topic_ref_path: str = "./data/topic_ref.json",
    target_quota: int = 1000
) -> Dict[str, Any]:
    """
    Verifies the scraped comments dataset against topic expectations (target_quota per topic).
    Audits comment counts, shortfalls, and reference URLs without writing CSV files.
    """
    # Check fallback input file paths if default doesn't exist
    if not os.path.exists(jsonl_path):
        alt_path = "./data/social_comments_crawled.json"
        if os.path.exists(alt_path):
            jsonl_path = alt_path
        else:
            print(f"[!] Input file not found at '{jsonl_path}'.")
            return {}

    print(f"[*] Reading scraped data from: {jsonl_path}")
    raw_records: List[Dict[str, Any]] = []

    with open(jsonl_path, "r", encoding="utf-8") as f:
        content = f.read().strip()
        if content.startswith("[") and content.endswith("]"):
            raw_records = json.loads(content)
        else:
            for line in content.splitlines():
                line_str = line.strip()
                if line_str:
                    try:
                        raw_records.append(json.loads(line_str))
                    except json.JSONDecodeError as e:
                        print(f"[!] Warning: Skipping malformed JSON line: {e}")

    # Process and tally comments per topic
    total_comments = 0
    topic_comment_counts: Dict[str, int] = {}
    topic_scraped_urls: Dict[str, Set[str]] = {}

    for record in raw_records:
        topic = str(record.get("topic", "")).strip()
        top_post_url = str(record.get("post_url", "")).strip()
        comments_list = record.get("comments", [])

        if not isinstance(comments_list, list) or not comments_list:
            if "text" in record or "comment" in record:
                comments_list = [record]
            else:
                continue

        if topic:
            if topic not in topic_scraped_urls:
                topic_scraped_urls[topic] = set()
            if top_post_url:
                topic_scraped_urls[topic].add(top_post_url)

        for c in comments_list:
            if not isinstance(c, dict):
                continue

            comment_text = c.get("text") or c.get("comment", "")
            if not comment_text:
                continue

            c_post_url = c.get("post_url") or top_post_url
            if topic and c_post_url:
                if topic not in topic_scraped_urls:
                    topic_scraped_urls[topic] = set()
                topic_scraped_urls[topic].add(c_post_url)

            total_comments += 1
            if topic:
                topic_comment_counts[topic] = topic_comment_counts.get(topic, 0) + 1

    # Load master reference topics
    master_topics: List[str] = []
    topic_refs_map: Dict[str, List[str]] = {}
    if os.path.exists(topic_ref_path):
        with open(topic_ref_path, "r", encoding="utf-8") as f:
            ref_data = json.load(f)
            for item in ref_data:
                t_name = str(item.get("topic", "")).strip()
                t_refs = item.get("ref", [])
                if isinstance(t_refs, str):
                    t_refs = [t_refs]
                if t_name:
                    master_topics.append(t_name)
                    topic_refs_map[t_name] = t_refs

    # Combine master topics and topics found in crawled data
    all_topics = list(dict.fromkeys(master_topics + list(topic_comment_counts.keys())))

    print("\n==========================================================================")
    print(f"[*] SCRAPED DATASET VERIFICATION REPORT (Target: {target_quota} comments / topic)")
    print("==========================================================================")

    all_met = True
    for idx, t in enumerate(all_topics, start=1):
        count = topic_comment_counts.get(t, 0)
        total_refs = len(topic_refs_map.get(t, []))
        scraped_urls_cnt = len(topic_scraped_urls.get(t, set()))
        met = count >= target_quota
        if not met:
            all_met = False

        shortfall = max(0, target_quota - count)
        status_badge = "[OK] MET    " if met else "[!] NOT MET"
        ref_str = f"{scraped_urls_cnt} / {total_refs}" if total_refs > 0 else f"{scraped_urls_cnt}"

        print(f"Topic {idx}: {t}")
        print(f"  Status       : {status_badge}")
        print(f"  Comments     : {count} / {target_quota} (Shortfall: {shortfall})")
        print(f"  Ref URLs     : {ref_str}")
        print("--------------------------------------------------------------------------")

    met_count = sum(1 for t in all_topics if topic_comment_counts.get(t, 0) >= target_quota)
    total_count = len(all_topics)

    print("\n--- SUMMARY STATUS ---")
    print(f"Topics Meeting Expectation ({target_quota}+ comments) : {met_count} / {total_count}")

    if all_met:
        print("[OK] VERIFICATION SUCCESSFUL: All topics met the requirement of 1,000 comments per topic!")
    else:
        print(f"[!] VERIFICATION INCOMPLETE: {total_count - met_count} topic(s) have not met the 1,000 comments target.")
        print("    Recommendation: Re-run 'python apify_crawler.py' after updating Apify API usage quota to complete scraping.")

    print("==========================================================================\n")

    return {
        "total_comments": total_comments,
        "topic_counts": topic_comment_counts,
        "all_met": all_met
    }


if __name__ == "__main__":
    verify_crawled_comments()
