#!/usr/bin/env python3
"""Run the credential-free DEEDY paper pilot.

This runner deliberately implements only the non-generative ABM and engineering
parts of the paper.  It does not silently replace the unavailable LLM, native
Thai rater, or held-out seed-packet experiments with synthetic scores.

The supplied crawl contains no reply-parent links.  Consequently, the planned
"observed network" condition is represented here by an explicitly named
post-affiliation proxy and compared with an edge-matched random graph.  That
comparison is a sensitivity analysis, not network correspondence validation.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import platform
import random
import statistics
import sys
import urllib.error
import urllib.request
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Sequence


SENTIMENT_SCORES = (-1, 0, 1)
FEEDS = ("chronological", "popularity", "interest")
NETWORKS = ("post_affiliation_proxy", "matched_random")
METRICS = (
    "action_rate",
    "reach_rate",
    "positive_share",
    "neutral_share",
    "negative_share",
    "js_distance_to_calibration_target",
    "sentiment_mean",
    "sentiment_shift",
    "normalized_entropy",
    "polarization_index",
    "cross_sentiment_edge_share",
    "largest_cascade_share",
    "cascade_depth",
    "cascade_breadth",
    "time_to_50pct",
)


@dataclass(frozen=True)
class CampaignProfile:
    name: str
    positive: float
    neutral: float
    negative: float
    total_comments: int
    post_counts: tuple[int, ...]
    unique_authors: int
    reply_links: int
    likes: tuple[int, ...]

    @property
    def target_distribution(self) -> tuple[float, float, float]:
        return (self.negative, self.neutral, self.positive)


@dataclass(frozen=True)
class SimulationConfig:
    campaign: str
    feed: str
    network: str
    population: int
    seed: int
    rounds: int = 12
    mean_degree: int = 6
    message_signal: float = 0.0
    scenario: str = "baseline"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def stable_seed(*parts: object) -> int:
    payload = "\x1f".join(str(part) for part in parts).encode("utf-8")
    return int.from_bytes(hashlib.sha256(payload).digest()[:8], "big")


def clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def sigmoid(value: float) -> float:
    if value >= 0:
        z = math.exp(-value)
        return 1.0 / (1.0 + z)
    z = math.exp(value)
    return z / (1.0 + z)


def quantile(values: Sequence[float], probability: float) -> float:
    if not values:
        return float("nan")
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    low = math.floor(position)
    high = math.ceil(position)
    if low == high:
        return float(ordered[low])
    fraction = position - low
    return float(ordered[low] * (1.0 - fraction) + ordered[high] * fraction)


def js_distance(left: Sequence[float], right: Sequence[float]) -> float:
    """Square-root Jensen--Shannon distance with base-2 logs (range 0--1)."""

    if len(left) != len(right) or not left:
        raise ValueError("Distributions must have the same non-zero length")
    left_total = sum(left)
    right_total = sum(right)
    if left_total <= 0 or right_total <= 0:
        raise ValueError("Distributions must have positive mass")
    p = [value / left_total for value in left]
    q = [value / right_total for value in right]
    midpoint = [(a + b) / 2.0 for a, b in zip(p, q)]

    def kl_divergence(source: Sequence[float], target: Sequence[float]) -> float:
        return sum(
            value * math.log2(value / target[index])
            for index, value in enumerate(source)
            if value > 0
        )

    return math.sqrt(
        0.5 * kl_divergence(p, midpoint) + 0.5 * kl_divergence(q, midpoint)
    )


def read_jsonl(path: Path) -> Iterable[dict]:
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(f"Invalid JSON on {path}:{line_number}: {error}") from error


def load_campaigns(summary_path: Path, threads_path: Path) -> list[CampaignProfile]:
    thread_stats: dict[str, dict] = defaultdict(
        lambda: {
            "post_counts": [],
            "authors": set(),
            "reply_links": 0,
            "likes": [],
            "comments": 0,
        }
    )
    for record in read_jsonl(threads_path):
        name = str(record.get("topic", "")).strip()
        if not name:
            continue
        comments = record.get("comments") or []
        stats = thread_stats[name]
        stats["post_counts"].append(len(comments))
        stats["comments"] += len(comments)
        for comment in comments:
            author = str(comment.get("author") or "").strip()
            if author:
                stats["authors"].add(author)
            if comment.get("parent_comment_id") not in (None, ""):
                stats["reply_links"] += 1
            try:
                likes = int(comment.get("likes_count") or 0)
            except (TypeError, ValueError):
                likes = 0
            stats["likes"].append(max(0, likes))

    campaigns: list[CampaignProfile] = []
    with summary_path.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            name = str(row["Topic"]).strip()
            stats = thread_stats.get(name)
            if not stats:
                raise ValueError(f"Campaign {name!r} is missing from {threads_path}")
            total = int(row["Total_Comments"])
            if total != stats["comments"]:
                raise ValueError(
                    f"Comment-count mismatch for {name}: summary={total}, "
                    f"threads={stats['comments']}"
                )
            profile = CampaignProfile(
                name=name,
                positive=float(row["Positive_Ratio"]),
                neutral=float(row["Neutral_Ratio"]),
                negative=float(row["Negative_Ratio"]),
                total_comments=total,
                post_counts=tuple(stats["post_counts"]),
                unique_authors=len(stats["authors"]),
                reply_links=int(stats["reply_links"]),
                likes=tuple(stats["likes"]),
            )
            if not math.isclose(sum(profile.target_distribution), 1.0, abs_tol=1e-6):
                raise ValueError(f"Sentiment ratios do not sum to one for {name}")
            campaigns.append(profile)
    if not campaigns:
        raise ValueError("No campaigns were loaded")
    return campaigns


def sample_population(
    profile: CampaignProfile, population: int, seed: int
) -> tuple[list[int], list[int], list[float]]:
    rng = random.Random(stable_seed(profile.name, population, seed, "population"))
    states = rng.choices(
        SENTIMENT_SCORES,
        weights=profile.target_distribution,
        k=population,
    )
    cluster_ids = rng.choices(
        range(len(profile.post_counts)),
        weights=profile.post_counts,
        k=population,
    )
    likes = profile.likes or (0,)
    raw_influence = [math.log1p(rng.choice(likes) + 1) for _ in range(population)]
    scale = max(1.0, quantile(raw_influence, 0.95))
    influence = [clamp(value / scale, 0.0, 1.5) for value in raw_influence]
    return states, cluster_ids, influence


def post_affiliation_graph(
    cluster_ids: Sequence[int], mean_degree: int
) -> tuple[list[set[int]], set[tuple[int, int]]]:
    adjacency = [set() for _ in cluster_ids]
    edges: set[tuple[int, int]] = set()
    clusters: dict[int, list[int]] = defaultdict(list)
    for node, cluster in enumerate(cluster_ids):
        clusters[cluster].append(node)
    half_degree = max(1, math.ceil(mean_degree / 2))
    for nodes in clusters.values():
        if len(nodes) < 2:
            continue
        for index, source in enumerate(nodes):
            for offset in range(1, min(half_degree, len(nodes) - 1) + 1):
                target = nodes[(index + offset) % len(nodes)]
                edge = (min(source, target), max(source, target))
                if edge[0] != edge[1]:
                    edges.add(edge)
    for source, target in edges:
        adjacency[source].add(target)
        adjacency[target].add(source)
    return adjacency, edges


def matched_random_graph(
    population: int, edge_count: int, rng: random.Random
) -> tuple[list[set[int]], set[tuple[int, int]]]:
    maximum = population * (population - 1) // 2
    target = min(maximum, edge_count)
    edges: set[tuple[int, int]] = set()
    while len(edges) < target:
        source = rng.randrange(population)
        target_node = rng.randrange(population - 1)
        if target_node >= source:
            target_node += 1
        edges.add((min(source, target_node), max(source, target_node)))
    adjacency = [set() for _ in range(population)]
    for source, target_node in edges:
        adjacency[source].add(target_node)
        adjacency[target_node].add(source)
    return adjacency, edges


def select_feed(
    candidate_nodes: Sequence[int],
    agent: int,
    feed: str,
    states: Sequence[int],
    baseline_states: Sequence[int],
    influence: Sequence[float],
    engagement_tick: dict[int, int],
    limit: int = 5,
) -> list[int]:
    if feed == "chronological":
        ordered = sorted(candidate_nodes, key=lambda node: (-engagement_tick[node], node))
    elif feed == "popularity":
        ordered = sorted(candidate_nodes, key=lambda node: (-influence[node], node))
    elif feed == "interest":
        ordered = sorted(
            candidate_nodes,
            key=lambda node: (
                abs(baseline_states[agent] - states[node]),
                -influence[node],
                node,
            ),
        )
    else:
        raise ValueError(f"Unknown feed: {feed}")
    return ordered[:limit]


def classify_score(value: float) -> int:
    if value > 0.30:
        return 1
    if value < -0.30:
        return -1
    return 0


def sentiment_distribution(states: Sequence[int]) -> tuple[float, float, float]:
    if not states:
        return (0.0, 1.0, 0.0)
    total = len(states)
    return tuple(states.count(score) / total for score in SENTIMENT_SCORES)


def cascade_metrics(
    engaged: set[int], parent: dict[int, int | None], engagement_tick: dict[int, int]
) -> tuple[float, int, int, int]:
    root_cache: dict[int, int] = {}
    depth_cache: dict[int, int] = {}

    def root_of(node: int) -> int:
        if node in root_cache:
            return root_cache[node]
        trail: list[int] = []
        current = node
        while parent.get(current) is not None:
            trail.append(current)
            current = int(parent[current])
        for item in trail:
            root_cache[item] = current
        root_cache[node] = current
        return current

    def depth_of(node: int) -> int:
        if node in depth_cache:
            return depth_cache[node]
        ancestor = parent.get(node)
        depth = 0 if ancestor is None else depth_of(int(ancestor)) + 1
        depth_cache[node] = depth
        return depth

    sizes: dict[int, int] = defaultdict(int)
    children: dict[int, int] = defaultdict(int)
    for node in engaged:
        sizes[root_of(node)] += 1
        if parent.get(node) is not None:
            children[int(parent[node])] += 1
    largest_share = max(sizes.values(), default=0) / max(1, len(engaged))
    max_depth = max((depth_of(node) for node in engaged), default=0)
    max_breadth = max(children.values(), default=0)
    final_count = len(engaged)
    halfway = math.ceil(final_count / 2)
    cumulative = 0
    time_to_half = 0
    tick_counts: dict[int, int] = defaultdict(int)
    for tick in engagement_tick.values():
        tick_counts[tick] += 1
    for tick in sorted(tick_counts):
        cumulative += tick_counts[tick]
        if cumulative >= halfway:
            time_to_half = tick
            break
    return largest_share, max_depth, max_breadth, time_to_half


def run_simulation(profile: CampaignProfile, config: SimulationConfig) -> dict:
    baseline_states, cluster_ids, influence = sample_population(
        profile, config.population, config.seed
    )
    states = list(baseline_states)
    proxy_adjacency, proxy_edges = post_affiliation_graph(
        cluster_ids, config.mean_degree
    )
    if config.network == "post_affiliation_proxy":
        adjacency, edges = proxy_adjacency, proxy_edges
    elif config.network == "matched_random":
        graph_rng = random.Random(
            stable_seed(profile.name, config.population, config.seed, "matched_random")
        )
        adjacency, edges = matched_random_graph(
            config.population, len(proxy_edges), graph_rng
        )
    else:
        raise ValueError(f"Unknown network: {config.network}")

    rng = random.Random(
        stable_seed(
            profile.name,
            config.population,
            config.seed,
            config.network,
            config.feed,
            config.scenario,
            "dynamics",
        )
    )
    root_count = max(2, math.ceil(config.population * 0.02))
    roots = sorted(range(config.population), key=lambda node: (-influence[node], node))[
        :root_count
    ]
    engaged: set[int] = set(roots)
    exposed: set[int] = set(roots)
    parent: dict[int, int | None] = {node: None for node in roots}
    engagement_tick: dict[int, int] = {node: 0 for node in roots}

    social_weight = {
        "chronological": 0.32,
        "popularity": 0.48,
        "interest": 0.40,
    }[config.feed]

    for tick in range(1, config.rounds + 1):
        new_actions: list[tuple[int, int, int]] = []
        for agent in range(config.population):
            if agent in engaged:
                continue
            candidates = [node for node in adjacency[agent] if node in engaged]
            if not candidates:
                continue
            exposed.add(agent)
            visible = select_feed(
                candidates,
                agent,
                config.feed,
                states,
                baseline_states,
                influence,
                engagement_tick,
            )
            feed_mean = statistics.fmean(states[node] for node in visible)
            mean_influence = statistics.fmean(influence[node] for node in visible)
            disagreement = abs(feed_mean - baseline_states[agent]) / 2.0
            logit = (
                -2.05
                + 0.40 * len(visible)
                + 0.32 * mean_influence
                + 0.24 * disagreement
                + 0.10 * abs(config.message_signal)
            )
            if rng.random() >= sigmoid(logit):
                continue
            score = (
                (0.78 - social_weight) * baseline_states[agent]
                + social_weight * feed_mean
                + 0.22 * config.message_signal
                + rng.gauss(0.0, 0.22)
            )
            new_state = classify_score(score)
            if config.feed == "popularity":
                parent_node = max(visible, key=lambda node: (influence[node], -node))
            elif config.feed == "interest":
                parent_node = min(
                    visible,
                    key=lambda node: (
                        abs(baseline_states[agent] - states[node]),
                        -influence[node],
                        node,
                    ),
                )
            else:
                parent_node = max(visible, key=lambda node: (engagement_tick[node], -node))
            new_actions.append((agent, new_state, parent_node))
        if not new_actions:
            break
        for agent, new_state, parent_node in new_actions:
            states[agent] = new_state
            engaged.add(agent)
            parent[agent] = parent_node
            engagement_tick[agent] = tick

    reaction_states = [states[node] for node in sorted(engaged)]
    negative, neutral, positive = sentiment_distribution(reaction_states)
    target_mean = profile.positive - profile.negative
    simulated_mean = positive - negative
    entropy = -sum(
        share * math.log(share)
        for share in (negative, neutral, positive)
        if share > 0
    ) / math.log(3)
    differing_edges = sum(1 for a, b in edges if states[a] != states[b])
    largest, depth, breadth, time_to_half = cascade_metrics(
        engaged, parent, engagement_tick
    )
    return {
        "experiment": "exp4_social_mechanism",
        "campaign": profile.name,
        "feed": config.feed,
        "network": config.network,
        "population": config.population,
        "seed": config.seed,
        "rounds": config.rounds,
        "mean_degree_requested": config.mean_degree,
        "scenario": config.scenario,
        "message_signal": config.message_signal,
        "edge_count": len(edges),
        "mean_degree_realized": 2.0 * len(edges) / config.population,
        "action_count": len(engaged),
        "action_rate": len(engaged) / config.population,
        "reach_rate": len(exposed) / config.population,
        "positive_share": positive,
        "neutral_share": neutral,
        "negative_share": negative,
        "js_distance_to_calibration_target": js_distance(
            profile.target_distribution, (negative, neutral, positive)
        ),
        "sentiment_mean": simulated_mean,
        "sentiment_shift": simulated_mean - target_mean,
        "normalized_entropy": entropy,
        "polarization_index": 4.0 * positive * negative,
        "cross_sentiment_edge_share": differing_edges / max(1, len(edges)),
        "largest_cascade_share": largest,
        "cascade_depth": depth,
        "cascade_breadth": breadth,
        "time_to_50pct": time_to_half,
    }


def summarize(rows: Sequence[dict], group_fields: Sequence[str]) -> list[dict]:
    grouped: dict[tuple, list[dict]] = defaultdict(list)
    for row in rows:
        grouped[tuple(row[field] for field in group_fields)].append(row)
    output: list[dict] = []
    for key in sorted(grouped, key=lambda item: tuple(str(value) for value in item)):
        group = grouped[key]
        summary = {field: value for field, value in zip(group_fields, key)}
        summary["runs"] = len(group)
        for metric in METRICS:
            values = [float(row[metric]) for row in group]
            summary[f"{metric}_mean"] = statistics.fmean(values)
            summary[f"{metric}_median"] = statistics.median(values)
            summary[f"{metric}_ci_low"] = quantile(values, 0.025)
            summary[f"{metric}_ci_high"] = quantile(values, 0.975)
        output.append(summary)
    return output


def paired_effects(rows: Sequence[dict]) -> list[dict]:
    pairs: dict[tuple[str, int], dict[str, dict]] = defaultdict(dict)
    for row in rows:
        pairs[(row["campaign"], row["seed"])][row["scenario"]] = row
    deltas: list[dict] = []
    for (campaign, seed), pair in sorted(pairs.items()):
        if "baseline" not in pair or "positive_clarity_frame" not in pair:
            continue
        item = {"campaign": campaign, "seed": seed}
        for metric in METRICS:
            item[f"{metric}_delta"] = (
                pair["positive_clarity_frame"][metric] - pair["baseline"][metric]
            )
        deltas.append(item)
    return deltas


def summarize_deltas(rows: Sequence[dict]) -> list[dict]:
    output: list[dict] = []
    campaigns = sorted({row["campaign"] for row in rows})
    for campaign in campaigns + ["ALL_CAMPAIGNS"]:
        selected = rows if campaign == "ALL_CAMPAIGNS" else [
            row for row in rows if row["campaign"] == campaign
        ]
        summary: dict[str, object] = {"campaign": campaign, "pairs": len(selected)}
        for metric in METRICS:
            values = [float(row[f"{metric}_delta"]) for row in selected]
            summary[f"{metric}_delta_mean"] = statistics.fmean(values)
            summary[f"{metric}_delta_median"] = statistics.median(values)
            summary[f"{metric}_delta_ci_low"] = quantile(values, 0.025)
            summary[f"{metric}_delta_ci_high"] = quantile(values, 0.975)
        output.append(summary)
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


def check_url(url: str | None) -> dict:
    if not url:
        return {"url": None, "status": "not_requested"}
    try:
        # Vite allows localhost by default but rejects an arbitrary Compose
        # service name in the Host header. The request still travels over the
        # isolated Compose network; only the virtual-host value is normalized.
        request = urllib.request.Request(url, headers={"Host": "localhost"})
        with urllib.request.urlopen(request, timeout=10) as response:
            body = response.read(500).decode("utf-8", errors="replace")
            return {
                "url": url,
                "status": "ok",
                "http_status": response.status,
                "body_prefix": body,
            }
    except (urllib.error.URLError, TimeoutError) as error:
        return {"url": url, "status": "failed", "error": str(error)}


def format_number(value: float) -> str:
    return f"{value:.3f}"


def build_results_markdown(
    campaigns: Sequence[CampaignProfile],
    exp4_overall: Sequence[dict],
    exp5_overall: Sequence[dict],
    effects: Sequence[dict],
    smoke: dict,
) -> str:
    lines = [
        "# DEEDY/MiroFish automated pilot results",
        "",
        "Generated from the supplied five-campaign crawl with ten deterministic seeds per condition. ",
        "This is an engineering and non-generative ABM pilot, not the paper's completed LLM/human evaluation.",
        "",
        "## Experimental coverage",
        "",
        "| Paper experiment | Pilot status |",
        "|---|---|",
        "| Exp. 1 grounding | Not run: independent seed packets and an LLM endpoint were unavailable. |",
        "| Exp. 2 Thai adaptation | Not run: model conditions and native-Thai reference ratings were unavailable. |",
        "| Exp. 3 core model | Non-generative ABM component only; no LLM comparison. |",
        "| Exp. 4 social mechanism | Automated sensitivity sweep completed. The missing reply graph was replaced by an explicitly labeled post-affiliation proxy. |",
        "| Exp. 5 application | Automated baseline/counterfactual and traceability artifacts completed; analyst usefulness was not rated. |",
        "",
        "## Dataset audit",
        "",
        "| Campaign | Comments | Posts | Unique authors | Reply links |",
        "|---|---:|---:|---:|---:|",
    ]
    for campaign in campaigns:
        lines.append(
            f"| {campaign.name} | {campaign.total_comments} | {len(campaign.post_counts)} | "
            f"{campaign.unique_authors} | {campaign.reply_links} |"
        )
    lines.extend(
        [
            "",
            "All 5,000 comments have null parent identifiers. Therefore cascade and network metrics below describe the simulated proxy graph only and cannot be interpreted as correspondence to observed reply cascades.",
            "",
            "## Exp. 4 social-mechanism sensitivity",
            "",
            "Values are means over five campaigns and ten seeds (50 runs per row). `JSD` is drift from the all-comment calibration distribution, not held-out accuracy.",
            "",
            "| Feed | Network | N | Action rate | Reach | JSD | Polarization | Largest cascade |",
            "|---|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in exp4_overall:
        lines.append(
            f"| {row['feed']} | {row['network']} | {row['population']} | "
            f"{format_number(row['action_rate_mean'])} | "
            f"{format_number(row['reach_rate_mean'])} | "
            f"{format_number(row['js_distance_to_calibration_target_mean'])} | "
            f"{format_number(row['polarization_index_mean'])} | "
            f"{format_number(row['largest_cascade_share_mean'])} |"
        )
    lines.extend(
        [
            "",
            "## Exp. 5 conditional message-frame smoke test",
            "",
            "The positive-clarity frame is a model-internal engineering counterfactual (`message_signal=0.8`), not a real-world causal estimate.",
            "",
            "| Scenario | Runs | Positive share | Sentiment mean | Action rate | JSD |",
            "|---|---:|---:|---:|---:|---:|",
        ]
    )
    for row in exp5_overall:
        lines.append(
            f"| {row['scenario']} | {row['runs']} | "
            f"{format_number(row['positive_share_mean'])} | "
            f"{format_number(row['sentiment_mean_mean'])} | "
            f"{format_number(row['action_rate_mean'])} | "
            f"{format_number(row['js_distance_to_calibration_target_mean'])} |"
        )
    all_effects = next(row for row in effects if row["campaign"] == "ALL_CAMPAIGNS")
    lines.extend(
        [
            "",
            f"Across {all_effects['pairs']} paired campaign-seed runs, the frame changed positive share by "
            f"{format_number(all_effects['positive_share_delta_mean'])} on average "
            f"(empirical 95% interval {format_number(all_effects['positive_share_delta_ci_low'])} to "
            f"{format_number(all_effects['positive_share_delta_ci_high'])}).",
            "",
            "## Docker smoke test",
            "",
            f"- API: `{smoke['api']['status']}` ({smoke['api'].get('http_status', 'n/a')})",
            f"- Frontend: `{smoke['frontend']['status']}` ({smoke['frontend'].get('http_status', 'n/a')})",
            "",
            "## Interpretation boundary",
            "",
            "These outputs verify deterministic execution, provenance, parameter sensitivity, and report generation. They do not establish Thai linguistic quality, held-out campaign correspondence, observed cascade fidelity, analyst usefulness, or a benefit from an LLM tier. Those claims remain pending the inputs listed in the manifest.",
            "",
        ]
    )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary", required=True, type=Path)
    parser.add_argument("--threads", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--seeds", type=int, default=10)
    parser.add_argument("--rounds", type=int, default=12)
    parser.add_argument("--populations", type=int, nargs="+", default=[200, 500, 1000])
    parser.add_argument("--mean-degree", type=int, default=6)
    parser.add_argument("--api-health-url")
    parser.add_argument("--frontend-url")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.seeds < 1 or args.rounds < 1 or args.mean_degree < 1:
        raise ValueError("seeds, rounds, and mean-degree must all be positive")
    if any(population < 10 for population in args.populations):
        raise ValueError("Each population must contain at least 10 agents")
    args.output.mkdir(parents=True, exist_ok=True)
    campaigns = load_campaigns(args.summary, args.threads)
    seeds = list(range(1, args.seeds + 1))

    exp4_runs: list[dict] = []
    for campaign in campaigns:
        for feed in FEEDS:
            for network in NETWORKS:
                for population in args.populations:
                    for seed in seeds:
                        config = SimulationConfig(
                            campaign=campaign.name,
                            feed=feed,
                            network=network,
                            population=population,
                            seed=seed,
                            rounds=args.rounds,
                            mean_degree=args.mean_degree,
                        )
                        exp4_runs.append(run_simulation(campaign, config))

    exp5_runs: list[dict] = []
    counterfactual_population = 500 if 500 in args.populations else args.populations[0]
    for campaign in campaigns:
        for scenario, signal in (("baseline", 0.0), ("positive_clarity_frame", 0.8)):
            for seed in seeds:
                config = SimulationConfig(
                    campaign=campaign.name,
                    feed="interest",
                    network="post_affiliation_proxy",
                    population=counterfactual_population,
                    seed=seed,
                    rounds=args.rounds,
                    mean_degree=args.mean_degree,
                    message_signal=signal,
                    scenario=scenario,
                )
                row = run_simulation(campaign, config)
                row["experiment"] = "exp5_application_counterfactual_smoke"
                exp5_runs.append(row)

    exp4_campaign = summarize(
        exp4_runs, ("campaign", "feed", "network", "population")
    )
    exp4_overall = summarize(exp4_runs, ("feed", "network", "population"))
    exp5_campaign = summarize(exp5_runs, ("campaign", "scenario"))
    exp5_overall = summarize(exp5_runs, ("scenario",))
    delta_rows = paired_effects(exp5_runs)
    effect_summary = summarize_deltas(delta_rows)

    audit = [
        {
            "campaign": profile.name,
            "comments": profile.total_comments,
            "posts": len(profile.post_counts),
            "unique_authors": profile.unique_authors,
            "reply_links": profile.reply_links,
            "positive_ratio": profile.positive,
            "neutral_ratio": profile.neutral,
            "negative_ratio": profile.negative,
        }
        for profile in campaigns
    ]
    smoke = {
        "api": check_url(args.api_health_url),
        "frontend": check_url(args.frontend_url),
    }

    write_csv(args.output / "dataset_audit.csv", audit)
    write_jsonl(args.output / "exp4_runs.jsonl", exp4_runs)
    write_csv(args.output / "exp4_campaign_summary.csv", exp4_campaign)
    write_csv(args.output / "exp4_overall_summary.csv", exp4_overall)
    write_jsonl(args.output / "exp5_runs.jsonl", exp5_runs)
    write_csv(args.output / "exp5_campaign_summary.csv", exp5_campaign)
    write_csv(args.output / "exp5_overall_summary.csv", exp5_overall)
    write_csv(args.output / "exp5_paired_deltas.csv", delta_rows)
    write_csv(args.output / "exp5_effect_summary.csv", effect_summary)
    write_json(args.output / "docker_smoke.json", smoke)
    results_markdown = build_results_markdown(
        campaigns, exp4_overall, exp5_overall, effect_summary, smoke
    )
    (args.output / "RESULTS.md").write_text(results_markdown, encoding="utf-8")

    artifact_names = [
        "dataset_audit.csv",
        "exp4_runs.jsonl",
        "exp4_campaign_summary.csv",
        "exp4_overall_summary.csv",
        "exp5_runs.jsonl",
        "exp5_campaign_summary.csv",
        "exp5_overall_summary.csv",
        "exp5_paired_deltas.csv",
        "exp5_effect_summary.csv",
        "docker_smoke.json",
        "RESULTS.md",
    ]
    manifest = {
        "schema_version": "1.0",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "runner": {
            "path": "experiments/run_paper_pilot.py",
            "sha256": sha256_file(Path(__file__).resolve()),
        },
        "python": sys.version,
        "platform": platform.platform(),
        "inputs": {
            "campaign_summary": {
                "path": str(args.summary),
                "sha256": sha256_file(args.summary),
            },
            "social_threads": {
                "path": str(args.threads),
                "sha256": sha256_file(args.threads),
            },
        },
        "parameters": {
            "seeds": seeds,
            "rounds": args.rounds,
            "populations": args.populations,
            "feeds": list(FEEDS),
            "networks": list(NETWORKS),
            "mean_degree": args.mean_degree,
            "counterfactual": {
                "population": counterfactual_population,
                "feed": "interest",
                "network": "post_affiliation_proxy",
                "positive_clarity_frame_signal": 0.8,
            },
        },
        "coverage": {
            "exp1_grounding": "not_run_missing_independent_seed_packets_and_llm_credentials",
            "exp2_thai_adaptation": "not_run_missing_model_conditions_and_native_thai_ratings",
            "exp3_core_model": "non_generative_abm_component_only",
            "exp4_social_mechanism": "completed_as_proxy_sensitivity_sweep",
            "exp5_application": "automated_counterfactual_and_traceability_smoke_only",
        },
        "data_findings": {
            "campaigns": len(campaigns),
            "comments": sum(profile.total_comments for profile in campaigns),
            "reply_links": sum(profile.reply_links for profile in campaigns),
            "network_substitution": "post_affiliation_proxy_for_unavailable_observed_reply_graph",
        },
        "interpretation_limits": [
            "The calibration sentiment distribution comes from all collected comments; JSD measures simulation drift, not held-out accuracy.",
            "The source export contains no parent reply links, so no observed cascade or reply-network correspondence is reported.",
            "No LLM calls, Thai human ratings, or analyst study were performed.",
            "The message-frame comparison is conditional inside this ABM and is not a causal estimate for Thai consumers.",
            "No comment text, author identifiers, or post URLs are written to result artifacts.",
        ],
        "row_counts": {
            "exp4_runs": len(exp4_runs),
            "exp5_runs": len(exp5_runs),
            "exp5_pairs": len(delta_rows),
        },
        "smoke_test": smoke,
        "artifacts": {
            name: {"sha256": sha256_file(args.output / name)}
            for name in artifact_names
        },
    }
    write_json(args.output / "manifest.json", manifest)
    print(
        f"Completed {len(exp4_runs)} Exp. 4 runs and {len(exp5_runs)} Exp. 5 runs; "
        f"artifacts: {args.output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
