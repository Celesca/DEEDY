import os
import json
import pandas as pd
from typing import List, Dict, Any

def convert_comments_json_to_csv(
    input_path: str = "./data/social_comments_crawled.jsonl",
    output_path: str = "./data/social_comments_crawled.csv"
) -> pd.DataFrame:
    """
    Reads crawled social post comments JSON/JSONL data, flattens nested comments,
    and exports to a clean CSV file with MUST-HAVE columns 'Topic' and 'comment'.
    """
    # Check fallback input file paths if default doesn't exist
    if not os.path.exists(input_path):
        alt_path = "./data/social_comments_crawled.json"
        if os.path.exists(alt_path):
            input_path = alt_path
        else:
            raise FileNotFoundError(f"Input file not found at '{input_path}' or '{alt_path}'.")

    print(f"[*] Reading input file: {input_path}")
    raw_records: List[Dict[str, Any]] = []

    with open(input_path, "r", encoding="utf-8") as f:
        # Handle JSONL (one JSON object per line) or standard JSON array
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

    rows = []
    for record in raw_records:
        topic = record.get("topic", "")
        top_platform = record.get("platform", "")
        top_post_url = record.get("post_url", "")
        comments_list = record.get("comments", [])

        # If the record itself is a single comment object rather than nested topic container
        if not isinstance(comments_list, list) or not comments_list:
            if "text" in record or "comment" in record:
                comments_list = [record]
            else:
                continue

        for c in comments_list:
            if not isinstance(c, dict):
                continue

            comment_text = c.get("text") or c.get("comment", "")
            if not comment_text:
                continue

            rows.append({
                "Topic": topic,
                "comment": comment_text,
                "Author": c.get("author", ""),
                "Likes_Count": c.get("likes_count", 0),
                "Platform": c.get("platform") or top_platform,
                "Post_URL": c.get("post_url") or top_post_url,
                "Comment_ID": c.get("comment_id", ""),
                "Parent_Comment_ID": c.get("parent_comment_id") or "",
                "Timestamp": c.get("timestamp", ""),
            })

    df = pd.DataFrame(rows)

    # Ensure target output directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Save to CSV using utf-8-sig for proper character display (e.g. Thai / Unicode in Excel)
    df.to_csv(output_path, index=False, encoding="utf-8-sig")

    print(f"[OK] Successfully exported {len(df)} comments to '{output_path}'!")
    print(f"    Columns: {list(df.columns)}")
    return df


if __name__ == "__main__":
    df = convert_comments_json_to_csv()
    if not df.empty:
        print("\n--- Preview (First 5 rows) ---")
        print(df[["Topic", "comment", "Author", "Likes_Count", "Platform"]].head())
