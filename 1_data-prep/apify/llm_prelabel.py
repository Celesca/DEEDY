import asyncio
import json
import os
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
from dotenv import load_dotenv
from openai import AsyncOpenAI
from pydantic import BaseModel, Field
from tqdm.asyncio import tqdm

load_dotenv()

# Initialize Async OpenRouter Client
client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
)

# ==========================================
# 1. Model Definitions & OpenRouter IDs
# ==========================================
CRITIQUE_MODELS = {
    "deepseek": "deepseek/deepseek-v4-flash",
    "qwen": "qwen/qwen3.7-flash",
    "gemini": "google/gemini-3.5-flash-lite",
}

SYNTHESIS_MODEL = "openai/gpt-5.6-terra"


# ==========================================
# 2. Pydantic Output Schemas
# ==========================================

class TopicSentimentCounts(BaseModel):
    positive: int = Field(description="Total count of positive comments")
    neutral: int = Field(description="Total count of neutral comments")
    negative: int = Field(description="Total count of negative comments")
    positive_ratio: float = Field(description="Percentage ratio of positive comments (0.0 to 1.0)")
    neutral_ratio: float = Field(description="Percentage ratio of neutral comments (0.0 to 1.0)")
    negative_ratio: float = Field(description="Percentage ratio of negative comments (0.0 to 1.0)")


class CampaignBusinessSuggestions(BaseModel):
    campaign_next_steps: str = Field(
        description="Strategic suggestions on what to do next with this marketing campaign."
    )
    business_changes_needed: str = Field(
        description="Concrete operational/business changes needed (e.g., product adjustments, pricing, hygiene, customer service, messaging)."
    )


class TopicMarketingAnalysis(BaseModel):
    topic: str
    total_comments_analyzed: int
    sentiment_direction_analysis: str = Field(
        description="Detailed analysis of the overall sentiment direction and key consumer feedback themes for this marketing campaign."
    )
    sentiment_counts: TopicSentimentCounts
    suggestions: CampaignBusinessSuggestions


# ==========================================
# 3. System Prompts
# ==========================================

CRITIQUE_SYSTEM_PROMPT = """
You are an expert Social Listening Analyst specializing in Thai consumer marketing campaigns.
You are given a sample of scraped social media comments for a specific marketing campaign topic.

Analyze the comments and output JSON with:
1. "comment_annotations": List of objects with {"text": "...", "sentiment": "Positive|Neutral|Negative"} for each comment.
2. "sentiment_direction_analysis": A summary analyzing public sentiment, consumer reaction, praise, and complaints.
3. "campaign_next_steps": What the brand should do next with this marketing campaign.
4. "business_changes_needed": Concrete changes needed in the business (product, pricing, hygiene, service, operations).

Output ONLY valid JSON matching this structure:
{
  "comment_annotations": [
    {"text": "...", "sentiment": "Positive|Neutral|Negative"}
  ],
  "sentiment_direction_analysis": "...",
  "campaign_next_steps": "...",
  "business_changes_needed": "..."
}
"""

SYNTHESIS_SYSTEM_PROMPT = """
You are a Lead Marketing Strategist and Ensemble Meta-Summarizer for Thai Social Data.
You are provided 3 independent analysis reports from 3 AI critique models (DeepSeek, Qwen, Gemini) analyzing scraped social comments for a marketing campaign topic.

Your task:
1. Synthesize a unified, insightful analysis of the sentiment direction for this marketing campaign.
2. Consolidate comment sentiment classifications into final consensus labels ('Positive', 'Neutral', or 'Negative') for all comments.
3. Formulate high-impact, actionable business suggestions:
   - Next steps for the marketing campaign
   - Required business/operational changes (e.g. hygiene, pricing, product quality, service, communication)

Output strictly valid JSON matching this schema:
{
  "sentiment_direction_analysis": "...",
  "consolidated_comment_sentiments": [
    {"text": "...", "sentiment": "Positive|Neutral|Negative"}
  ],
  "suggestions": {
    "campaign_next_steps": "...",
    "business_changes_needed": "..."
  }
}
"""


# ==========================================
# 4. Helper & Data Loading Functions
# ==========================================

