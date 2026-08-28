#!/usr/bin/env python3
"""Run the OpenRouter-backed pilot for paper Experiments 1--3.

The runner uses only aggregate campaign metadata for valid conditions.  The
deliberately leaky condition receives the observed aggregate sentiment summary
and is always labeled as an invalid diagnostic upper bound.  No authentic
comment text, author handle, or post URL is sent to OpenRouter or written to the
result bundle.

Equivalent model calls are reused across experiments:

* Exp. 1 seed-only == Exp. 2 Thai-context == Exp. 3 model comparison.
* Exp. 3 adds a deterministic non-generative uniform-prior ABM baseline.

This keeps the default live run to 500 calls instead of 700 while preserving
the five campaigns, ten seeds, two models, and five unique prompt conditions.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import random
import re
import statistics
import sys
import threading
import time
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from experiments.run_paper_pilot import js_distance, quantile, sha256_file, stable_seed


PRIMARY_MODEL = "deepseek/deepseek-v4-flash-0731"
COMPARISON_MODEL = "qwen/qwen3-8b"
CONDITIONS = (
    "seed_only_thai_context",
    "ungrounded",
    "leaky_all_source",
    "translated_unadapted",
    "normalization_no_context",
)
SENTIMENTS = ("negative", "neutral", "positive")
FALLBACK_PRICING_PER_TOKEN = {
    PRIMARY_MODEL: {"prompt": 0.035 / 1_000_000, "completion": 0.28 / 1_000_000},
    COMPARISON_MODEL: {"prompt": 0.117 / 1_000_000, "completion": 0.455 / 1_000_000},
}
METRICS = (
    "sentiment_js_distance",
    "positive_share",
    "neutral_share",
    "negative_share",
    "schema_valid_share",
    "thai_character_ratio",
    "latin_character_ratio",
    "exact_duplicate_share",
    "distinct_char_bigram",
    "narrative_count",
    "narrative_entropy",
    "mean_length_chars",
    "latency_seconds",
    "prompt_tokens",
    "completion_tokens",
    "cost_usd",
)

PERSONAS = (
    "วัยทำงานกรุงเทพฯ ใช้ Facebook และ TikTok สนใจความคุ้มค่า",
    "นักศึกษาต่างจังหวัด ใช้ TikTok เป็นหลัก ชอบภาษากันเอง",
    "ผู้ปกครองวัยกลางคน ใช้ Facebook สนใจความปลอดภัยและเงื่อนไข",
    "พนักงานออฟฟิศ ชอบทดลองสินค้าใหม่แต่ระวังราคา",
    "เจ้าของกิจการรายย่อย สนใจประโยชน์ใช้สอยและความน่าเชื่อถือ",
    "ผู้บริโภควัยเกษียณ ใช้ Facebook และอ่านรายละเอียดก่อนตัดสินใจ",
    "ครีเอเตอร์สายอาหาร สนใจภาพลักษณ์ รสชาติ และประเด็นไวรัล",
    "คนทำงานภาคอีสาน สนใจการเข้าถึงสาขาและค่าใช้จ่ายจริง",
    "คนรุ่นใหม่ภาคเหนือ ใช้ภาษาไทยปนอังกฤษเล็กน้อยและชอบมีม",
    "ผู้ใช้ทั่วไปภาคใต้ ไม่ได้ติดตามแบรนด์เป็นประจำและมักอ่านเงียบๆ",
)


@dataclass(frozen=True)
class Campaign:
    name: str
    positive: float
    neutral: float
    negative: float
    platforms: tuple[str, ...]
    post_count: int
    leaky_analysis: str

    @property
    def target(self) -> tuple[float, float, float]:
        return (self.negative, self.neutral, self.positive)


@dataclass(frozen=True)
class Job:
    model: str
    condition: str
    campaign: Campaign
    seed: int

    @property
    def key(self) -> str:
        return "|".join((self.model, self.condition, self.campaign.name, str(self.seed)))


def load_env() -> None:
    root = Path(__file__).resolve().parents[1]
    env_path = root / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def api_key() -> str:
    return (
        os.environ.get("OPENROUTER_API_KEY")
        or os.environ.get("LLM_API_KEY")
        or os.environ.get("OPENAI_API_KEY")
        or ""
    )


def is_real_key(value: str) -> bool:
    return bool(value) and "your-" not in value and "your_" not in value


def read_jsonl(path: Path) -> Iterable[dict]:
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(f"Invalid JSON at {path}:{line_number}: {error}") from error


def load_campaigns(summary_path: Path, threads_path: Path, analysis_path: Path) -> list[Campaign]:
    thread_meta: dict[str, dict] = defaultdict(lambda: {"platforms": set(), "posts": 0})
    for record in read_jsonl(threads_path):
        name = str(record.get("topic") or "").strip()
        if not name:
            continue
        thread_meta[name]["posts"] += 1
        platform_name = str(record.get("platform") or "").strip()
        if platform_name:
            thread_meta[name]["platforms"].add(platform_name)
    analyses = {
        str(record["topic"]): str(record.get("sentiment_direction_analysis") or "")
        for record in read_jsonl(analysis_path)
    }
    campaigns: list[Campaign] = []
    with summary_path.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            name = str(row["Topic"]).strip()
            meta = thread_meta.get(name)
            if not meta:
                raise ValueError(f"Missing thread metadata for {name}")
            campaigns.append(
                Campaign(
                    name=name,
                    positive=float(row["Positive_Ratio"]),
                    neutral=float(row["Neutral_Ratio"]),
                    negative=float(row["Negative_Ratio"]),
                    platforms=tuple(sorted(meta["platforms"])),
                    post_count=int(meta["posts"]),
                    leaky_analysis=analyses.get(name, ""),
                )
            )
    if len(campaigns) != 5:
        raise ValueError(f"Expected five campaigns, found {len(campaigns)}")
    return campaigns


def normalized_name(name: str) -> str:
    return re.sub(r"[^0-9A-Za-z\u0E00-\u0E7F ]+", " ", name).strip()


def build_prompt(job: Job, samples: int) -> tuple[str, str]:
    campaign = job.campaign
    persona = PERSONAS[(job.seed - 1) % len(PERSONAS)]
    schema = f"""Return one JSON object with a `responses` array containing exactly {samples} objects.
