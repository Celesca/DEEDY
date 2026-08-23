import asyncio
import json
import os
from typing import Any, Dict, List, Optional

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
# 2. Data Schemas
# ==========================================
class MicroPostAnnotation(BaseModel):
    title_or_snippet: str = Field(
        description="Title or key sentence snippet from the summarized content."
    )
    sentiment_label: str = Field(
        description="Must be strictly: 'Positive', 'Neutral', or 'Negative'"
    )
    stance_label: str = Field(
        description=(
            "Core stance (e.g., 'Purist', 'Pragmatist', 'Brand Defense',"
            " 'Skeptical')"
        )
    )
    is_sarcastic: bool = Field(
        description=(
            "True if post contains sarcasm, irony, or Thai double meaning."
        )
    )


class MacroTrendSummary(BaseModel):
    extractive_summary: str = Field(
        description="Factual 2-3 sentence summary of what actually happened."
    )
    public_opinion_direction: str = Field(
        description=(
            "Summary of public reaction, debates, and dominant viewpoints."
        )
    )
    key_polarization_axis: str = Field(
        description=(
            "Main conflict axis (e.g., 'Authentic Ingredients vs. Food"
            " Innovation')."
        )
    )
    estimated_sentiment_distribution: dict = Field(
        description=(
            "Calculated ratio breakdown like {'positive': 0.3, 'neutral': 0.2,"
            " 'negative': 0.5}"
        )
    )


class DramaGroundTruthAnnotation(BaseModel):
    topic: str
    macro_summary: MacroTrendSummary
    micro_post_annotations: List[MicroPostAnnotation]


# ==========================================
# 3. System Prompts
# ==========================================
CRITIQUE_SYSTEM_PROMPT = """
You are an expert Thai Social Listening Analyst. Analyze summarized posts regarding a Thai drama topic and extract:
1. Macro summary (extractive summary, public reaction, key polarization axis).
2. Micro annotations per post (sentiment: Positive/Neutral/Negative, stance, is_sarcastic boolean).

Detect Thai irony/sarcasm carefully. Output ONLY valid JSON matching this schema:
{
  "macro_summary": {
    "extractive_summary": "...",
    "public_opinion_direction": "...",
    "key_polarization_axis": "..."
  },
  "micro_post_annotations": [
    {
      "title_or_snippet": "...",
      "sentiment_label": "Positive|Neutral|Negative",
      "stance_label": "...",
      "is_sarcastic": false
    }
  ]
}
"""

SYNTHESIS_SYSTEM_PROMPT = """
You are a Lead Data Scientist and Ensemble Meta-Summarizer for Thai Internet Social Data.
You are given 3 independent JSON analysis reports from 3 critique models (DeepSeek-V4-Flash, Qwen-3.7-Flash, and Gemini-3.5-Flash-Lite) evaluating the same topic.

Your task:
1. Synthesize the insights across all 3 reports into a single, definitive ground-truth annotation.
2. For sentiment and stance, resolve minor disagreements by taking the majority consensus among the models.
3. Consolidate macro-summaries into a coherent, high-quality analysis.
4. Output strictly valid JSON with no additional explanation.
"""


# ==========================================
# 4. Helper Functions
# ==========================================
def compute_sentiment_distribution(micro_annotations: List[dict]) -> dict:
    """Calculates deterministic sentiment ratios from micro annotations."""
    if not micro_annotations:
        return {"positive": 0.0, "neutral": 0.0, "negative": 0.0}

    total = len(micro_annotations)
    counts = {"positive": 0, "neutral": 0, "negative": 0}

    for item in micro_annotations:
        label = str(item.get("sentiment_label", "")).strip().lower()
        if label in counts:
            counts[label] += 1

    return {
        "positive": round(counts["positive"] / total, 2),
        "neutral": round(counts["neutral"] / total, 2),
        "negative": round(counts["negative"] / total, 2),
    }


async def call_critique_agent(
    model_alias: str, model_id: str, payload_prompt: str
) -> Dict[str, Any]:
    """Asynchronously queries a single critique model."""
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