def load_scraped_comments(
    jsonl_path: str = "./data/social_comments_crawled.jsonl",
    csv_path: str = "./data/social_comments_crawled.csv"
) -> Dict[str, List[Dict[str, Any]]]:
    """Loads scraped social comments grouped by topic from JSONL or CSV file."""
    comments_by_topic: Dict[str, List[Dict[str, Any]]] = {}

    if os.path.exists(jsonl_path):
        print(f"[+] Loading scraped comments from '{jsonl_path}'...")
        with open(jsonl_path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    record = json.loads(line.strip())
                    topic = str(record.get("topic", "")).strip()
                    comments = record.get("comments", [])
                    if topic and comments:
                        if topic not in comments_by_topic:
                            comments_by_topic[topic] = []
                        comments_by_topic[topic].extend(comments)
                except Exception:
                    pass

    elif os.path.exists(csv_path):
        print(f"[+] Loading scraped comments from CSV '{csv_path}'...")
        df = pd.read_csv(csv_path)
        for topic, group in df.groupby("Topic"):
            str_topic = str(topic).strip()
            comments_by_topic[str_topic] = group.to_dict(orient="records")

    total_comments = sum(len(c) for c in comments_by_topic.values())
    print(f"[OK] Loaded {total_comments} comments across {len(comments_by_topic)} topic(s).")
    return comments_by_topic


def calculate_sentiment_counts(
    consolidated_sentiments: List[Dict[str, Any]],
    total_topic_comments: int
) -> TopicSentimentCounts:
    """Calculates exact sentiment counts and ratios for a topic."""
    pos = sum(1 for c in consolidated_sentiments if str(c.get("sentiment", "")).lower() == "positive")
    neu = sum(1 for c in consolidated_sentiments if str(c.get("sentiment", "")).lower() == "neutral")
    neg = sum(1 for c in consolidated_sentiments if str(c.get("sentiment", "")).lower() == "negative")

    annotated_total = pos + neu + neg
    if annotated_total == 0:
        return TopicSentimentCounts(
            positive=0, neutral=0, negative=0,
            positive_ratio=0.0, neutral_ratio=0.0, negative_ratio=0.0
        )

    # Scale counts proportionally to cover full topic comments dataset if sampled
    scale_factor = total_topic_comments / float(annotated_total)
    scaled_pos = int(round(pos * scale_factor))
    scaled_neu = int(round(neu * scale_factor))
    scaled_neg = int(round(neg * scale_factor))

    # Adjust rounding differences
    diff = total_topic_comments - (scaled_pos + scaled_neu + scaled_neg)
    if diff != 0:
        scaled_neu += diff

    pos_r = round(scaled_pos / total_topic_comments, 4)
    neu_r = round(scaled_neu / total_topic_comments, 4)
    neg_r = round(scaled_neg / total_topic_comments, 4)

    return TopicSentimentCounts(
        positive=scaled_pos,
        neutral=scaled_neu,
        negative=scaled_neg,
        positive_ratio=pos_r,
        neutral_ratio=neu_r,
        negative_ratio=neg_r
    )


# ==========================================
# 5. LLM Critique & Synthesis Execution
# ==========================================

async def call_critique_agent(
    model_alias: str, model_id: str, payload_prompt: str
) -> Dict[str, Any]:
    """Queries a single critique model asynchronously."""
    try:
        response = await client.chat.completions.create(
            model=model_id,
            messages=[
                {"role": "system", "content": CRITIQUE_SYSTEM_PROMPT},
                {"role": "user", "content": payload_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
        )
        content = response.choices[0].message.content
        return {
            "model_alias": model_alias,
            "status": "success",
            "data": json.loads(content),
        }
    except Exception as e:
        print(f"[!] Model {model_alias} ({model_id}) error: {e}")
        return {"model_alias": model_alias, "status": "failed", "error": str(e)}


async def process_topic_analysis(
    topic: str,
    raw_comments: List[Dict[str, Any]],
    max_sample_comments: int = 80
) -> Optional[Dict[str, Any]]:
    """Runs parallel critique models and synthesizes final marketing campaign analysis."""
    total_topic_comments = len(raw_comments)

    # Sample representative comments for context window efficiency
    sampled_comments = raw_comments[:max_sample_comments]
    formatted_comments = []
    for c in sampled_comments:
        text = str(c.get("text") or c.get("comment") or "").strip()
        author = str(c.get("author") or "User").strip()
        likes = c.get("likes_count", 0)
        if text:
            formatted_comments.append({"author": author, "text": text, "likes": likes})

    payload_prompt = json.dumps(
        {
            "topic": topic,
            "total_comments": total_topic_comments,
            "comments_sample": formatted_comments
        },
        ensure_ascii=False,
        indent=2
    )

    print(f"[*] Analyzing topic '{topic}' ({total_topic_comments} total comments) with 3 critique models...")

    # 1. Concurrent Critique Execution across DeepSeek, Qwen, Gemini
    tasks = [
        call_critique_agent(alias, model_id, payload_prompt)
        for alias, model_id in CRITIQUE_MODELS.items()
    ]
    critique_results = await asyncio.gather(*tasks)

    successful_critiques = {
        res["model_alias"]: res["data"]
        for res in critique_results
        if res["status"] == "success"
    }

    if not successful_critiques:
        print(f"[!] All critique models failed for topic '{topic}'.")
        return None

    # 2. Meta-Synthesis using GPT-5.6 Terra
    synthesis_prompt = f"""
Topic: {topic}
Total Comments in Topic: {total_topic_comments}

Here are the independent critique reports from 3 models:
{json.dumps(successful_critiques, ensure_ascii=False, indent=2)}

Please synthesize the final comprehensive JSON output.
"""

    try:
        meta_response = await client.chat.completions.create(
            model=SYNTHESIS_MODEL,
            messages=[
                {"role": "system", "content": SYNTHESIS_SYSTEM_PROMPT},
                {"role": "user", "content": synthesis_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
        )

        content = meta_response.choices[0].message.content
        parsed = json.loads(content)

        consolidated_sentiments = parsed.get("consolidated_comment_sentiments", [])
        sentiment_counts = calculate_sentiment_counts(consolidated_sentiments, total_topic_comments)

        final_analysis = TopicMarketingAnalysis(
            topic=topic,
            total_comments_analyzed=total_topic_comments,
            sentiment_direction_analysis=parsed.get("sentiment_direction_analysis", ""),
            sentiment_counts=sentiment_counts,
            suggestions=CampaignBusinessSuggestions(
                campaign_next_steps=parsed.get("suggestions", {}).get("campaign_next_steps", ""),
                business_changes_needed=parsed.get("suggestions", {}).get("business_changes_needed", "")
            )
        )

        return final_analysis.model_dump()

    except Exception as e:
        print(f"[!] Synthesis error for topic '{topic}': {e}")
        return None


# ==========================================
# 6. Main Pipeline Entrypoint
# ==========================================

async def main():
    comments_file = "./data/social_comments_crawled.jsonl"
    output_jsonl = "./data/campaign_sentiment_analysis.jsonl"
    output_csv = "./data/campaign_sentiment_summary.csv"

    comments_map = load_scraped_comments(jsonl_path=comments_file)
    if not comments_map:
        print(f"[!] No comments found in '{comments_file}'. Please run apify_crawler.py first.")
        return

    # Check for already completed topics to resume execution
    completed_topics = set()
    os.makedirs(os.path.dirname(output_jsonl), exist_ok=True)
    if os.path.exists(output_jsonl):
        with open(output_jsonl, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        obj = json.loads(line.strip())
                        if "topic" in obj:
                            completed_topics.add(obj["topic"])
                    except Exception:
                        pass
        if completed_topics:
            print(f"[*] Resuming pipeline... Found {len(completed_topics)} already analyzed topic(s).")

    all_analyses = []
    
    # Also load existing analyses if file exists
    if os.path.exists(output_jsonl):
        with open(output_jsonl, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        all_analyses.append(json.loads(line.strip()))
                    except Exception:
                        pass

    for topic, raw_comments in comments_map.items():
        if topic in completed_topics:
            print(f"[➜] Skipping already analyzed topic: '{topic}'")
            continue

        print(f"\n==========================================")
        print(f"[*] Processing Campaign Topic: '{topic}' ({len(raw_comments)} comments)")
        print(f"==========================================")

        result = await process_topic_analysis(topic, raw_comments)
        if result:
            all_analyses.append(result)
            completed_topics.add(topic)
            
            # Immediately append & flush to JSONL
            with open(output_jsonl, "a", encoding="utf-8") as out_f:
                out_f.write(json.dumps(result, ensure_ascii=False) + "\n")
                out_f.flush()

            print(f"  [OK] Successfully saved analysis for '{topic}' to '{output_jsonl}'")

    # Export a flattened summary CSV report for easy viewing in Excel
    if all_analyses:
        csv_rows = []
        for a in all_analyses:
            sc = a.get("sentiment_counts", {})
            sug = a.get("suggestions", {})
            csv_rows.append({
                "Topic": a.get("topic"),
                "Total_Comments": a.get("total_comments_analyzed"),
                "Positive_Comments": sc.get("positive"),
                "Neutral_Comments": sc.get("neutral"),
                "Negative_Comments": sc.get("negative"),
                "Positive_Ratio": sc.get("positive_ratio"),
                "Neutral_Ratio": sc.get("neutral_ratio"),
                "Negative_Ratio": sc.get("negative_ratio"),
                "Sentiment_Direction_Analysis": a.get("sentiment_direction_analysis"),
                "Campaign_Next_Steps": sug.get("campaign_next_steps"),
                "Business_Changes_Needed": sug.get("business_changes_needed"),
            })
        
        df_summary = pd.DataFrame(csv_rows)
        df_summary.to_csv(output_csv, index=False, encoding="utf-8-sig")
        print(f"\n[OK] Finished analysis pipeline! Exported summary CSV to '{output_csv}'")


if __name__ == "__main__":
    asyncio.run(main())