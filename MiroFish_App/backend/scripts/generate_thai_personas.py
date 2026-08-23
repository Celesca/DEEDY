#!/usr/bin/env python3
"""
Generate Thai Personas from Scraped Data (DEEDY)
Reads ensemble_ground_truth.jsonl and uses an LLM to generate Thai Archetype profiles.
"""

import os
import sys
import json
import logging
from typing import List, Dict, Any

# Setup paths to import backend modules
_scripts_dir = os.path.dirname(os.path.abspath(__file__))
_backend_dir = os.path.abspath(os.path.join(_scripts_dir, '..'))
sys.path.insert(0, _backend_dir)

from app.utils.openai_chat_compat import create_chat_completion, extract_chat_completion_text
from openai import OpenAI

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("thai_persona_generator")

def load_env():
    env_path = os.path.join(_backend_dir, "..", ".env")
    if not os.path.exists(env_path):
        return
    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

def generate_personas_sync(sample_size=30, max_personas=5):
    load_env()
    client = OpenAI(
        api_key=os.environ.get("OPENAI_API_KEY", "dummy"),
        base_url=os.environ.get("LLM_BASE_URL")
    )
    model = os.environ.get("LLM_MODEL_NAME", "gpt-4o")
    
    workspace_dir = os.path.dirname(_backend_dir)
    data_path = os.path.join(workspace_dir, "1_data-prep", "data", "ensemble_ground_truth.jsonl")
    
    if not os.path.exists(data_path):
        logger.error(f"Data file not found: {data_path}")
        return []

    logger.info("Loading scraped data...")
    snippets = []
    
    with open(data_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip(): continue
            data = json.loads(line)
            topic = data.get("topic", "")
            annotations = data.get("micro_post_annotations", [])
            for ann in annotations:
                snippet = ann.get("title_or_snippet", "")
                stance = ann.get("stance_label", "")
                sentiment = ann.get("sentiment_label", "")
                if snippet:
                    snippets.append(f"- Topic: {topic}\n  Text: '{snippet}'\n  Stance: {stance}\n  Sentiment: {sentiment}")

    # Sample to avoid huge prompt
    sampled_snippets = snippets[:sample_size]
    
    logger.info(f"Loaded {len(snippets)} snippets. Using {sample_size} for persona generation.")
    
    prompt = f"""
Based on the following Thai social media snippets and stances, generate {max_personas} distinct "Persona Archetypes" (Digital Twins) representing typical Thai netizens.

CRITICAL REQUIREMENT:
Since social media data only captures people who are passionate enough to post, it suffers from survivorship bias. Therefore, you MUST dedicate at least 1 of the {max_personas} archetypes to represent the "Silent Majority" (คนทั่วไปที่ไม่ได้สนใจดราม่า, เฉยๆ, หรือสนใจแต่ไม่กล้าแสดงออก). 

For each persona, define:
1. "agent_id": A unique snake_case ID (e.g. "angry_boomer")
2. "name": A realistic Thai nickname/username
3. "age": Estimated age
4. "occupation": Estimated occupation
5. "region": Thailand region (e.g. Bangkok, Isan)
6. "base_personality": A short description of their personality and attitude
7. "tone_of_voice": How they type (e.g. slang, polite, sarcastic, aggressive)
8. "deference": A number from 0-100 indicating respect for authority/seniority
9. "seniority_pressure": A number from 0-100 indicating how much they yield to peer pressure or elders

Snippets:
{{snippets_text}}

Output ONLY valid JSON in this format:
[
  {{
    "agent_id": "...",
    "name": "...",
    "age": 25,
    "occupation": "...",
    "region": "...",
    "base_personality": "...",
    "tone_of_voice": "...",
    "deference": 50,
    "seniority_pressure": 50
  }}
]
"""
    
    prompt_formatted = prompt.replace("{snippets_text}", "\n\n".join(sampled_snippets))
    
    messages = [
        {"role": "system", "content": "You are an expert sociologist and AI persona designer specializing in Thai social media behavior."},
        {"role": "user", "content": prompt_formatted}
    ]
    
    logger.info(f"Calling LLM ({model}) to generate personas...")
    try:
        response = create_chat_completion(
            client=client,
            model=model,
            messages=messages,
            temperature=0.7,
            response_format={"type": "json_object"} if "gpt" in model.lower() else None
        )
        output_text = extract_chat_completion_text(response)
        
        # Clean markdown code blocks if present
        if output_text.startswith("```json"):
            output_text = output_text[7:-3].strip()
        elif output_text.startswith("```"):
            output_text = output_text[3:-3].strip()
            
        personas = json.loads(output_text)
        if isinstance(personas, dict) and "personas" in personas:
            personas = personas["personas"]
            
        return personas
    except Exception as e:
        logger.error(f"Error generating personas: {e}")
        raise

def main():
    personas = generate_personas_sync()
    if not personas:
        return
        
    out_dir = os.path.join(_backend_dir, "data", "personas")
    os.makedirs(out_dir, exist_ok=True)
    
    out_path = os.path.join(out_dir, "thai_personas.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(personas, f, ensure_ascii=False, indent=2)
        
    logger.info(f"Successfully generated {len(personas)} personas and saved to {out_path}")

if __name__ == "__main__":
    main()
