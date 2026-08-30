#!/usr/bin/env python3
"""Run leakage-guarded OpenRouter pilots for DEEDY Experiments 4 and 5.

The LLM receives frozen campaign facts, persona prompts, and experimental
mechanism conditions.  It never receives authentic comments, target sentiment
ratios, or summaries derived from those comments.  Ground truth is loaded only
after generation and is used solely to score aggregate correspondence.

This is a cognitive-agent panel diagnostic.  It exposes concise stated
rationales and action choices, but it is not a replacement for a full OASIS
network trajectory or private chain-of-thought.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import random
import statistics
import sys
import threading
import time
import urllib.error
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from experiments.run_llm_exp123 import (
    COMPARISON_MODEL,
    FALLBACK_PRICING_PER_TOKEN,
    PRIMARY_MODEL,
    fetch_pricing,
    is_real_key,
    js_distance,
    load_env,
    quantile,
    request_json,
    sha256_file,
    stable_seed,
    validate_key,
)


FEEDS = ("chronological", "popularity", "interest")
NETWORKS = ("post_affiliation_proxy", "matched_random")
EXP5_VARIANTS = ("baseline", "clarity_frame")
SENTIMENTS = ("negative", "neutral", "positive")
ACTIONS = ("silence", "like", "share", "comment", "reply")

PERSONAS = (
    "วัยทำงานกรุงเทพฯ สนใจความคุ้มค่าและอ่านเงื่อนไขก่อนซื้อ",
    "นักศึกษาต่างจังหวัด ใช้ TikTok เป็นหลัก ชอบภาษากันเอง",
    "ผู้ปกครองวัยกลางคน ใช้ Facebook สนใจความปลอดภัยและค่าใช้จ่ายจริง",
    "พนักงานออฟฟิศที่ชอบทดลองสินค้าใหม่แต่ระวังราคา",
    "เจ้าของกิจการรายย่อย สนใจความน่าเชื่อถือและผลกระทบทางเศรษฐกิจ",
    "ผู้บริโภควัยเกษียณที่อ่านรายละเอียดและถามพนักงานก่อนตัดสินใจ",
    "ครีเอเตอร์สายอาหารและไลฟ์สไตล์ สนใจภาพลักษณ์และประเด็นไวรัล",
    "ผู้ใช้ทั่วไปที่ไม่ได้ติดตามแบรนด์และมักอ่านโดยไม่แสดงความเห็น",
)


@dataclass(frozen=True)
class Scenario:
    name: str
    baseline_message: str
    clarity_message: str
    scenario_details: dict
    source_urls: tuple[str, ...]


@dataclass(frozen=True)
class Job:
    experiment: str
    model: str
    scenario: Scenario
    seed: int
    feed: str
    network: str
    variant: str

    @property
    def key(self) -> str:
        return "|".join(
            (
                self.experiment,
                self.model,
                self.scenario.name,
                str(self.seed),
                self.feed,
                self.network,
                self.variant,
            )
        )


def read_jsonl(path: Path) -> Iterable[dict]:
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(f"Invalid JSON at {path}:{line_number}: {error}") from error


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


def load_scenarios(path: Path) -> list[Scenario]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    scenarios = [
        Scenario(
            name=str(item["name"]),
            baseline_message=str(item["baseline_message"]),
            clarity_message=str(item["clarity_message"]),
            scenario_details=dict(item["scenario_details"]),
            source_urls=tuple(item["source_urls"]),
        )
        for item in payload
    ]
    expected = {
        "Parameter Gelato",
        "KFC Bucket Ware",
        "MK Buffet",
        "วิ่งแลกแว่น | Top Charoen",
        "ไทยช่วยไทยพลัส",
    }
    names = {scenario.name for scenario in scenarios}
    if names != expected or len(scenarios) != 5:
        raise ValueError(f"Scenario names do not match the five registered campaigns: {names}")
    return scenarios


def load_targets(path: Path) -> dict[str, tuple[float, float, float]]:
    targets: dict[str, tuple[float, float, float]] = {}
    with path.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            targets[str(row["Topic"]).strip()] = (
                float(row["Negative_Ratio"]),
                float(row["Neutral_Ratio"]),
                float(row["Positive_Ratio"]),
            )
    if len(targets) != 5:
        raise ValueError(f"Expected five ground-truth campaigns, found {len(targets)}")
    return targets


def mechanism_description(feed: str, network: str) -> str:
    feeds = {
        "chronological": "เห็นโพสต์ตามลำดับเวลา โดยความใหม่สำคัญกว่าความนิยม",
        "popularity": "เห็นโพสต์ที่ระบบจัดอันดับจากความนิยมและ engagement ก่อน",
        "interest": "เห็นโพสต์ที่ระบบคัดตามความสนใจและความใกล้เคียงกับโปรไฟล์",
    }
    networks = {
        "post_affiliation_proxy": "ผู้ใช้ถูกจัดเป็นกลุ่มตามโพสต์ต้นทางเดียวกัน; นี่เป็น proxy ไม่ใช่เครือข่ายตอบกลับจริง",
        "matched_random": "ผู้ใช้เชื่อมต่อแบบสุ่มโดยควบคุมจำนวนเส้นเชื่อมให้ใกล้เคียงกับ proxy",
    }
    return f"นโยบายฟีด: {feeds[feed]}\nสมมติฐานเครือข่าย: {networks[network]}"


def build_prompt(job: Job, samples: int) -> tuple[str, str]:
    start = (job.seed - 1) % len(PERSONAS)
    personas = [PERSONAS[(start + index) % len(PERSONAS)] for index in range(samples)]
    message = (
        job.scenario.clarity_message
        if job.variant == "clarity_frame"
        else job.scenario.baseline_message
    )
    system = f"""คุณจำลองแผงผู้ใช้โซเชียลมีเดียชาวไทยจำนวน {samples} คนหลังได้รับ exposure ต่อข้อความแคมเปญ
