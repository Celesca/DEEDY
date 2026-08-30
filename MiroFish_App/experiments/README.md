# Paper experiment pilot

This directory contains the reproducible, credential-free portion of the
experimental plan in `paper_plan/paper/28-8-2026.tex`.

Run the full pilot through Docker:

```sh
docker compose --profile experiments run --rm paper-experiments
```

The command writes aggregate-only artifacts to `result/`. It never copies raw
comment text, author names, or post URLs into the result bundle.

Scope is intentionally strict:

- Exp. 3 executes the simple non-generative ABM component only.
- Exp. 4 sweeps three feeds, two network assumptions, three population sizes,
  five campaigns, and ten seeds (900 runs).
- Exp. 5 runs a paired model-internal baseline/message-frame smoke test (100
  runs).
- Exp. 1, the LLM portions of Exp. 2--3, native-Thai rating, and analyst rating
  remain pending because the checkout contains neither independent scenario
  seeds, model credentials, nor human reference ratings.

The crawl has no reply-parent links. The runner therefore labels its clustered
graph `post_affiliation_proxy`; it must not be described as an observed reply
network.

## OpenRouter Experiments 1--3

Configure `OPENROUTER_API_KEY` in the project-root `.env`, then run:

```sh
docker compose --profile experiments run --rm llm-experiments
```

The primary model is pinned to `deepseek/deepseek-v4-flash-0731`; the
cost-efficient comparator is `qwen/qwen3-8b`. A dry run writes the exact call
plan and cost estimate without sending a model request:

```sh
docker compose --profile experiments run --rm llm-experiments --dry-run
```

Before the full matrix, one live request per model can be checked with:

```sh
docker compose --profile experiments run --rm llm-experiments --smoke-test
```

The live runner validates the key, enforces a USD cost cap, writes each
completed call immediately, and resumes only incomplete jobs after interruption.

## OpenRouter Experiments 4--5

The original Exp. 4--5 pilot is non-generative. To run the additional
leakage-guarded LLM cognitive-agent panel, use:

```sh
docker compose --profile experiments run --rm llm-experiments-45
```

From the repository root, the equivalent local command is:

```sh
python3 MiroFish_App/experiments/run_llm_exp45.py \
  --scenarios MiroFish_App/experiments/exp45_scenarios.json \
  --summary 1_data-prep/apify/data/campaign_sentiment_summary.csv \
  --output MiroFish_App/result
```

Both commands resume completed schema-valid calls from
`result/llm_exp45_calls.jsonl`, so an interrupted run does not start over.

The run covers all five campaigns, three feed policies, two network
assumptions, baseline/clarity message frames, ten seeds, and both configured
models. A dry run prints the exact matrix and worst-case cost estimate:

```sh
docker compose --profile experiments run --rm llm-experiments-45 --dry-run
```

A six-call live smoke test (Experiment 4 plus both Experiment 5 variants for
both models) is available:

```sh
docker compose --profile experiments run --rm llm-experiments-45 --smoke-test
```

The prompts read only `experiments/exp45_scenarios.json`. The real aggregate
sentiment ratios in `campaign_sentiment_summary.csv` are loaded only after all
model calls finish and are used solely for post-generation JSD scoring. Full
agent texts, actions, narratives, and short stated rationales are written to
`result/llm_exp45_calls.jsonl`.

## GLM-5.3-Flash judge for Experiments 4--5

After the generative Experiment 4--5 run is complete, run the blinded
same-campaign real-versus-simulated comparison with:

```sh
docker compose --profile experiments run --rm llm-judge-experiments-45
```

The local equivalent from the repository root is:

```sh
python3 MiroFish_App/experiments/run_llm_judge_exp45.py \
  --synthetic MiroFish_App/result/llm_exp45_calls.jsonl \
  --real-comments 1_data-prep/apify/data/social_comments_crawled.jsonl \
  --analysis 1_data-prep/apify/data/campaign_sentiment_analysis.jsonl \
  --summary 1_data-prep/apify/data/campaign_sentiment_summary.csv \
  --scenarios MiroFish_App/experiments/exp45_scenarios.json \
  --output MiroFish_App/result
```

The judge is `z-ai/glm-5.3-flash`. One visible synthetic reaction from every
Experiment 4--5 call is paired with one authentic same-campaign comment and
judged twice with reversed A/B order. Author objects, URLs, comment IDs, and
post IDs are excluded; URL, email, handle, and phone-like strings are redacted
before judging. Calls in which every agent chose silence have no comment to
compare and are excluded from text judging while remaining in action-rate
metrics. The sentiment analysis and aggregate summary are withheld from the
judge and loaded only after all calls complete. Use `--dry-run` to inspect the
741-pair/1,482-call plan or `--smoke-test` for two pairs/four calls.
