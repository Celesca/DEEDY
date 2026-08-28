import json
import asyncio

# Prevent API rate limit explosion
llm_semaphore = asyncio.Semaphore(20)

import os
import httpx
import re

async def generate_agent_action(prompt: str, model: str = None) -> dict:
    if model is None:
        model = os.environ.get("LLM_MODEL_NAME", "deepseek/deepseek-v4-flash-0731")
    api_key = (
        os.environ.get("OPENROUTER_API_KEY")
        or os.environ.get("LLM_API_KEY")
        or os.environ.get("OPENAI_API_KEY", "")
    )
    base_url = os.environ.get("LLM_BASE_URL", "https://openrouter.ai/api/v1")
    headers = {"Authorization": f"Bearer {api_key}"}
    if os.environ.get("OPENROUTER_HTTP_REFERER"):
        headers["HTTP-Referer"] = os.environ["OPENROUTER_HTTP_REFERER"]
    if os.environ.get("OPENROUTER_APP_TITLE"):
        headers["X-OpenRouter-Title"] = os.environ["OPENROUTER_APP_TITLE"]
    
    async with llm_semaphore:
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{base_url}/chat/completions",
                    headers=headers,
                    json={
                        "model": model,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.7
                    },
                    timeout=15.0
                )
                data = response.json()
                
                if "choices" not in data:
                    print(f"API Error Response: {data.get('error', data)}")
                    return {"action": "IGNORE", "comment": "", "sentiment": 0}
                    
                content = data["choices"][0]["message"]["content"]
                
                # Try to extract JSON
                match = re.search(r'\{.*\}', content.replace('\n', ''))
                if match:
                    return json.loads(match.group(0))
                return json.loads(content)
            except Exception as e:
                print(f"LLM Processing Error: {e}")
                return {"action": "IGNORE", "comment": "", "sentiment": 0}

async def generate_reflection(metrics_summary: str, model: str = None) -> str:
    if model is None:
        model = os.environ.get("LLM_MODEL_NAME", "deepseek/deepseek-v4-flash-0731")
    api_key = (
        os.environ.get("OPENROUTER_API_KEY")
        or os.environ.get("LLM_API_KEY")
        or os.environ.get("OPENAI_API_KEY", "")
    )
    base_url = os.environ.get("LLM_BASE_URL", "https://openrouter.ai/api/v1")
    headers = {"Authorization": f"Bearer {api_key}"}
    if os.environ.get("OPENROUTER_HTTP_REFERER"):
        headers["HTTP-Referer"] = os.environ["OPENROUTER_HTTP_REFERER"]
    if os.environ.get("OPENROUTER_APP_TITLE"):
        headers["X-OpenRouter-Title"] = os.environ["OPENROUTER_APP_TITLE"]
    
    prompt = (
        "You are a Senior Marketing Analyst. Review the following simulation metrics and agent comments "
        "from a recent social media campaign.\n"
        f"{metrics_summary}\n\n"
        "Provide a concise, 2-paragraph analyst report. Paragraph 1: Summary of performance and sentiment. "
        "Paragraph 2: Key risks or recommendations for the brand."
    )
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{base_url}/chat/completions",
                headers=headers,
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.5
                },
                timeout=20.0
            )
            data = response.json()
            if "choices" not in data:
                print(f"Reflection API Error: {data.get('error', data)}")
                return "Failed to generate AI insights due to an API error."
            return data["choices"][0]["message"]["content"].strip()
        except Exception as e:
            print(f"Reflection Error: {e}")
            return "Failed to generate AI insights due to an API error."
