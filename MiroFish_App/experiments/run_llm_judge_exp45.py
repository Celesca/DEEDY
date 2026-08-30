#!/usr/bin/env python3
"""Run a blinded OpenRouter LLM-as-a-judge evaluation for DEEDY Exp. 4--5.

The judge compares one visible synthetic reaction from every completed Exp. 4--5
generation call with one authentic, same-campaign comment. Each pair is judged
twice with reversed A/B order. Author fields, URLs, post identifiers, and raw
comment text are never written to the result bundle. Authentic comment text is
sanitized before it is sent to the judge. Campaign-level sentiment analyses and
aggregate ratios are withheld until all judging calls finish and are used only
for post-judging correspondence checks.

This is a secondary quality diagnostic. It does not replace native-Thai human
ratings, held-out behavioral outcomes, or observed network/cascade validation.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import random
import re
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
    api_key,
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
from experiments.run_llm_exp45 import (
    Scenario,
    load_scenarios,
    load_targets,
    read_jsonl,
    strip_json_fence,
    write_csv,
    write_json,
    write_jsonl,
)


JUDGE_MODEL = "z-ai/glm-5.3-flash"
FALLBACK_PRICING_PER_TOKEN = {
    JUDGE_MODEL: {"prompt": 0.15 / 1_000_000, "completion": 0.50 / 1_000_000}
}
DIMENSIONS = (
    "thai_naturalness",
    "campaign_relevance",
    "social_media_plausibility",
    "pragmatic_cultural_fit",
    "contextual_specificity",
    "unsupported_claim_risk",
)
SENTIMENTS = ("negative", "neutral", "positive")
STANCES = ("support", "oppose", "question", "unclear", "mixed")
PREFERENCES = ("A", "B", "tie")
URL_RE = re.compile(r"(?i)\b(?:https?://|www\.)\S+")
EMAIL_RE = re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b")
MENTION_RE = re.compile(r"(?<!\w)@[A-Za-z0-9_.-]+")
PHONE_RE = re.compile(r"(?<!\d)(?:\+?66|0)[\d\s().-]{7,14}\d(?!\d)")
SPACE_RE = re.compile(r"\s+")


@dataclass(frozen=True)
class PairJob:
    pair_id: str
    synthetic_job_key: str
    experiment: str
    generator_model: str
    campaign: str
    seed: int
    feed: str
    network: str
    variant: str
    real_platform: str
    real_text: str
    real_comment_sha256: str
    real_locator_sha256: str
    synthetic_text: str
    synthetic_text_sha256: str
    synthetic_action: str
    synthetic_agent_id: str
    scenario: Scenario


@dataclass(frozen=True)
class JudgeJob:
    pair: PairJob
    orientation: int

    @property
    def key(self) -> str:
        return f"{self.pair.pair_id}|orientation={self.orientation}"

    @property
    def a_source(self) -> str:
        first_real = stable_seed(self.pair.pair_id, "initial-order") % 2 == 0
        if self.orientation == 1:
            first_real = not first_real
        return "real" if first_real else "synthetic"

    @property
    def b_source(self) -> str:
        return "synthetic" if self.a_source == "real" else "real"

    def text_for(self, source: str) -> str:
        return self.pair.real_text if source == "real" else self.pair.synthetic_text


def sanitize_comment(text: object, max_chars: int = 600) -> tuple[str, bool]:
    value = str(text or "").replace("\x00", " ")
    value = URL_RE.sub("[URL]", value)
    value = EMAIL_RE.sub("[EMAIL]", value)
    value = MENTION_RE.sub("[MENTION]", value)
    value = PHONE_RE.sub("[PHONE]", value)
    value = SPACE_RE.sub(" ", value).strip()
    truncated = len(value) > max_chars
    if truncated:
        value = value[:max_chars].rstrip() + "..."
    return value, truncated


def text_sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def load_real_comments(path: Path) -> dict[str, list[dict]]:
    campaigns: dict[str, list[dict]] = defaultdict(list)
    for thread in read_jsonl(path):
        campaign = str(thread.get("topic") or "").strip()
        platform = str(thread.get("platform") or "").strip()
        post_url = str(thread.get("post_url") or "")
        for index, comment in enumerate(thread.get("comments") or []):
            raw_text = str(comment.get("text") or "").strip()
            sanitized, truncated = sanitize_comment(raw_text)
            if not sanitized:
                continue
            locator = "\x1f".join(
                (
                    campaign,
                    post_url,
                    str(comment.get("comment_id") or index),
                )
            )
            campaigns[campaign].append(
                {
                    "text": sanitized,
                    "raw_sha256": text_sha256(raw_text),
                    "locator_sha256": text_sha256(locator),
                    "platform": platform,
                    "truncated": truncated,
                }
            )
    if set(campaigns) != {
        "Parameter Gelato",
        "KFC Bucket Ware",
        "MK Buffet",
        "วิ่งแลกแว่น | Top Charoen",
        "ไทยช่วยไทยพลัส",
    }:
        raise ValueError(f"Unexpected real-comment campaigns: {sorted(campaigns)}")
    if any(len(rows) < 160 for rows in campaigns.values()):
        raise ValueError("Each campaign needs at least 160 non-empty real comments")
    return campaigns


def select_synthetic_agent(record: dict) -> dict:
    candidates = [
        agent
        for agent in record.get("agents") or []
        if agent.get("schema_valid")
        and agent.get("action") != "silence"
        and str(agent.get("text") or "").strip()
    ]
    if not candidates:
        raise ValueError(f"No visible synthetic reaction in {record.get('job_key')}")
    index = stable_seed(str(record["job_key"]), "judge-visible-agent") % len(candidates)
    return candidates[index]


def has_visible_synthetic_reaction(record: dict) -> bool:
    return any(
        agent.get("schema_valid")
        and agent.get("action") != "silence"
        and str(agent.get("text") or "").strip()
        for agent in record.get("agents") or []
    )


def build_pairs(
    synthetic_path: Path,
    real_path: Path,
    scenarios_path: Path,
    *,
    limit_pairs: int | None = None,
) -> list[PairJob]:
    scenarios = {scenario.name: scenario for scenario in load_scenarios(scenarios_path)}
    synthetic = sorted(read_jsonl(synthetic_path), key=lambda row: str(row.get("job_key")))
    if len(synthetic) != 800 or any(row.get("status") != "ok" for row in synthetic):
        raise ValueError("Expected 800 successful Experiment 4--5 synthetic calls")
    by_campaign: dict[str, list[dict]] = defaultdict(list)
    for record in synthetic:
        if has_visible_synthetic_reaction(record):
            by_campaign[str(record["campaign"])].append(record)
    if sum(map(len, by_campaign.values())) != 741:
        raise ValueError("Expected 741 calls with at least one visible synthetic reaction")

    real = load_real_comments(real_path)
    selected_real: dict[str, list[dict]] = {}
    for campaign, rows in real.items():
        shuffled = list(rows)
        random.Random(stable_seed(campaign, "judge-real-sample-v1")).shuffle(shuffled)
        selected_real[campaign] = shuffled[: len(by_campaign[campaign])]

    pairs: list[PairJob] = []
    for campaign in sorted(by_campaign):
        for record, real_comment in zip(by_campaign[campaign], selected_real[campaign]):
            agent = select_synthetic_agent(record)
            synthetic_text, _ = sanitize_comment(agent["text"])
            pair_id = text_sha256(f"deedy-judge-v1\x1f{record['job_key']}")[:24]
            pairs.append(
                PairJob(
                    pair_id=pair_id,
                    synthetic_job_key=str(record["job_key"]),
                    experiment=str(record["experiment"]),
                    generator_model=str(record["model"]),
                    campaign=campaign,
                    seed=int(record["seed"]),
                    feed=str(record["feed"]),
                    network=str(record["network"]),
                    variant=str(record["variant"]),
                    real_platform=str(real_comment["platform"]),
                    real_text=str(real_comment["text"]),
                    real_comment_sha256=str(real_comment["raw_sha256"]),
                    real_locator_sha256=str(real_comment["locator_sha256"]),
                    synthetic_text=synthetic_text,
                    synthetic_text_sha256=text_sha256(str(agent["text"])),
                    synthetic_action=str(agent["action"]),
                    synthetic_agent_id=str(agent["agent_id"]),
                    scenario=scenarios[campaign],
                )
            )
    pairs.sort(key=lambda pair: pair.synthetic_job_key)
    return pairs[:limit_pairs] if limit_pairs else pairs


def build_prompt(job: JudgeJob) -> tuple[str, str]:
    schema = {
        "comment_a": {
            **{dimension: "integer 1-5" for dimension in DIMENSIONS},
            "sentiment": "negative|neutral|positive",
            "stance": "support|oppose|question|unclear|mixed",
        },
        "comment_b": {
            **{dimension: "integer 1-5" for dimension in DIMENSIONS},
            "sentiment": "negative|neutral|positive",
            "stance": "support|oppose|question|unclear|mixed",
        },
        "more_likely_real": "A|B|tie",
        "evidence_summary": "one short sentence describing observable cues without quoting either comment",
    }
    system = """You are an independent evaluator of Thai social-media campaign reactions.