async def process_topic_ensemble(
    drama_topic: str, posts_data: List[dict]
) -> Optional[dict]:
    """Runs parallel critique models and synthesizes their outputs using GPT-5.6 Terra."""
    formatted_input = {
        "topic": drama_topic,
        "summarized_posts": [
            {
                "platform": item.get("platform"),
                "post_title": item.get("post_title"),
                "summary": item.get("summary"),
            }
            for item in posts_data[:15]
        ],
    }

    payload_prompt = f"Topic and Summaries to Analyze:\n{json.dumps(formatted_input, ensure_ascii=False, indent=2)}"

    # 1. Parallel Execution Across the 3 Critique Models
    tasks = [
        call_critique_agent(alias, model_id, payload_prompt)
        for alias, model_id in CRITIQUE_MODELS.items()
    ]
    critique_results = await asyncio.gather(*tasks)

    # Filter successful responses
    successful_critiques = {
        res["model_alias"]: res["data"]
        for res in critique_results
        if res["status"] == "success"
    }

    if not successful_critiques:
        print(
            f"[!] All critique models failed for topic: '{drama_topic[:30]}...'"
        )
        return None

    # 2. Meta-Synthesis using GPT-5.6 Terra
    synthesis_prompt = f"""
Topic: {drama_topic}

Here are the critique reports from our 3 models:
{json.dumps(successful_critiques, ensure_ascii=False, indent=2)}

Please synthesize these into the final ground truth JSON structure:
{{
  "macro_summary": {{
    "extractive_summary": "...",
    "public_opinion_direction": "...",
    "key_polarization_axis": "..."
  }},
  "micro_post_annotations": [
    {{
      "title_or_snippet": "...",
      "sentiment_label": "Positive|Neutral|Negative",
      "stance_label": "...",
      "is_sarcastic": false
    }}
  ]
}}
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
        parsed_json = json.loads(content)
        parsed_json["topic"] = drama_topic

        # Calculate exact sentiment ratios directly from final micro annotations
        micro_annotations = parsed_json.get("micro_post_annotations", [])
        if "macro_summary" not in parsed_json or not isinstance(
            parsed_json["macro_summary"], dict
        ):
            parsed_json["macro_summary"] = {}

        parsed_json["macro_summary"]["estimated_sentiment_distribution"] = (
            compute_sentiment_distribution(micro_annotations)
        )

        return parsed_json

    except Exception as e:
        print(f"[!] GPT-5.6 Terra Synthesis error for topic '{drama_topic}': {e}")
        return None


# ==========================================
# 5. Main Execution Pipeline
# ==========================================
async def run_ensemble_pipeline(csv_input_path: str, output_jsonl_path: str):
    print(
        "[+] Loading pre-summarized vLLM CSV dataset from"
        f" '{csv_input_path}'..."
    )
    df = pd.read_csv(csv_input_path)

    # Filter strictly for relevant posts
    df_clean = df[df["is_related"] == True]
    print(f"[+] Found {len(df_clean)} relevant posts across topics.")

    # Group records by topic
    grouped_topics = df_clean.groupby("topic")

    # Check for existing completed topics to resume
    existing_topics = set()
    out_dir = os.path.dirname(output_jsonl_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    if os.path.exists(output_jsonl_path):
        with open(output_jsonl_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        obj = json.loads(line.strip(), strict=False)
                        if "topic" in obj:
                            existing_topics.add(obj["topic"])
                    except Exception:
                        pass
        if existing_topics:
            print(
                f"[*] Found {len(existing_topics)} previously annotated topics."
                " Resuming..."
            )

    annotated_count = 0
    with open(output_jsonl_path, "a", encoding="utf-8") as out_f:
        for topic, group in tqdm(grouped_topics, desc="Ensemble Prelabeling"):
            if topic in existing_topics:
                continue

            posts_data = group.to_dict(orient="records")
            result = await process_topic_ensemble(str(topic), posts_data)

            if result:
                out_f.write(json.dumps(result, ensure_ascii=False) + "\n")
                out_f.flush()
                annotated_count += 1
                existing_topics.add(str(topic))

    print(
        f"[✔] Successfully generated ground truth for {annotated_count} new"
        f" topics -> Saved to '{output_jsonl_path}'"
    )


if __name__ == "__main__":
    INPUT_CSV = "./data/summarized_post_content.csv"
    OUTPUT_JSONL = "./data/ensemble_ground_truth.jsonl"

    if os.path.exists(INPUT_CSV):
        asyncio.run(run_ensemble_pipeline(INPUT_CSV, OUTPUT_JSONL))
    else:
        print(f"[!] Input CSV '{INPUT_CSV}' not found.")