Each object must contain:
- `text`: one short, distinct social-media reaction in Thai;
- `sentiment`: exactly `positive`, `neutral`, or `negative`;
- `stance`: short label such as support, oppose, question, or unclear;
- `narrative`: a short reusable theme label;
- `sarcasm`: true or false.
Do not include markdown, analysis, probabilities, or extra keys outside the JSON object."""

    thai_system = (
        "คุณจำลองปฏิกิริยาของผู้ใช้โซเชียลมีเดียชาวไทยหลายคน "
        "แต่ละข้อความต้องเป็นธรรมชาติ แตกต่างกัน และไม่เหมารวมภูมิภาคหรือวัย "
        "อนุญาตภาษาพูด อีโมจิ การสะกดไม่เป็นทางการ และไทยปนอังกฤษเล็กน้อยตามบริบท "
        "ห้ามแต่งข้อเท็จจริงเกี่ยวกับแคมเปญนอกข้อมูลที่ให้ และห้ามอ้างว่าเห็นความคิดเห็นจริง\n\n"
        + schema
    )
    english_system = (
        "You simulate diverse consumer reactions using a generic translated social-media prompt. "
        "Write the reaction text in Thai, but do not use Thai-specific pragmatic, persona, regional, "
        "code-mixing, or conversational-context guidance. Do not invent campaign facts.\n\n"
        + schema
    )

    seed_packet = (
        f"ชื่อแคมเปญ: {campaign.name}\n"
        f"แพลตฟอร์มที่เก็บข้อมูล: {', '.join(campaign.platforms)}\n"
        f"จำนวนโพสต์ต้นทาง: {campaign.post_count}\n"
        "ขอบเขตข้อมูล: ไม่เปิดเผยความคิดเห็นจริง ป้ายกำกับผลลัพธ์ หรือสรุปกระแสให้โมเดล\n"
        f"ตัวอย่างบริบทผู้ใช้สำหรับรอบนี้: {persona}\n"
        f"รหัสสุ่มการทดลอง: {job.seed}"
    )

    if job.condition == "seed_only_thai_context":
        return thai_system, seed_packet
    if job.condition == "ungrounded":
        return (
            thai_system,
            f"ชื่อหัวข้อเท่านั้น: {campaign.name}\n"
            "ไม่มี scenario packet, platform metadata, observed labels, หรือความคิดเห็นจริง\n"
            f"รหัสสุ่มการทดลอง: {job.seed}",
        )
    if job.condition == "leaky_all_source":
        return (
            thai_system,
            seed_packet
            + "\n\nคำเตือน: เงื่อนไขนี้จงใจรั่วไหลและห้ามใช้เป็นผลระบบจริง\n"
            + (
                "สัดส่วนผลลัพธ์จากความคิดเห็นทั้งหมด: "
                f"positive={campaign.positive:.3f}, neutral={campaign.neutral:.3f}, "
                f"negative={campaign.negative:.3f}\n"
                f"สรุปกระแสจากข้อมูลเป้าหมาย: {campaign.leaky_analysis}"
            ),
        )
    if job.condition == "translated_unadapted":
        return english_system, (
            f"Campaign: {campaign.name}\n"
            f"Observed source platforms: {', '.join(campaign.platforms)}\n"
            f"Source post strata: {campaign.post_count}\n"
            "No real comments or outcome labels are available."
        )
    if job.condition == "normalization_no_context":
        return (
            "สร้างข้อความตอบสนองภาษาไทยแบบสั้นโดยใช้เฉพาะข้อมูลที่กำหนด "
            "ไม่มี persona, conversation context, cultural cue, หรือคำแนะนำด้านวัจนปฏิบัติ\n\n"
            + schema,
            f"ชื่อแคมเปญแบบ normalize: {normalized_name(campaign.name)}\n"
            f"แพลตฟอร์ม: {', '.join(campaign.platforms)}\n"
            f"รหัสสุ่ม: {job.seed}",
        )
    raise ValueError(f"Unknown condition: {job.condition}")


def prompt_hash(system: str, user: str) -> str:
    return hashlib.sha256((system + "\x1f" + user).encode("utf-8")).hexdigest()


def request_json(url: str, *, key: str = "", payload: dict | None = None, timeout: int = 180) -> dict:
    headers = {"Content-Type": "application/json"}
    if key:
        headers["Authorization"] = f"Bearer {key}"
    if os.environ.get("OPENROUTER_HTTP_REFERER"):
        headers["HTTP-Referer"] = os.environ["OPENROUTER_HTTP_REFERER"]
    if os.environ.get("OPENROUTER_APP_TITLE"):
        headers["X-OpenRouter-Title"] = os.environ["OPENROUTER_APP_TITLE"]
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload else None
    request = urllib.request.Request(url, data=body, headers=headers)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.load(response)


def validate_key(base_url: str, key: str) -> None:
    try:
        request_json(f"{base_url.rstrip('/')}/key", key=key, timeout=30)
    except urllib.error.HTTPError as error:
        raise RuntimeError(f"OpenRouter key validation failed with HTTP {error.code}") from error


def fetch_pricing(base_url: str, models: Sequence[str]) -> dict[str, dict[str, float]]:
    pricing = {model: dict(FALLBACK_PRICING_PER_TOKEN.get(model, {})) for model in models}
    try:
        payload = request_json(f"{base_url.rstrip('/')}/models", timeout=45)
        catalog = {item.get("id"): item for item in payload.get("data", [])}
        missing = [model for model in models if model not in catalog]
        if missing:
            raise ValueError(f"Models missing from OpenRouter catalog: {missing}")
        for model in models:
            model_pricing = catalog[model].get("pricing") or {}
            pricing[model] = {
                "prompt": float(model_pricing.get("prompt") or 0),
                "completion": float(model_pricing.get("completion") or 0),
            }
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as error:
        print(f"Warning: using pinned fallback pricing because catalog lookup failed: {error}")
    return pricing


def strip_json_fence(text: str) -> str:
    value = text.strip()
    if value.startswith("```"):
        parts = value.split("```", 2)
        if len(parts) >= 2:
            value = parts[1].removeprefix("json").strip()
    return value


def parse_responses(content: str) -> list[dict]:
    parsed = json.loads(strip_json_fence(content))
    if not isinstance(parsed, dict) or not isinstance(parsed.get("responses"), list):
        raise ValueError("Response does not contain a responses array")
    output: list[dict] = []
    for item in parsed["responses"]:
        if not isinstance(item, dict):
            continue
        sentiment = str(item.get("sentiment") or "").lower().strip()
        output.append(
            {
                "text": str(item.get("text") or "").strip(),
                "sentiment": sentiment,
                "stance": str(item.get("stance") or "").strip(),
                "narrative": str(item.get("narrative") or "").strip(),
                "sarcasm": bool(item.get("sarcasm", False)),
                "schema_valid": bool(item.get("text"))
                and sentiment in SENTIMENTS
                and bool(item.get("stance"))
                and bool(item.get("narrative")),
            }
        )
    return output


def call_job(
    job: Job,
    *,
    key: str,
    base_url: str,
    samples: int,
    max_tokens: int,
    temperature: float,
    pricing: dict[str, dict[str, float]],
    retries: int,
) -> dict:
    system, user = build_prompt(job, samples)
    request_seed = stable_seed(job.key, "openrouter") % 2_147_483_647
    payload = {
        "model": job.model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
        "seed": request_seed,
        "response_format": {"type": "json_object"},
        "reasoning": {"enabled": False},
    }
    started = time.monotonic()
    last_error = ""
    for attempt in range(1, retries + 1):
        try:
            response = request_json(
                f"{base_url.rstrip('/')}/chat/completions",
                key=key,
                payload=payload,
                timeout=240,
            )
            message = response["choices"][0]["message"]
            content = message.get("content") or ""
            if isinstance(content, list):
                content = "".join(
                    block.get("text", "")
                    for block in content
                    if isinstance(block, dict)
                )
            responses = parse_responses(str(content))
            usage = response.get("usage") or {}
            prompt_tokens = int(usage.get("prompt_tokens") or 0)
            completion_tokens = int(usage.get("completion_tokens") or 0)
            rate = pricing[job.model]
            cost = prompt_tokens * rate["prompt"] + completion_tokens * rate["completion"]
            return {
                "job_key": job.key,
                "status": "ok",
                "model": job.model,
                "condition": job.condition,
                "campaign": job.campaign.name,
                "seed": job.seed,
                "request_seed": request_seed,
                "prompt_sha256": prompt_hash(system, user),
                "response_id": response.get("id"),
                "provider": response.get("provider"),
                "latency_seconds": time.monotonic() - started,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "cost_usd": cost,
                "requested_samples": samples,
                "returned_samples": len(responses),
                "responses": responses,
            }
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, KeyError, ValueError, json.JSONDecodeError) as error:
            if isinstance(error, urllib.error.HTTPError):
                last_error = f"HTTP {error.code}"
                retryable = error.code in (408, 409, 429) or error.code >= 500
            else:
                last_error = f"{type(error).__name__}: {str(error)[:160]}"
                retryable = True
            if attempt < retries and retryable:
                time.sleep(min(20.0, 2 ** (attempt - 1) + random.random()))
                continue
            break
    return {
        "job_key": job.key,
        "status": "error",
        "model": job.model,
        "condition": job.condition,
        "campaign": job.campaign.name,
        "seed": job.seed,
        "request_seed": request_seed,
        "prompt_sha256": prompt_hash(system, user),
        "latency_seconds": time.monotonic() - started,
        "error": last_error,
    }


def letter_ratios(texts: Sequence[str]) -> tuple[float, float]:
    letters = [character for text in texts for character in text if character.isalpha()]
    if not letters:
        return 0.0, 0.0
    thai = sum("\u0E00" <= character <= "\u0E7F" for character in letters)
    latin = sum(
        ("a" <= character.lower() <= "z")
        for character in letters
    )
    return thai / len(letters), latin / len(letters)


def entropy(labels: Sequence[str]) -> float:
    if not labels:
        return 0.0
    counts = Counter(labels)
    total = len(labels)
    return -sum((count / total) * math.log2(count / total) for count in counts.values())


def record_metrics(record: dict, campaign: Campaign) -> dict:
    responses = record.get("responses") or []
    valid = [item for item in responses if item.get("schema_valid")]
    sentiment_counts = Counter(item["sentiment"] for item in valid)
    denominator = max(1, sum(sentiment_counts.values()))
    negative = sentiment_counts["negative"] / denominator
    neutral = sentiment_counts["neutral"] / denominator
    positive = sentiment_counts["positive"] / denominator
    texts = [str(item["text"]) for item in valid]
    thai_ratio, latin_ratio = letter_ratios(texts)
    normalized_texts = [re.sub(r"\s+", "", text.lower()) for text in texts if text]
    bigrams = [
        text[index : index + 2]
        for text in normalized_texts
        for index in range(max(0, len(text) - 1))
    ]
    narratives = [str(item["narrative"]).strip().lower() for item in valid]
    returned = int(record.get("returned_samples") or 0)
    requested = int(record.get("requested_samples") or returned or 1)
    return {
        "campaign": campaign.name,
        "seed": record["seed"],
        "source_condition": record["condition"],
        "model": record["model"],
        "sentiment_js_distance": js_distance(campaign.target, (negative, neutral, positive)),
        "positive_share": positive,
        "neutral_share": neutral,
        "negative_share": negative,
        "schema_valid_share": len(valid) / requested,
        "thai_character_ratio": thai_ratio,
        "latin_character_ratio": latin_ratio,
        "exact_duplicate_share": 1.0 - len(set(normalized_texts)) / max(1, len(normalized_texts)),
        "distinct_char_bigram": len(set(bigrams)) / max(1, len(bigrams)),
        "narrative_count": len(set(narratives)),
        "narrative_entropy": entropy(narratives),
        "mean_length_chars": statistics.fmean(map(len, texts)) if texts else 0.0,
        "latency_seconds": float(record.get("latency_seconds") or 0),
        "prompt_tokens": int(record.get("prompt_tokens") or 0),
        "completion_tokens": int(record.get("completion_tokens") or 0),
        "cost_usd": float(record.get("cost_usd") or 0),
    }


def expand_experiments(call_records: Sequence[dict], campaigns: Sequence[Campaign], samples: int) -> list[dict]:
    by_campaign = {campaign.name: campaign for campaign in campaigns}
    expanded: list[dict] = []
    for record in call_records:
        if record.get("status") != "ok":
            continue
        base = record_metrics(record, by_campaign[record["campaign"]])
        source = record["condition"]
        mappings: list[tuple[str, str]] = []
        if source == "seed_only_thai_context":
            mappings.extend(
                [
                    ("exp1_grounding", "seed_only"),
                    ("exp2_thai_adaptation", "thai_context_prompt"),
                    ("exp3_core_model", "deepseek_v4_flash" if record["model"] == PRIMARY_MODEL else "qwen3_8b"),
                ]
            )
        elif source == "ungrounded":
            mappings.append(("exp1_grounding", "ungrounded"))
        elif source == "leaky_all_source":
            mappings.append(("exp1_grounding", "leaky_invalid_upper_bound"))
        elif source == "translated_unadapted":
            mappings.append(("exp2_thai_adaptation", "translated_unadapted"))
        elif source == "normalization_no_context":
            mappings.append(("exp2_thai_adaptation", "normalization_no_context"))
        for experiment, condition in mappings:
            expanded.append({"experiment": experiment, "condition": condition, **base})

    for campaign in campaigns:
        for seed in sorted({int(record["seed"]) for record in call_records}):
            rng = random.Random(stable_seed(campaign.name, seed, "uniform_abm"))
            labels = [rng.choice(SENTIMENTS) for _ in range(samples)]
            counts = Counter(labels)
            distribution = tuple(counts[label] / samples for label in SENTIMENTS)
            expanded.append(
                {
                    "experiment": "exp3_core_model",
                    "condition": "non_generative_uniform_abm",
                    "campaign": campaign.name,
                    "seed": seed,
                    "source_condition": "non_generative_uniform_abm",
                    "model": "none",
                    "sentiment_js_distance": js_distance(campaign.target, distribution),
                    "positive_share": distribution[2],
                    "neutral_share": distribution[1],
                    "negative_share": distribution[0],
                    "schema_valid_share": 1.0,
                    "thai_character_ratio": None,
                    "latin_character_ratio": None,
                    "exact_duplicate_share": None,
                    "distinct_char_bigram": None,
                    "narrative_count": None,
                    "narrative_entropy": None,
                    "mean_length_chars": None,
                    "latency_seconds": 0.0,
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "cost_usd": 0.0,
                }
            )
    return expanded


def summarize(rows: Sequence[dict], group_fields: Sequence[str]) -> list[dict]:
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for row in rows:
        groups[tuple(row[field] for field in group_fields)].append(row)
    output: list[dict] = []
    for key in sorted(groups, key=lambda values: tuple(str(value) for value in values)):
        selected = groups[key]
        summary = {field: value for field, value in zip(group_fields, key)}
        summary["runs"] = len(selected)
        for metric in METRICS:
            values = [float(row[metric]) for row in selected if row.get(metric) is not None]
            if not values:
                summary[f"{metric}_mean"] = None
                summary[f"{metric}_median"] = None
                summary[f"{metric}_ci_low"] = None
                summary[f"{metric}_ci_high"] = None
                continue
            summary[f"{metric}_mean"] = statistics.fmean(values)
            summary[f"{metric}_median"] = statistics.median(values)
            summary[f"{metric}_ci_low"] = quantile(values, 0.025)
            summary[f"{metric}_ci_high"] = quantile(values, 0.975)
        output.append(summary)
    return output


def exp3_paired_effects(rows: Sequence[dict]) -> list[dict]:
    selected = [row for row in rows if row["experiment"] == "exp3_core_model"]
    pairs: dict[tuple[str, int], dict[str, dict]] = defaultdict(dict)
    for row in selected:
        pairs[(row["campaign"], row["seed"])][row["condition"]] = row
    output: list[dict] = []
    for (campaign, seed), pair in sorted(pairs.items()):
        if "deepseek_v4_flash" not in pair or "qwen3_8b" not in pair:
            continue
        item: dict[str, object] = {"campaign": campaign, "seed": seed}
        for metric in METRICS:
            left = pair["deepseek_v4_flash"].get(metric)
            right = pair["qwen3_8b"].get(metric)
            item[f"{metric}_deepseek_minus_qwen"] = (
                float(left) - float(right) if left is not None and right is not None else None
            )
        output.append(item)
    return output


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: Sequence[dict]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def write_csv(path: Path, rows: Sequence[dict]) -> None:
    if not rows:
        raise ValueError(f"Cannot write empty CSV: {path}")
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def load_resume(path: Path) -> dict[str, dict]:
    if not path.exists():
        return {}
    records: dict[str, dict] = {}
    for record in read_jsonl(path):
        records[str(record["job_key"])] = record
    return records


def append_record(path: Path, record: dict, lock: threading.Lock) -> None:
    line = json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n"
    with lock:
        with path.open("a", encoding="utf-8") as handle:
            handle.write(line)


def estimate_cost(
    jobs: Sequence[Job],
    pricing: dict[str, dict[str, float]],
    max_tokens: int,
    samples: int,
) -> float:
    # UTF-8 byte count is a deliberately conservative prompt-token ceiling for
    # the Thai prompts. Completion spend is strictly bounded by max_tokens.
    return sum(
        len("".join(build_prompt(job, samples)).encode("utf-8"))
        * pricing[job.model]["prompt"]
        + max_tokens * pricing[job.model]["completion"]
        for job in jobs
    )


def short_model(model: str) -> str:
    if model == PRIMARY_MODEL:
        return "DeepSeek V4 Flash 0731"
    if model == COMPARISON_MODEL:
        return "Qwen3 8B"
    return model


def build_results_markdown(summary: Sequence[dict], paired: Sequence[dict], call_records: Sequence[dict]) -> str:
    rows = {(row["experiment"], row["condition"], row["model"]): row for row in summary}
    lines = [
        "# OpenRouter LLM pilot: Experiments 1--3",
        "",
        "Models: `deepseek/deepseek-v4-flash-0731` and `qwen/qwen3-8b`. Each LLM row aggregates five campaigns and ten seeds (50 runs); each call requested 12 synthetic Thai reactions.",
        "",
        "> Scope: sentiment is self-labeled by the generating model and compared with an all-comment aggregate target. There are no native-Thai human ratings or independent campaign holdouts, so these are pilot diagnostics rather than final validation.",
        "",
    ]
    for experiment, title in (
        ("exp1_grounding", "Experiment 1: grounding"),
        ("exp2_thai_adaptation", "Experiment 2: Thai prompt adaptation"),
        ("exp3_core_model", "Experiment 3: core model"),
    ):
        lines.extend(
            [
                f"## {title}",
                "",
                "| Condition | Model | Runs | Sentiment JSD | Thai ratio | Duplicate share | Schema valid | Mean cost/run |",
                "|---|---|---:|---:|---:|---:|---:|---:|",
            ]
        )
        for (row_experiment, condition, model), row in sorted(rows.items()):
            if row_experiment != experiment:
                continue
            def fmt(name: str) -> str:
                value = row.get(name)
                return "--" if value is None else f"{float(value):.4f}"
            lines.append(
                f"| {condition} | {short_model(model)} | {row['runs']} | "
                f"{fmt('sentiment_js_distance_mean')} | {fmt('thai_character_ratio_mean')} | "
                f"{fmt('exact_duplicate_share_mean')} | {fmt('schema_valid_share_mean')} | "
                f"${fmt('cost_usd_mean')} |"
            )
        lines.append("")
    total_cost = sum(float(record.get("cost_usd") or 0) for record in call_records)
    failures = sum(record.get("status") != "ok" for record in call_records)
    lines.extend(
        [
            "## Execution summary",
            "",
            f"- Unique OpenRouter calls: {len(call_records)}",
            f"- Failed calls: {failures}",
            f"- Recorded model cost: ${total_cost:.4f}",
            f"- Matched DeepSeek/Qwen pairs in Exp. 3: {len(paired)}",
            "",
            "The deliberately leaky Exp. 1 row is an invalid diagnostic bound and must never be reported as DEEDY performance. The non-generative ABM emits sentiment states only, so Thai-language and text-diversity cells are intentionally absent.",
            "",
        ]
    )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary", required=True, type=Path)
    parser.add_argument("--threads", required=True, type=Path)
    parser.add_argument("--analysis", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--seeds", type=int, default=10)
    parser.add_argument("--samples", type=int, default=12)
    parser.add_argument("--max-tokens", type=int, default=2200)
    parser.add_argument("--temperature", type=float, default=0.8)
    parser.add_argument("--concurrency", type=int, default=6)
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--max-cost-usd", type=float, default=5.0)
    parser.add_argument("--models", nargs="+", default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit-calls", type=int)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    load_env()
    args.output.mkdir(parents=True, exist_ok=True)
    models = args.models or [
        os.environ.get("LLM_MODEL_NAME", PRIMARY_MODEL),
        os.environ.get("LLM_COMPARISON_MODEL_NAME", COMPARISON_MODEL),
    ]
    if len(models) != 2 or len(set(models)) != 2:
        raise ValueError("Exactly two distinct models are required")
    if args.seeds < 1 or args.samples < 3 or args.concurrency < 1:
        raise ValueError("seeds/concurrency must be positive and samples must be at least three")
    base_url = os.environ.get("LLM_BASE_URL", "https://openrouter.ai/api/v1")
    campaigns = load_campaigns(args.summary, args.threads, args.analysis)
    jobs = [
        Job(model=model, condition=condition, campaign=campaign, seed=seed)
        for model in models
        for condition in CONDITIONS
        for campaign in campaigns
        for seed in range(1, args.seeds + 1)
    ]
    if args.limit_calls:
        jobs = jobs[: args.limit_calls]
    pricing = fetch_pricing(base_url, models)
    estimated_cost = estimate_cost(jobs, pricing, args.max_tokens, args.samples)
    plan = {
        "models": models,
        "conditions": list(CONDITIONS),
        "campaigns": [campaign.name for campaign in campaigns],
        "seeds": args.seeds,
        "samples_per_call": args.samples,
        "unique_calls": len(jobs),
        "expanded_experiment_rows_expected": 750 if not args.limit_calls and args.seeds == 10 else None,
        "estimated_worst_case_cost_usd": estimated_cost,
        "max_cost_usd": args.max_cost_usd,
        "credentials_present": is_real_key(api_key()),
        "pricing_per_token": pricing,
        "leakage_guard": "Only leaky_all_source receives observed aggregate ratios/analysis; no raw comments or URLs are used.",
    }
    write_json(args.output / "llm_exp123_plan.json", plan)
    if args.dry_run:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return 0
    if estimated_cost > args.max_cost_usd:
        raise RuntimeError(
            f"Estimated worst-case cost ${estimated_cost:.2f} exceeds cap ${args.max_cost_usd:.2f}"
        )
    key = api_key()
    if not is_real_key(key):
        raise RuntimeError(
            "OPENROUTER_API_KEY is missing. Add it to MiroFish_App/.env; the key is never printed or committed."
        )
    validate_key(base_url, key)

    calls_path = args.output / "llm_exp123_calls.jsonl"
    records = load_resume(calls_path)
    pending = [job for job in jobs if records.get(job.key, {}).get("status") != "ok"]
    print(
        f"OpenRouter Exp. 1--3: {len(jobs)} planned, {len(jobs) - len(pending)} resumed, "
        f"{len(pending)} pending; estimated cap ${estimated_cost:.2f}"
    )
    write_lock = threading.Lock()
    with ThreadPoolExecutor(max_workers=args.concurrency) as executor:
        futures = {
            executor.submit(
                call_job,
                job,
                key=key,
                base_url=base_url,
                samples=args.samples,
                max_tokens=args.max_tokens,
                temperature=args.temperature,
                pricing=pricing,
                retries=args.retries,
            ): job
            for job in pending
        }
        completed = 0
        for future in as_completed(futures):
            record = future.result()
            records[record["job_key"]] = record
            append_record(calls_path, record, write_lock)
            completed += 1
            if completed % 25 == 0 or completed == len(pending):
                ok_count = sum(item.get("status") == "ok" for item in records.values())
                print(f"progress={completed}/{len(pending)} total_ok={ok_count}")

    ordered_records = [records[job.key] for job in jobs if job.key in records]
    write_jsonl(calls_path, ordered_records)
    failures = [record for record in ordered_records if record.get("status") != "ok"]
    if failures:
        write_json(args.output / "llm_exp123_failures.json", failures)
        raise RuntimeError(
            f"{len(failures)} calls failed. Re-run the same command to resume only failed jobs."
        )

    expanded = expand_experiments(ordered_records, campaigns, args.samples)
    overall = summarize(expanded, ("experiment", "condition", "model"))
    campaign_summary = summarize(
        expanded, ("experiment", "condition", "model", "campaign")
    )
    paired = exp3_paired_effects(expanded)
    write_jsonl(args.output / "llm_exp123_metrics.jsonl", expanded)
    write_csv(args.output / "llm_exp123_overall_summary.csv", overall)
    write_csv(args.output / "llm_exp123_campaign_summary.csv", campaign_summary)
    write_csv(args.output / "llm_exp3_paired_effects.csv", paired)
    (args.output / "LLM_EXP123_RESULTS.md").write_text(
        build_results_markdown(overall, paired, ordered_records), encoding="utf-8"
    )

    artifact_names = [
        "llm_exp123_plan.json",
        "llm_exp123_calls.jsonl",
        "llm_exp123_metrics.jsonl",
        "llm_exp123_overall_summary.csv",
        "llm_exp123_campaign_summary.csv",
        "llm_exp3_paired_effects.csv",
        "LLM_EXP123_RESULTS.md",
    ]
    manifest = {
        "schema_version": "1.0",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "runner": {
            "path": "experiments/run_llm_exp123.py",
            "sha256": sha256_file(Path(__file__).resolve()),
        },
        "openrouter": {
            "base_url": base_url,
            "models": models,
            "pricing_per_token_at_run": pricing,
            "key_validated": True,
        },
        "inputs": {
            "summary": {"sha256": sha256_file(args.summary)},
            "threads": {"sha256": sha256_file(args.threads)},
            "analysis": {"sha256": sha256_file(args.analysis)},
        },
        "parameters": {
            "conditions": list(CONDITIONS),
            "seeds": list(range(1, args.seeds + 1)),
            "samples_per_call": args.samples,
            "max_tokens": args.max_tokens,
            "temperature": args.temperature,
            "reasoning_enabled": False,
            "concurrency": args.concurrency,
            "max_cost_usd": args.max_cost_usd,
        },
        "row_counts": {
            "unique_calls": len(ordered_records),
            "expanded_metric_rows": len(expanded),
            "exp3_pairs": len(paired),
        },
        "actual_cost_usd": sum(float(record.get("cost_usd") or 0) for record in ordered_records),
        "interpretation_limits": [
            "Generated sentiment labels are model self-reports, not independent human annotations.",
            "Observed target ratios aggregate all comments and are not a campaign-held-out test set.",
            "The leaky condition is an invalid diagnostic upper bound.",
            "The Thai-context condition is a prompt-level proxy; native-Thai quality ratings remain pending.",
            "The non-generative ABM produces sentiment states but no language.",
            "No authentic comment text, author identifier, or post URL was sent to OpenRouter.",
        ],
        "artifacts": {
            name: {"sha256": sha256_file(args.output / name)} for name in artifact_names
        },
    }
    write_json(args.output / "llm_exp123_manifest.json", manifest)
    print(
        f"Completed {len(ordered_records)} OpenRouter calls, {len(expanded)} experiment rows, "
        f"cost=${manifest['actual_cost_usd']:.4f}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
