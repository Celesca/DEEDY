# DEEDY/MiroFish automated pilot results

Generated from the supplied five-campaign crawl with ten seeds per condition.
Experiments 1--3 use OpenRouter LLM calls; Experiments 4--5 use the
non-generative ABM. This remains a pilot rather than the paper's completed
held-out and human-rated evaluation.

## Experimental coverage

| Paper experiment | Pilot status |
|---|---|
| Exp. 1 grounding | OpenRouter seed-only, ungrounded, and deliberately leaky diagnostic conditions completed for two models. Independent held-out seed packets remain unavailable. |
| Exp. 2 Thai adaptation | Three prompt-level conditions completed for two models. Native-Thai human ratings remain unavailable. |
| Exp. 3 core model | DeepSeek V4 Flash 0731, Qwen3 8B, and a uniform non-generative ABM baseline completed. |
| Exp. 4 social mechanism | Automated sensitivity sweep completed. The missing reply graph was replaced by an explicitly labeled post-affiliation proxy. |
| Exp. 5 application | Automated baseline/counterfactual and traceability artifacts completed; analyst usefulness was not rated. |

## Dataset audit

| Campaign | Comments | Posts | Unique authors | Reply links |
|---|---:|---:|---:|---:|
| Parameter Gelato | 1000 | 5 | 981 | 0 |
| KFC Bucket Ware | 1000 | 12 | 964 | 0 |
| MK Buffet | 1000 | 7 | 946 | 0 |
| วิ่งแลกแว่น | Top Charoen | 1000 | 2 | 973 | 0 |
| ไทยช่วยไทยพลัส | 1000 | 7 | 947 | 0 |

All 5,000 comments have null parent identifiers. Therefore cascade and network metrics below describe the simulated proxy graph only and cannot be interpreted as correspondence to observed reply cascades.

## Exp. 1--3 OpenRouter LLM pilot

The run used `deepseek/deepseek-v4-flash-0731` and `qwen/qwen3-8b`.
It completed 500 unique calls (five campaigns, five prompt conditions, ten
seeds, and two models), requesting 12 synthetic Thai reactions per call. The
same seed-only calls were reused across Experiments 1--3, producing 750 expanded
metric rows without purchasing duplicate requests. There were no failed calls.

Sentiment is self-labeled by the generating model and compared with the
all-comment aggregate distribution, so JSD here is a diagnostic rather than
held-out accuracy. Lower JSD is better.

| Experiment | Condition | DeepSeek JSD | Qwen JSD |
|---|---|---:|---:|
| Exp. 1 | seed only | 0.2572 | 0.2859 |
| Exp. 1 | ungrounded | 0.2635 | 0.2388 |
| Exp. 1 | leaky invalid upper bound | 0.2031 | 0.1966 |
| Exp. 2 | Thai-context prompt | 0.2572 | 0.2859 |
| Exp. 2 | translated/unadapted | 0.2604 | 0.2523 |
| Exp. 2 | normalization without context | 0.2460 | 0.2548 |
| Exp. 3 | configured LLM | 0.2572 | 0.2859 |

For Experiment 1, seed-only minus ungrounded JSD was -0.0063 for DeepSeek
(empirical 95% interval -0.1483 to 0.1756) and 0.0471 for Qwen (-0.3313 to
0.3484). In Experiment 3, DeepSeek minus Qwen JSD was -0.0287 (-0.3592 to
0.2179). All three intervals span zero; this pilot therefore establishes no
grounding or model-fidelity advantage. The leaky row is lower on average but is
invalid by design because it receives target aggregates.

DeepSeek returned 2,983/3,000 requested reactions, averaged 35.51 seconds per
call, and cost $0.0276. Qwen returned 3,000/3,000, averaged 15.17 seconds, and
cost $0.1109. Total recorded cost was $0.1386. The Thai-character ratio was
high in the shared seed-only condition (0.9822 DeepSeek; 0.9922 Qwen), but this
character-level proxy cannot replace blinded native-Thai judgments. Detailed
condition tables, campaign summaries, run records, and paired effects are in
`LLM_EXP123_RESULTS.md` and the `llm_exp123_*` artifacts.

## Exp. 4 social-mechanism sensitivity

Values are means over five campaigns and ten seeds (50 runs per row). `JSD` is drift from the all-comment calibration distribution, not held-out accuracy.

| Feed | Network | N | Action rate | Reach | JSD | Polarization | Largest cascade |
|---|---|---:|---:|---:|---:|---:|---:|
| chronological | matched_random | 1000 | 0.966 | 0.997 | 0.070 | 0.172 | 0.153 |
| chronological | matched_random | 200 | 0.965 | 0.997 | 0.086 | 0.165 | 0.479 |
| chronological | matched_random | 500 | 0.968 | 0.997 | 0.077 | 0.172 | 0.251 |
| chronological | post_affiliation_proxy | 1000 | 0.419 | 0.484 | 0.069 | 0.179 | 0.081 |
| chronological | post_affiliation_proxy | 200 | 0.405 | 0.462 | 0.102 | 0.172 | 0.355 |
| chronological | post_affiliation_proxy | 500 | 0.402 | 0.463 | 0.082 | 0.169 | 0.159 |
| interest | matched_random | 1000 | 0.968 | 0.996 | 0.096 | 0.137 | 0.140 |
| interest | matched_random | 200 | 0.966 | 0.997 | 0.110 | 0.144 | 0.446 |
| interest | matched_random | 500 | 0.970 | 0.997 | 0.102 | 0.138 | 0.224 |
| interest | post_affiliation_proxy | 1000 | 0.416 | 0.480 | 0.092 | 0.146 | 0.082 |
| interest | post_affiliation_proxy | 200 | 0.408 | 0.463 | 0.131 | 0.152 | 0.356 |
| interest | post_affiliation_proxy | 500 | 0.400 | 0.463 | 0.097 | 0.163 | 0.161 |
| popularity | matched_random | 1000 | 0.968 | 0.996 | 0.118 | 0.124 | 0.141 |
| popularity | matched_random | 200 | 0.965 | 0.997 | 0.145 | 0.110 | 0.439 |
| popularity | matched_random | 500 | 0.968 | 0.997 | 0.120 | 0.126 | 0.239 |
| popularity | post_affiliation_proxy | 1000 | 0.416 | 0.480 | 0.102 | 0.157 | 0.081 |
| popularity | post_affiliation_proxy | 200 | 0.402 | 0.459 | 0.159 | 0.149 | 0.344 |
| popularity | post_affiliation_proxy | 500 | 0.400 | 0.461 | 0.115 | 0.164 | 0.159 |

## Exp. 5 conditional message-frame smoke test

The positive-clarity frame is a model-internal engineering counterfactual (`message_signal=0.8`), not a real-world causal estimate.

| Scenario | Runs | Positive share | Sentiment mean | Action rate | JSD |
|---|---:|---:|---:|---:|---:|
| baseline | 50 | 0.443 | 0.306 | 0.400 | 0.097 |
| positive_clarity_frame | 50 | 0.667 | 0.615 | 0.417 | 0.266 |

Across 50 paired campaign-seed runs, the frame changed positive share by 0.225 on average (empirical 95% interval 0.106 to 0.364).

## Docker smoke test

- API: `ok` (200)
- Frontend: `ok` (200)

## Interpretation boundary

These outputs verify reproducible execution, provenance, parameter sensitivity,
LLM routing, structured Thai generation, and report generation. They do not
establish Thai linguistic quality, held-out campaign correspondence, observed
cascade fidelity, analyst usefulness, or a benefit from an LLM tier. Those
claims remain pending the inputs listed in the manifests.