Exactly one candidate is an authentic public comment and the other is simulated. Their order is randomized. Evaluate both independently before choosing which is more likely authentic; `tie` is allowed.
Scores are integers 1-5, where 5 is better, except `unsupported_claim_risk`, where 5 means higher risk. Judge only observable text and supplied campaign facts. Do not infer author identity or demographics. Do not reward length alone.
Do not quote either candidate, reproduce names/handles/contact details, or provide chain-of-thought. `evidence_summary` must name only concise observable cues such as colloquiality, specificity, relevance, repetition, or unsupported claims.
Return exactly one JSON object with the requested keys, English property names, and no markdown."""
    user = (
        f"Campaign: {job.pair.campaign}\n"
        f"Allowed scenario facts: {job.pair.scenario.baseline_message}\n"
        f"Scenario details: {json.dumps(job.pair.scenario.scenario_details, ensure_ascii=False, sort_keys=True)}\n\n"
        f"Comment A:\n{job.text_for(job.a_source)}\n\n"
        f"Comment B:\n{job.text_for(job.b_source)}\n\n"
        f"Required JSON shape:\n{json.dumps(schema, ensure_ascii=False)}"
    )
    return system, user


def parse_score_block(value: object) -> dict:
    if not isinstance(value, dict):
        raise ValueError("Comment score block is not an object")
    output: dict[str, object] = {}
    for dimension in DIMENSIONS:
        score = value.get(dimension)
        if isinstance(score, str) and score.strip().isdigit():
            score = int(score.strip())
        if not isinstance(score, int) or isinstance(score, bool) or not 1 <= score <= 5:
            raise ValueError(f"Invalid {dimension} score: {score}")
        output[dimension] = score
    raw_sentiment = str(value.get("sentiment") or "").strip().lower()
    sentiment = "neutral" if raw_sentiment == "mixed" else raw_sentiment
    stance = str(value.get("stance") or "").strip().lower()
    if sentiment not in SENTIMENTS:
        raise ValueError(f"Invalid sentiment: {sentiment}")
    if stance not in STANCES:
        raise ValueError(f"Invalid stance: {stance}")
    output["sentiment"] = sentiment
    output["sentiment_was_mixed"] = raw_sentiment == "mixed"
    output["stance"] = stance
    return output


def parse_judgment(content: str, job: JudgeJob) -> dict:
    payload = json.loads(strip_json_fence(content))
    if not isinstance(payload, dict):
        raise ValueError("Judge response is not an object")
    a = parse_score_block(payload.get("comment_a"))
    b = parse_score_block(payload.get("comment_b"))
    preference = str(payload.get("more_likely_real") or "").strip()
    normalized = {"a": "A", "b": "B", "equal": "tie", "same": "tie"}.get(
        preference.lower(), preference
    )
    if normalized not in PREFERENCES:
        raise ValueError(f"Invalid preference: {preference}")
    evidence, _ = sanitize_comment(payload.get("evidence_summary") or "", max_chars=320)
    if not evidence:
        raise ValueError("Missing evidence summary")
    source_scores = {
        job.a_source: a,
        job.b_source: b,
    }
    mapped_preference = (
        "tie"
        if normalized == "tie"
        else job.a_source
        if normalized == "A"
        else job.b_source
    )
    return {
        "scores": source_scores,
        "raw_preference": normalized,
        "mapped_preference": mapped_preference,
        "evidence_summary": evidence,
    }


def prompt_hash(system: str, user: str) -> str:
    return text_sha256(system + "\x1f" + user)


def call_job(
    job: JudgeJob,
    *,
    key: str,
    base_url: str,
    model: str,
    max_tokens: int,
    temperature: float,
    rate: dict[str, float],
    retries: int,
) -> dict:
    system, user = build_prompt(job)
    request_seed = stable_seed(job.key, "openrouter-judge") % 2_147_483_647
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
        "seed": request_seed,
        "response_format": {"type": "json_object"},
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
                    block.get("text", "") for block in content if isinstance(block, dict)
                )
            judgment = parse_judgment(str(content), job)
            usage = response.get("usage") or {}
            prompt_tokens = int(usage.get("prompt_tokens") or 0)
            completion_tokens = int(usage.get("completion_tokens") or 0)
            return {
                "call_key": job.key,
                "pair_id": job.pair.pair_id,
                "status": "ok",
                "orientation": job.orientation,
                "a_source": job.a_source,
                "b_source": job.b_source,
                "experiment": job.pair.experiment,
                "generator_model": job.pair.generator_model,
                "judge_model": model,
                "campaign": job.pair.campaign,
                "seed": job.pair.seed,
                "feed": job.pair.feed,
                "network": job.pair.network,
                "variant": job.pair.variant,
                "real_platform": job.pair.real_platform,
                "real_comment_sha256": job.pair.real_comment_sha256,
                "real_locator_sha256": job.pair.real_locator_sha256,
                "synthetic_text_sha256": job.pair.synthetic_text_sha256,
                "synthetic_action": job.pair.synthetic_action,
                "synthetic_agent_id": job.pair.synthetic_agent_id,
                "prompt_sha256": prompt_hash(system, user),
                "request_seed": int(payload["seed"]),
                "response_id": response.get("id"),
                "provider": response.get("provider"),
                "latency_seconds": time.monotonic() - started,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "cost_usd": prompt_tokens * rate["prompt"]
                + completion_tokens * rate["completion"],
                **judgment,
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
        "call_key": job.key,
        "pair_id": job.pair.pair_id,
        "status": "error",
        "orientation": job.orientation,
        "experiment": job.pair.experiment,
        "generator_model": job.pair.generator_model,
        "judge_model": model,
        "campaign": job.pair.campaign,
        "seed": job.pair.seed,
        "feed": job.pair.feed,
        "network": job.pair.network,
        "variant": job.pair.variant,
        "prompt_sha256": prompt_hash(system, user),
        "latency_seconds": time.monotonic() - started,
        "error": last_error,
    }


def record_complete(record: dict) -> bool:
    return (
        record.get("status") == "ok"
        and record.get("raw_preference") in PREFERENCES
        and record.get("mapped_preference") in ("real", "synthetic", "tie")
        and isinstance(record.get("scores"), dict)
        and set(record["scores"]) == {"real", "synthetic"}
        and all(
            all(isinstance(record["scores"][source].get(dimension), int) for dimension in DIMENSIONS)
            for source in ("real", "synthetic")
        )
    )


def append_record(path: Path, record: dict, lock: threading.Lock) -> None:
    line = json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n"
    with lock:
        with path.open("a", encoding="utf-8") as handle:
            handle.write(line)
            handle.flush()
            os.fsync(handle.fileno())


def load_resume(path: Path) -> dict[str, dict]:
    return {str(record["call_key"]): record for record in read_jsonl(path)} if path.exists() else {}


def mean(values: Sequence[float]) -> float:
    return statistics.fmean(values) if values else 0.0


def bootstrap_mean_ci(values: Sequence[float], seed_key: str, samples: int = 2000) -> tuple[float, float]:
    if not values:
        return (0.0, 0.0)
    rng = random.Random(stable_seed(seed_key, "bootstrap-v1"))
    n = len(values)
    means = [statistics.fmean(values[rng.randrange(n)] for _ in range(n)) for _ in range(samples)]
    return quantile(means, 0.025), quantile(means, 0.975)


def aggregate_pairs(jobs: Sequence[PairJob], records: dict[str, dict]) -> list[dict]:
    output: list[dict] = []
    for pair in jobs:
        calls = [records[f"{pair.pair_id}|orientation={orientation}"] for orientation in (0, 1)]
        mapped = [str(call["mapped_preference"]) for call in calls]
        row: dict[str, object] = {
            "pair_id": pair.pair_id,
            "experiment": pair.experiment,
            "generator_model": pair.generator_model,
            "campaign": pair.campaign,
            "seed": pair.seed,
            "feed": pair.feed,
            "network": pair.network,
            "variant": pair.variant,
            "real_platform": pair.real_platform,
            "real_comment_sha256": pair.real_comment_sha256,
            "real_locator_sha256": pair.real_locator_sha256,
            "synthetic_text_sha256": pair.synthetic_text_sha256,
            "synthetic_action": pair.synthetic_action,
            "preference_consistent": mapped[0] == mapped[1],
            "real_win_share": mapped.count("real") / 2,
            "synthetic_win_share": mapped.count("synthetic") / 2,
            "tie_share": mapped.count("tie") / 2,
            "simulated_realism_score": (mapped.count("synthetic") + 0.5 * mapped.count("tie")) / 2,
            "a_choice_count": sum(call["raw_preference"] == "A" for call in calls),
            "non_tie_count": sum(call["raw_preference"] != "tie" for call in calls),
            "judge_sentiment_agreement_real": calls[0]["scores"]["real"]["sentiment"]
            == calls[1]["scores"]["real"]["sentiment"],
            "judge_sentiment_agreement_synthetic": calls[0]["scores"]["synthetic"]["sentiment"]
            == calls[1]["scores"]["synthetic"]["sentiment"],
            "latency_seconds_mean": mean([float(call["latency_seconds"]) for call in calls]),
            "cost_usd": sum(float(call["cost_usd"]) for call in calls),
        }
        for source in ("real", "synthetic"):
            for dimension in DIMENSIONS:
                row[f"{source}_{dimension}"] = mean(
                    [float(call["scores"][source][dimension]) for call in calls]
                )
            for sentiment in SENTIMENTS:
                row[f"{source}_{sentiment}_weight"] = mean(
                    [call["scores"][source]["sentiment"] == sentiment for call in calls]
                )
        for dimension in DIMENSIONS:
            row[f"gap_{dimension}"] = float(row[f"synthetic_{dimension}"]) - float(
                row[f"real_{dimension}"]
            )
        output.append(row)
    return output


def summarize_group(rows: Sequence[dict], target: Sequence[float], key: str) -> dict:
    realism_values = [float(row["simulated_realism_score"]) for row in rows]
    realism_low, realism_high = bootstrap_mean_ci(realism_values, f"{key}|realism")
    output: dict[str, object] = {
        "pairs": len(rows),
        "judge_calls": 2 * len(rows),
        "real_win_share": mean([float(row["real_win_share"]) for row in rows]),
        "synthetic_win_share": mean([float(row["synthetic_win_share"]) for row in rows]),
        "tie_share": mean([float(row["tie_share"]) for row in rows]),
        "simulated_realism_score": mean([float(row["simulated_realism_score"]) for row in rows]),
        "simulated_realism_score_ci_low": realism_low,
        "simulated_realism_score_ci_high": realism_high,
        "preference_consistency": mean([float(row["preference_consistent"]) for row in rows]),
        "position_a_choice_share": sum(float(row["a_choice_count"]) for row in rows)
        / max(1, sum(float(row["non_tie_count"]) for row in rows)),
        "judge_sentiment_agreement_real": mean(
            [float(row["judge_sentiment_agreement_real"]) for row in rows]
        ),
        "judge_sentiment_agreement_synthetic": mean(
            [float(row["judge_sentiment_agreement_synthetic"]) for row in rows]
        ),
        "latency_seconds_mean": mean([float(row["latency_seconds_mean"]) for row in rows]),
        "cost_usd": sum(float(row["cost_usd"]) for row in rows),
    }
    for dimension in DIMENSIONS:
        real_values = [float(row[f"real_{dimension}"]) for row in rows]
        synthetic_values = [float(row[f"synthetic_{dimension}"]) for row in rows]
        gaps = [float(row[f"gap_{dimension}"]) for row in rows]
        low, high = bootstrap_mean_ci(gaps, f"{key}|{dimension}")
        output[f"real_{dimension}_mean"] = mean(real_values)
        output[f"synthetic_{dimension}_mean"] = mean(synthetic_values)
        output[f"gap_{dimension}_mean"] = mean(gaps)
        output[f"gap_{dimension}_ci_low"] = low
        output[f"gap_{dimension}_ci_high"] = high
    for source in ("real", "synthetic"):
        distribution = tuple(
            mean([float(row[f"{source}_{sentiment}_weight"]) for row in rows])
            for sentiment in SENTIMENTS
        )
        output[f"{source}_negative_share"] = distribution[0]
        output[f"{source}_neutral_share"] = distribution[1]
        output[f"{source}_positive_share"] = distribution[2]
        output[f"{source}_sentiment_jsd"] = js_distance(target, distribution)
    return output


def summarize(
    pairs: Sequence[dict],
    targets: dict[str, tuple[float, float, float]],
    fields: Sequence[str],
) -> list[dict]:
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for row in pairs:
        groups[tuple(row[field] for field in fields)].append(row)
    output: list[dict] = []
    for values in sorted(groups, key=lambda item: tuple(map(str, item))):
        selected = groups[values]
        target = tuple(
            mean([targets[str(row["campaign"])][i] for row in selected]) for i in range(3)
        )
        prefix = {field: value for field, value in zip(fields, values)}
        key = "|".join(map(str, values))
        prefix.update(summarize_group(selected, target, key))
        output.append(prefix)
    return output


def short_model(model: str) -> str:
    if model == "deepseek/deepseek-v4-flash-0731":
        return "DeepSeek V4 Flash 0731"
    if model == "qwen/qwen3-8b":
        return "Qwen3 8B"
    return model


def results_markdown(
    overall: Sequence[dict], pairs: Sequence[dict], calls: Sequence[dict], global_row: dict
) -> str:
    lines = [
        "# GLM-5.3-Flash LLM-as-a-judge: Experiments 4--5",
        "",
        "> One authentic same-campaign comment and one synthetic reaction were judged twice with reversed A/B order. The judge never received source identity, author data, URLs, aggregate sentiment targets, or campaign-level sentiment analyses.",
        "",
        "## Global diagnostic",
        "",
        f"- Pairs: {len(pairs)}; judge calls: {len(calls)}",
        f"- Real-preferred share: {global_row['real_win_share']:.4f}",
        f"- Synthetic-preferred share: {global_row['synthetic_win_share']:.4f}",
        f"- Tie share: {global_row['tie_share']:.4f}",
        f"- Simulated realism score (synthetic win + 0.5 tie): {global_row['simulated_realism_score']:.4f}",
        f"- Bootstrap 95% CI for simulated realism score: {global_row['simulated_realism_score_ci_low']:.4f} to {global_row['simulated_realism_score_ci_high']:.4f}",
        f"- Reversed-order preference consistency: {global_row['preference_consistency']:.4f}",
        f"- Raw A-choice share among non-ties: {global_row['position_a_choice_share']:.4f}",
        f"- Recorded cost: ${sum(float(call.get('cost_usd') or 0) for call in calls):.4f}",
        "",
        "## Global score comparison",
        "",
        "| Dimension | Real mean | Synthetic mean | Synthetic-minus-real gap | Bootstrap 95% CI |",
        "|---|---:|---:|---:|---:|",
    ]
    for dimension in DIMENSIONS:
        label = dimension.replace("_", " ").title()
        lines.append(
            f"| {label} | {global_row[f'real_{dimension}_mean']:.4f} | "
            f"{global_row[f'synthetic_{dimension}_mean']:.4f} | "
            f"{global_row[f'gap_{dimension}_mean']:.4f} | "
            f"[{global_row[f'gap_{dimension}_ci_low']:.4f}, {global_row[f'gap_{dimension}_ci_high']:.4f}] |"
        )
    lines.extend(
        [
            "",
            f"The judge-labeled real-comment sentiment distribution had JSD {global_row['real_sentiment_jsd']:.4f} from the supplied aggregate reference; the synthetic distribution had JSD {global_row['synthetic_sentiment_jsd']:.4f}.",
            "",
        "## Experiment-condition summary",
        "",
        "| Experiment | Generator | Feed | Network | Variant | Pairs | Real win | Synthetic win | Tie | Realism score | Thai gap | Plausibility gap | Unsupported-risk gap |",
        "|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in overall:
        lines.append(
            f"| {row['experiment']} | {short_model(str(row['generator_model']))} | {row['feed']} | {row['network']} | {row['variant']} | "
            f"{row['pairs']} | {row['real_win_share']:.4f} | {row['synthetic_win_share']:.4f} | {row['tie_share']:.4f} | "
            f"{row['simulated_realism_score']:.4f} | {row['gap_thai_naturalness_mean']:.4f} | "
            f"{row['gap_social_media_plausibility_mean']:.4f} | {row['gap_unsupported_claim_risk_mean']:.4f} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation boundary",
            "",
            "This is a single-model secondary diagnostic, not human ground truth. The rule-based ABM is excluded from text judging because it emits states rather than comments. Pairwise realism does not establish behavioral forecasting, message-treatment effects, or network/cascade fidelity. Native-Thai human ratings and judge-human agreement remain required.",
            "",
        ]
    )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--synthetic", type=Path, default=Path("/app/result/llm_exp45_calls.jsonl"))
    parser.add_argument("--real-comments", type=Path, default=Path("/data-prep/apify/data/social_comments_crawled.jsonl"))
    parser.add_argument("--analysis", type=Path, default=Path("/data-prep/apify/data/campaign_sentiment_analysis.jsonl"))
    parser.add_argument("--summary", type=Path, default=Path("/data-prep/apify/data/campaign_sentiment_summary.csv"))
    parser.add_argument("--scenarios", type=Path, default=Path("/app/experiments/exp45_scenarios.json"))
    parser.add_argument("--output", type=Path, default=Path("/app/result"))
    parser.add_argument("--model", default=JUDGE_MODEL)
    parser.add_argument("--max-tokens", type=int, default=2200)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--concurrency", type=int, default=20)
    parser.add_argument("--retries", type=int, default=8)
    parser.add_argument("--max-cost-usd", type=float, default=4.0)
    parser.add_argument("--limit-pairs", type=int)
    parser.add_argument("--smoke-test", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    load_env()
    pairs = build_pairs(
        args.synthetic,
        args.real_comments,
        args.scenarios,
        limit_pairs=2 if args.smoke_test else args.limit_pairs,
    )
    jobs = [JudgeJob(pair, orientation) for pair in pairs for orientation in (0, 1)]
    pricing = fetch_pricing("https://openrouter.ai/api/v1", [args.model])
    if not pricing.get(args.model) or not pricing[args.model].get("completion"):
        pricing[args.model] = FALLBACK_PRICING_PER_TOKEN[JUDGE_MODEL]
    estimated_cap = len(jobs) * (
        1800 * pricing[args.model]["prompt"]
        + args.max_tokens * pricing[args.model]["completion"]
    )
    print(
        f"GLM judge: {len(pairs)} pairs, {len(jobs)} reversed-order calls; "
        f"estimated cap ${estimated_cap:.2f}"
    )
    if estimated_cap > args.max_cost_usd:
        raise RuntimeError(
            f"Estimated cap ${estimated_cap:.2f} exceeds --max-cost-usd ${args.max_cost_usd:.2f}"
        )
    plan_rows = [
        {
            "pair_id": pair.pair_id,
            "synthetic_job_key": pair.synthetic_job_key,
            "experiment": pair.experiment,
            "generator_model": pair.generator_model,
            "campaign": pair.campaign,
            "seed": pair.seed,
            "feed": pair.feed,
            "network": pair.network,
            "variant": pair.variant,
            "real_platform": pair.real_platform,
            "real_comment_sha256": pair.real_comment_sha256,
            "real_locator_sha256": pair.real_locator_sha256,
            "synthetic_text_sha256": pair.synthetic_text_sha256,
            "synthetic_action": pair.synthetic_action,
        }
        for pair in pairs
    ]
    write_json(args.output / "llm_judge_exp45_plan.json", {
        "judge_model": args.model,
        "pairs": plan_rows,
        "calls": len(jobs),
        "excluded_all_silence_calls": 800 - len(pairs),
        "position_control": "Each pair is judged twice with reversed A/B order.",
        "privacy": "No author fields, URLs, IDs, or raw comment text are persisted in judge outputs.",
    })
    if args.dry_run:
        return 0

    key = api_key()
    if not is_real_key(key):
        raise RuntimeError("A real OPENROUTER_API_KEY is required")
    base_url = os.environ.get("OPENAI_BASE_URL", "https://openrouter.ai/api/v1")
    validate_key(base_url, key)
    calls_path = args.output / "llm_judge_exp45_calls.jsonl"
    records = load_resume(calls_path)
    pending = [job for job in jobs if not record_complete(records.get(job.key, {}))]
    print(f"resumed={len(jobs)-len(pending)} pending={len(pending)}")
    lock = threading.Lock()
    if pending:
        with ThreadPoolExecutor(max_workers=max(1, args.concurrency)) as executor:
            futures = {
                executor.submit(
                    call_job,
                    job,
                    key=key,
                    base_url=base_url,
                    model=args.model,
                    max_tokens=args.max_tokens,
                    temperature=args.temperature,
                    rate=pricing[args.model],
                    retries=args.retries,
                ): job
                for job in pending
            }
            completed = 0
            for future in as_completed(futures):
                record = future.result()
                records[record["call_key"]] = record
                append_record(calls_path, record, lock)
                completed += 1
                if completed % 50 == 0 or completed == len(pending):
                    ok = sum(record_complete(record) for record in records.values())
                    print(f"progress={completed}/{len(pending)} total_ok={ok}")

    ordered = [records[job.key] for job in jobs if job.key in records]
    write_jsonl(calls_path, ordered)
    failures = [record for record in ordered if not record_complete(record)]
    failures_path = args.output / "llm_judge_exp45_failures.json"
    if failures:
        write_json(failures_path, failures)
        raise RuntimeError(f"{len(failures)} judge calls failed; rerun to resume")
    failures_path.unlink(missing_ok=True)

    # Reference targets and campaign analyses are loaded only after judging ends.
    targets = load_targets(args.summary)
    analyses = list(read_jsonl(args.analysis))
    if {str(row.get("topic")) for row in analyses} != set(targets):
        raise ValueError("Campaign sentiment analysis and summary topics do not match")
    pair_rows = aggregate_pairs(pairs, records)
    weighted_target = tuple(
        mean([targets[str(row["campaign"])][i] for row in pair_rows]) for i in range(3)
    )
    global_summary = summarize_group(pair_rows, weighted_target, "global")
    overall = summarize(
        pair_rows,
        targets,
        ("experiment", "generator_model", "feed", "network", "variant"),
    )
    campaigns = summarize(
        pair_rows,
        targets,
        ("experiment", "generator_model", "campaign", "feed", "network", "variant"),
    )
    models = summarize(pair_rows, targets, ("experiment", "generator_model"))
    campaign_overall = summarize(pair_rows, targets, ("campaign",))
    write_jsonl(args.output / "llm_judge_exp45_pairs.jsonl", pair_rows)
    write_csv(args.output / "llm_judge_exp45_global_summary.csv", [global_summary])
    write_csv(args.output / "llm_judge_exp45_overall_summary.csv", overall)
    write_csv(args.output / "llm_judge_exp45_campaign_summary.csv", campaigns)
    write_csv(args.output / "llm_judge_exp45_model_summary.csv", models)
    write_csv(args.output / "llm_judge_exp45_campaign_overall.csv", campaign_overall)
    (args.output / "LLM_JUDGE_EXP45_RESULTS.md").write_text(
        results_markdown(overall, pair_rows, ordered, global_summary), encoding="utf-8"
    )
    artifacts = (
        "llm_judge_exp45_plan.json",
        "llm_judge_exp45_calls.jsonl",
        "llm_judge_exp45_pairs.jsonl",
        "llm_judge_exp45_global_summary.csv",
        "llm_judge_exp45_overall_summary.csv",
        "llm_judge_exp45_campaign_summary.csv",
        "llm_judge_exp45_model_summary.csv",
        "llm_judge_exp45_campaign_overall.csv",
        "LLM_JUDGE_EXP45_RESULTS.md",
    )
    manifest = {
        "schema_version": "1.0",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "runner": {
            "path": "experiments/run_llm_judge_exp45.py",
            "sha256": sha256_file(Path(__file__).resolve()),
        },
        "inputs": {
            "synthetic_calls": {"sha256": sha256_file(args.synthetic), "prompt_input": True},
            "real_comments": {
                "sha256": sha256_file(args.real_comments),
                "prompt_input": "sanitized text only",
            },
            "campaign_sentiment_analysis": {
                "sha256": sha256_file(args.analysis),
                "prompt_input": False,
                "use": "post-judging provenance cross-check only",
            },
            "campaign_sentiment_summary": {
                "sha256": sha256_file(args.summary),
                "prompt_input": False,
                "use": "post-judging aggregate sentiment correspondence",
            },
            "scenarios": {"sha256": sha256_file(args.scenarios), "prompt_input": True},
        },
        "openrouter": {"model": args.model, "key_validated": True},
        "parameters": {
            "pairs": len(pairs),
            "excluded_all_silence_calls": 800 - len(pairs),
            "orientations_per_pair": 2,
            "temperature": args.temperature,
            "max_tokens": args.max_tokens,
            "dimensions": list(DIMENSIONS),
            "mixed_sentiment_mapping": "Judge label `mixed` is mapped to `neutral` for the supplied three-class reference.",
        },
        "row_counts": {
            "judge_calls": len(ordered),
            "pairs": len(pair_rows),
            "overall_groups": len(overall),
            "campaign_groups": len(campaigns),
            "model_groups": len(models),
            "campaign_overall_groups": len(campaign_overall),
        },
        "actual_cost_usd": sum(float(record.get("cost_usd") or 0) for record in ordered),
        "privacy": [
            "Author objects, comment IDs, post URLs, and source identity are excluded from prompts.",
            "URLs, emails, handles, and phone-like strings are redacted from comment text before judging.",
            "Raw authentic and synthetic comment text is not persisted in judge result artifacts.",
        ],
        "interpretation_limits": [
            "GLM-5.3-Flash is a single secondary judge, not human ground truth.",
            "The rule-based ABM is not text-judged because it emits states rather than comments.",
            "Pairwise realism does not establish behavioral, causal, network, or cascade fidelity.",
            "Native-Thai human ratings and judge-human agreement remain pending.",
        ],
        "artifacts": {
            name: {"sha256": sha256_file(args.output / name)} for name in artifacts
        },
    }
    write_json(args.output / "llm_judge_exp45_manifest.json", manifest)
    print(
        f"Completed {len(ordered)} judge calls over {len(pair_rows)} pairs; "
        f"cost=${manifest['actual_cost_usd']:.4f}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