ใช้เฉพาะข้อเท็จจริง สถานการณ์ กลไกฟีด และ persona ที่ให้ ห้ามอ้างว่าเห็นความคิดเห็นจริง ห้ามเดาสัดส่วนผลลัพธ์จริง และห้ามสร้างเงื่อนไขแคมเปญเพิ่มเติม
ให้แต่ละคนเลือก action หนึ่งค่า: silence, like, share, comment, reply และระบุ sentiment เป็น positive, neutral หรือ negative
`rationale_summary` ต้องเป็นเหตุผลสั้นหนึ่งประโยคที่ผู้ใช้จำลองยินดีเปิดเผย ไม่ใช่ chain-of-thought หรือการวิเคราะห์ทีละขั้น
คืน JSON object เดียวที่มี `agents` array จำนวน {samples} รายการ แต่ละรายการมี keys: agent_id, persona, action, text, sentiment, stance, narrative, rationale_summary, confidence
ถ้า action เป็น silence ให้ text เป็นสตริงว่าง แต่ยังต้องระบุ sentiment, stance, narrative และ rationale_summary ห้ามใช้ markdown หรือเพิ่ม key อื่นนอก JSON object
IMPORTANT: property names and enum values must remain exactly in English. Do not translate, rename, omit, or add properties.
รูปแบบตัวอย่างหนึ่งรายการ: {{"agent_id":"1","persona":"...","action":"comment","text":"...","sentiment":"neutral","stance":"question","narrative":"conditions","rationale_summary":"ต้องการทราบเงื่อนไขก่อนตัดสินใจ","confidence":"medium"}}"""
    user = (
        f"การทดลอง: {job.experiment}\n"
        f"แคมเปญ: {job.scenario.name}\n"
        f"เงื่อนไขข้อความ: {job.variant}\n"
        f"ข้อความที่ได้รับ:\n{message}\n\n"
        f"รายละเอียดสถานการณ์ที่อนุญาต:\n"
        f"{json.dumps(job.scenario.scenario_details, ensure_ascii=False, sort_keys=True)}\n\n"
        f"{mechanism_description(job.feed, job.network)}\n\n"
        f"persona ตาม agent_id 1-{samples}:\n"
        + "\n".join(f"{index + 1}. {persona}" for index, persona in enumerate(personas))
        + f"\nรหัสสุ่มการทดลอง: {job.seed}"
    )
    return system, user


def strip_json_fence(text: str) -> str:
    value = text.strip()
    if value.startswith("```"):
        parts = value.split("```", 2)
        if len(parts) >= 2:
            value = parts[1].removeprefix("json").strip()
    return value


def parse_agents(content: str, samples: int) -> list[dict]:
    payload = json.loads(strip_json_fence(content))
    if not isinstance(payload, dict) or not isinstance(payload.get("agents"), list):
        raise ValueError("Response does not contain an agents array")
    agents: list[dict] = []
    for index, item in enumerate(payload["agents"], start=1):
        if not isinstance(item, dict):
            continue
        action = str(item.get("action") or item.get("engagement_action") or "").strip().lower()
        action = {
            "read": "silence",
            "ignore": "silence",
            "อ่าน": "silence",
            "เงียบ": "silence",
            "ถูกใจ": "like",
            "กดไลก์": "like",
            "แชร์": "share",
            "ถาม": "comment",
            "inquire": "comment",
            "inform": "comment",
            "แสดงความคิดเห็น": "comment",
            "ตอบ": "reply",
            "ตอบกลับ": "reply",
        }.get(action, action)
        sentiment = str(item.get("sentiment") or item.get("emotion") or "").strip().lower()
        sentiment = {
            "บวก": "positive",
            "เชิงบวก": "positive",
            "กลาง": "neutral",
            "เป็นกลาง": "neutral",
            "curious": "neutral",
            "ลบ": "negative",
            "เชิงลบ": "negative",
        }.get(sentiment, sentiment)
        stance = str(item.get("stance") or item.get("position") or "").strip()
        narrative = str(item.get("narrative") or item.get("theme") or "").strip()
        rationale = str(
            item.get("rationale_summary") or item.get("rationale") or item.get("reason") or ""
        ).strip()
        agents.append(
            {
                "agent_id": str(item.get("agent_id") or index),
                "persona": str(item.get("persona") or "").strip(),
                "action": action,
                "text": str(item.get("text") or "").strip(),
                "sentiment": sentiment,
                "stance": stance,
                "narrative": narrative,
                "rationale_summary": rationale,
                "confidence": str(item.get("confidence") or "").strip().lower(),
                "schema_valid": action in ACTIONS
                and sentiment in SENTIMENTS
                and bool(stance)
                and bool(narrative)
                and bool(rationale),
            }
        )
    if not agents:
        raise ValueError("Response contains no usable agents")
    return agents[:samples]


def api_key() -> str:
    return (
        os.environ.get("OPENROUTER_API_KEY")
        or os.environ.get("LLM_API_KEY")
        or os.environ.get("OPENAI_API_KEY")
        or ""
    )


def prompt_hash(system: str, user: str) -> str:
    return hashlib.sha256((system + "\x1f" + user).encode("utf-8")).hexdigest()


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
            payload["seed"] = request_seed + attempt - 1
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
            agents = parse_agents(str(content), samples)
            if len(agents) != samples or not all(agent.get("schema_valid") for agent in agents):
                raise ValueError(
                    f"Agent schema incomplete: {sum(bool(agent.get('schema_valid')) for agent in agents)}/{samples} valid"
                )
            usage = response.get("usage") or {}
            prompt_tokens = int(usage.get("prompt_tokens") or 0)
            completion_tokens = int(usage.get("completion_tokens") or 0)
            rate = pricing[job.model]
            cost = prompt_tokens * rate["prompt"] + completion_tokens * rate["completion"]
            return {
                "job_key": job.key,
                "status": "ok",
                "experiment": job.experiment,
                "model": job.model,
                "campaign": job.scenario.name,
                "seed": job.seed,
                "feed": job.feed,
                "network": job.network,
                "variant": job.variant,
                "request_seed": int(payload["seed"]),
                "prompt_sha256": prompt_hash(system, user),
                "response_id": response.get("id"),
                "provider": response.get("provider"),
                "latency_seconds": time.monotonic() - started,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "cost_usd": cost,
                "requested_agents": samples,
                "returned_agents": len(agents),
                "agents": agents,
            }
        except (
            urllib.error.HTTPError,
            urllib.error.URLError,
            TimeoutError,
            KeyError,
            ValueError,
            json.JSONDecodeError,
        ) as error:
            if isinstance(error, urllib.error.HTTPError):
                last_error = f"HTTP {error.code}"
                retryable = error.code in (408, 409, 429) or error.code >= 500
            else:
                last_error = f"{type(error).__name__}: {str(error)[:180]}"
                retryable = True
            if attempt < retries and retryable:
                time.sleep(min(20.0, 2 ** (attempt - 1) + random.random()))
                continue
            break
    return {
        "job_key": job.key,
        "status": "error",
        "experiment": job.experiment,
        "model": job.model,
        "campaign": job.scenario.name,
        "seed": job.seed,
        "feed": job.feed,
        "network": job.network,
        "variant": job.variant,
        "request_seed": request_seed,
        "prompt_sha256": prompt_hash(system, user),
        "latency_seconds": time.monotonic() - started,
        "error": last_error,
    }


def record_metrics(record: dict, target: Sequence[float]) -> dict:
    agents = record.get("agents") or []
    valid = [agent for agent in agents if agent.get("schema_valid")]
    sentiments = Counter(agent["sentiment"] for agent in valid)
    actions = Counter(agent["action"] for agent in valid)
    total = max(1, len(valid))
    distribution = tuple(sentiments[label] / total for label in SENTIMENTS)
    narratives = [str(agent["narrative"]).strip().lower() for agent in valid]
    rationale_lengths = [len(str(agent["rationale_summary"])) for agent in valid]
    output = {
        key: record[key]
        for key in ("experiment", "model", "campaign", "seed", "feed", "network", "variant")
    }
    output.update(
        {
            "sentiment_js_distance": js_distance(target, distribution),
            "negative_share": distribution[0],
            "neutral_share": distribution[1],
            "positive_share": distribution[2],
            "visible_action_rate": 1.0 - actions["silence"] / total,
            "like_share": actions["like"] / total,
            "share_share": actions["share"] / total,
            "comment_share": actions["comment"] / total,
            "reply_share": actions["reply"] / total,
            "schema_valid_share": len(valid) / max(1, int(record.get("requested_agents") or total)),
            "narrative_count": len(set(narratives)),
            "mean_rationale_chars": statistics.fmean(rationale_lengths) if rationale_lengths else 0.0,
            "latency_seconds": float(record.get("latency_seconds") or 0),
            "prompt_tokens": int(record.get("prompt_tokens") or 0),
            "completion_tokens": int(record.get("completion_tokens") or 0),
            "cost_usd": float(record.get("cost_usd") or 0),
        }
    )
    return output


METRICS = (
    "sentiment_js_distance",
    "negative_share",
    "neutral_share",
    "positive_share",
    "visible_action_rate",
    "like_share",
    "share_share",
    "comment_share",
    "reply_share",
    "schema_valid_share",
    "narrative_count",
    "mean_rationale_chars",
    "latency_seconds",
    "prompt_tokens",
    "completion_tokens",
    "cost_usd",
)


def summarize(rows: Sequence[dict], fields: Sequence[str]) -> list[dict]:
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for row in rows:
        groups[tuple(row[field] for field in fields)].append(row)
    output: list[dict] = []
    for key in sorted(groups, key=lambda values: tuple(str(value) for value in values)):
        selected = groups[key]
        summary = {field: value for field, value in zip(fields, key)}
        summary["runs"] = len(selected)
        for metric in METRICS:
            values = [float(row[metric]) for row in selected]
            summary[f"{metric}_mean"] = statistics.fmean(values)
            summary[f"{metric}_median"] = statistics.median(values)
            summary[f"{metric}_ci_low"] = quantile(values, 0.025)
            summary[f"{metric}_ci_high"] = quantile(values, 0.975)
        output.append(summary)
    return output


def exp5_pairs(rows: Sequence[dict]) -> list[dict]:
    grouped: dict[tuple[str, str, int], dict[str, dict]] = defaultdict(dict)
    for row in rows:
        if row["experiment"] == "exp5_application":
            grouped[(row["model"], row["campaign"], row["seed"])][row["variant"]] = row
    output: list[dict] = []
    for (model, campaign, seed), pair in sorted(grouped.items()):
        if not all(variant in pair for variant in EXP5_VARIANTS):
            continue
        output.append(
            {
                "model": model,
                "campaign": campaign,
                "seed": seed,
                "jsd_clarity_minus_baseline": pair["clarity_frame"]["sentiment_js_distance"]
                - pair["baseline"]["sentiment_js_distance"],
                "positive_share_clarity_minus_baseline": pair["clarity_frame"]["positive_share"]
                - pair["baseline"]["positive_share"],
                "visible_action_rate_clarity_minus_baseline": pair["clarity_frame"]["visible_action_rate"]
                - pair["baseline"]["visible_action_rate"],
            }
        )
    return output


def short_model(model: str) -> str:
    if model == PRIMARY_MODEL:
        return "DeepSeek V4 Flash 0731"
    if model == COMPARISON_MODEL:
        return "Qwen3 8B"
    return model


def markdown_cell(value: object) -> str:
    return str(value).replace("|", r"\|")


def results_markdown(
    overall: Sequence[dict],
    campaign_rows: Sequence[dict],
    pairs: Sequence[dict],
    targets: dict[str, tuple[float, float, float]],
    calls: Sequence[dict],
) -> str:
    lines = [
        "# OpenRouter LLM pilot: Experiments 4--5",
        "",
        "> The LLM saw frozen scenario facts and experimental mechanism conditions only. Authentic comments, sentiment ratios, and real-data summaries were withheld until scoring. Stated rationales are short observable explanations, not private chain-of-thought.",
        "",
        "## Ground-truth scoring targets (scoring only)",
        "",
        "| Campaign | Negative | Neutral | Positive |",
        "|---|---:|---:|---:|",
    ]
    for campaign, target in targets.items():
        lines.append(
            f"| {markdown_cell(campaign)} | {target[0]:.3f} | {target[1]:.3f} | {target[2]:.3f} |"
        )
    lines.extend(
        [
            "",
            "## Experiment 4: LLM cognitive-agent mechanism diagnostic",
            "",
            "This prompt-level panel varies feed and network assumptions. It measures generated reaction/action differences and aggregate sentiment correspondence; it does not create a validated reply cascade.",
            "",
            "| Model | Feed | Network | Runs | JSD | Visible action | Positive | Neutral | Negative |",
            "|---|---|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in overall:
        if row["experiment"] != "exp4_social_mechanism":
            continue
        lines.append(
            f"| {short_model(row['model'])} | {row['feed']} | {row['network']} | {row['runs']} | "
            f"{row['sentiment_js_distance_mean']:.4f} | {row['visible_action_rate_mean']:.4f} | "
            f"{row['positive_share_mean']:.4f} | {row['neutral_share_mean']:.4f} | {row['negative_share_mean']:.4f} |"
        )
    lines.extend(
        [
            "",
            "## Experiment 5: baseline versus clarity frame",
            "",
            "| Model | Variant | Runs | JSD | Visible action | Positive | Neutral | Negative |",
            "|---|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in overall:
        if row["experiment"] != "exp5_application":
            continue
        lines.append(
            f"| {short_model(row['model'])} | {row['variant']} | {row['runs']} | "
            f"{row['sentiment_js_distance_mean']:.4f} | {row['visible_action_rate_mean']:.4f} | "
            f"{row['positive_share_mean']:.4f} | {row['neutral_share_mean']:.4f} | {row['negative_share_mean']:.4f} |"
        )
    lines.extend(["", "### Campaign-level Experiment 5 correspondence", "", "| Model | Campaign | Variant | JSD |", "|---|---|---|---:|"])
    for row in campaign_rows:
        if row["experiment"] == "exp5_application":
            lines.append(
                f"| {short_model(row['model'])} | {markdown_cell(row['campaign'])} | {row['variant']} | "
                f"{row['sentiment_js_distance_mean']:.4f} |"
            )
    if pairs:
        deltas = [float(row["jsd_clarity_minus_baseline"]) for row in pairs]
        lines.extend(
            [
                "",
                "### Paired clarity-frame effect",
                "",
                f"Across {len(pairs)} matched model/campaign/seed pairs, clarity minus baseline JSD was {statistics.fmean(deltas):.4f} (empirical 95% interval {quantile(deltas, 0.025):.4f} to {quantile(deltas, 0.975):.4f}). Negative values mean the clarity frame moved generated sentiment closer to the real aggregate target.",
            ]
        )
    lines.extend(
        [
            "",
            "## Execution summary",
            "",
            f"- Calls: {len(calls)}",
            f"- Failed calls: {sum(call.get('status') != 'ok' for call in calls)}",
            f"- Recorded cost: ${sum(float(call.get('cost_usd') or 0) for call in calls):.4f}",
            "- Full generated texts, actions, narratives, and rationale summaries are stored in `llm_exp45_calls.jsonl`.",
            "",
            "## Interpretation boundary",
            "",
            "These results test prompt-conditioned cognitive-agent reactions. They do not establish observed network or cascade fidelity, and the all-comment aggregate target is not an independent campaign holdout. A lower JSD is therefore diagnostic correspondence, not proof of forecasting accuracy.",
            "",
        ]
    )
    return "\n".join(lines)


def load_resume(path: Path) -> dict[str, dict]:
    return {str(record["job_key"]): record for record in read_jsonl(path)} if path.exists() else {}


def record_is_complete(record: dict, requested_agents: int) -> bool:
    agents = record.get("agents") or []
    return (
        record.get("status") == "ok"
        and len(agents) == requested_agents
        and all(agent.get("schema_valid") for agent in agents)
    )


def append_record(path: Path, record: dict, lock: threading.Lock) -> None:
    with lock:
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def build_jobs(models: Sequence[str], scenarios: Sequence[Scenario], seeds: int) -> list[Job]:
    jobs: list[Job] = []
    for model in models:
        for scenario in scenarios:
            for seed in range(1, seeds + 1):
                for feed in FEEDS:
                    for network in NETWORKS:
                        jobs.append(
                            Job(
                                "exp4_social_mechanism",
                                model,
                                scenario,
                                seed,
                                feed,
                                network,
                                "baseline",
                            )
                        )
                for variant in EXP5_VARIANTS:
                    jobs.append(
                        Job(
                            "exp5_application",
                            model,
                            scenario,
                            seed,
                            "interest",
                            "post_affiliation_proxy",
                            variant,
                        )
                    )
    return jobs


def estimate_cost(
    jobs: Sequence[Job], pricing: dict[str, dict[str, float]], max_tokens: int, samples: int
) -> float:
    return sum(
        len("".join(build_prompt(job, samples)).encode("utf-8")) * pricing[job.model]["prompt"]
        + max_tokens * pricing[job.model]["completion"]
        for job in jobs
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenarios", type=Path, default=Path("/app/experiments/exp45_scenarios.json"))
    parser.add_argument("--summary", type=Path, default=Path("/data-prep/apify/data/campaign_sentiment_summary.csv"))
    parser.add_argument("--output", type=Path, default=Path("/app/result"))
    parser.add_argument("--seeds", type=int, default=10)
    parser.add_argument("--agents-per-call", type=int, default=8)
    parser.add_argument("--max-tokens", type=int, default=2400)
    parser.add_argument("--temperature", type=float, default=0.8)
    parser.add_argument("--concurrency", type=int, default=6)
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--max-cost-usd", type=float, default=5.0)
    parser.add_argument("--models", nargs="+", default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--smoke-test", action="store_true")
    parser.add_argument("--limit-calls", type=int)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    load_env()
    args.output.mkdir(parents=True, exist_ok=True)
    scenarios = load_scenarios(args.scenarios)
    models = args.models or [
        os.environ.get("LLM_MODEL_NAME", PRIMARY_MODEL),
        os.environ.get("LLM_COMPARISON_MODEL_NAME", COMPARISON_MODEL),
    ]
    if len(models) != 2 or len(set(models)) != 2:
        raise ValueError("Exactly two distinct models are required")
    if args.seeds < 1 or args.agents_per_call < 3 or args.concurrency < 1:
        raise ValueError("seeds/concurrency must be positive and agents-per-call at least three")
    base_url = os.environ.get("LLM_BASE_URL", "https://openrouter.ai/api/v1")
    jobs = build_jobs(models, scenarios, args.seeds)
    if args.smoke_test:
        jobs = []
        for model in models:
            jobs.append(
                next(
                    job
                    for job in build_jobs(models, scenarios, args.seeds)
                    if job.model == model and job.experiment == "exp4_social_mechanism"
                )
            )
            for variant in EXP5_VARIANTS:
                jobs.append(
                    next(
                        job
                        for job in build_jobs(models, scenarios, args.seeds)
                        if job.model == model
                        and job.experiment == "exp5_application"
                        and job.variant == variant
                    )
                )
    if args.limit_calls:
        jobs = jobs[: args.limit_calls]
    pricing = fetch_pricing(base_url, models)
    estimated_cost = estimate_cost(jobs, pricing, args.max_tokens, args.agents_per_call)
    plan = {
        "models": models,
        "campaigns": [scenario.name for scenario in scenarios],
        "scenario_sources": {scenario.name: list(scenario.source_urls) for scenario in scenarios},
        "exp4_conditions": {"feeds": list(FEEDS), "networks": list(NETWORKS)},
        "exp5_variants": list(EXP5_VARIANTS),
        "seeds": args.seeds,
        "agents_per_call": args.agents_per_call,
        "unique_calls": len(jobs),
        "estimated_worst_case_cost_usd": estimated_cost,
        "max_cost_usd": args.max_cost_usd,
        "credentials_present": is_real_key(api_key()),
        "leakage_guard": "Prompts are built only from exp45_scenarios.json and mechanism/persona settings. The ground-truth CSV is loaded only after all LLM calls complete.",
    }
    write_json(args.output / "llm_exp45_plan.json", plan)
    if args.dry_run:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return 0
    if estimated_cost > args.max_cost_usd:
        raise RuntimeError(
            f"Estimated worst-case cost ${estimated_cost:.2f} exceeds cap ${args.max_cost_usd:.2f}"
        )
    key = api_key()
    if not is_real_key(key):
        raise RuntimeError("OPENROUTER_API_KEY is missing from MiroFish_App/.env")
    validate_key(base_url, key)

    calls_path = args.output / "llm_exp45_calls.jsonl"
    records = load_resume(calls_path)
    pending = [
        job
        for job in jobs
        if not record_is_complete(records.get(job.key, {}), args.agents_per_call)
    ]
    print(
        f"OpenRouter Exp. 4--5: {len(jobs)} planned, {len(jobs) - len(pending)} resumed, "
        f"{len(pending)} pending; estimated cap ${estimated_cost:.2f}"
    )
    lock = threading.Lock()
    with ThreadPoolExecutor(max_workers=args.concurrency) as executor:
        futures = {
            executor.submit(
                call_job,
                job,
                key=key,
                base_url=base_url,
                samples=args.agents_per_call,
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
            append_record(calls_path, record, lock)
            completed += 1
            if completed % 25 == 0 or completed == len(pending):
                ok = sum(
                    record_is_complete(item, args.agents_per_call)
                    for item in records.values()
                )
                print(f"progress={completed}/{len(pending)} total_ok={ok}")

    ordered = [records[job.key] for job in jobs if job.key in records]
    write_jsonl(calls_path, ordered)
    failures = [
        record
        for record in ordered
        if not record_is_complete(record, args.agents_per_call)
    ]
    failures_path = args.output / "llm_exp45_failures.json"
    if failures:
        write_json(failures_path, failures)
        raise RuntimeError(f"{len(failures)} calls failed; rerun the command to resume them")
    failures_path.unlink(missing_ok=True)

    # Leakage boundary: target data is loaded only after generation is complete.
    targets = load_targets(args.summary)
    metrics = [record_metrics(record, targets[record["campaign"]]) for record in ordered]
    overall = summarize(metrics, ("experiment", "model", "feed", "network", "variant"))
    campaign_rows = summarize(
        metrics, ("experiment", "model", "campaign", "feed", "network", "variant")
    )
    pairs = exp5_pairs(metrics)
    write_jsonl(args.output / "llm_exp45_metrics.jsonl", metrics)
    write_csv(args.output / "llm_exp45_overall_summary.csv", overall)
    write_csv(args.output / "llm_exp45_campaign_summary.csv", campaign_rows)
    write_csv(args.output / "llm_exp5_llm_paired_deltas.csv", pairs)
    (args.output / "LLM_EXP45_RESULTS.md").write_text(
        results_markdown(overall, campaign_rows, pairs, targets, ordered), encoding="utf-8"
    )
    artifacts = (
        "llm_exp45_plan.json",
        "llm_exp45_calls.jsonl",
        "llm_exp45_metrics.jsonl",
        "llm_exp45_overall_summary.csv",
        "llm_exp45_campaign_summary.csv",
        "llm_exp5_llm_paired_deltas.csv",
        "LLM_EXP45_RESULTS.md",
    )
    manifest = {
        "schema_version": "1.0",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "runner": {"path": "experiments/run_llm_exp45.py", "sha256": sha256_file(Path(__file__).resolve())},
        "inputs": {
            "scenarios": {"sha256": sha256_file(args.scenarios), "prompt_input": True},
            "ground_truth_summary": {"sha256": sha256_file(args.summary), "prompt_input": False, "use": "post-generation scoring only"},
        },
        "openrouter": {"base_url": base_url, "models": models, "key_validated": True},
        "parameters": {
            "seeds": list(range(1, args.seeds + 1)),
            "agents_per_call": args.agents_per_call,
            "feeds": list(FEEDS),
            "networks": list(NETWORKS),
            "exp5_variants": list(EXP5_VARIANTS),
            "reasoning_enabled": False,
            "temperature": args.temperature,
        },
        "row_counts": {"calls": len(ordered), "metrics": len(metrics), "exp5_pairs": len(pairs)},
        "actual_cost_usd": sum(float(record.get("cost_usd") or 0) for record in ordered),
        "interpretation_limits": [
            "Rationale summaries are model-stated observable explanations, not private chain-of-thought.",
            "Experiment 4 is a prompt-conditioned cognitive panel, not a full OASIS network trajectory.",
            "The post-affiliation graph is a proxy because the crawl contains no reply-parent links.",
            "The aggregate real-data target is scoring-only but is not an independent campaign holdout.",
            "No authentic comment text, author identifier, post URL, real sentiment ratio, or real-data summary was sent to the LLM.",
        ],
        "artifacts": {name: {"sha256": sha256_file(args.output / name)} for name in artifacts},
    }
    write_json(args.output / "llm_exp45_manifest.json", manifest)
    print(
        f"Completed {len(ordered)} OpenRouter calls and {len(metrics)} metric rows; "
        f"cost=${manifest['actual_cost_usd']:.4f}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
