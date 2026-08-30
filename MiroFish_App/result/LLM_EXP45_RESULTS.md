# OpenRouter LLM pilot: Experiments 4--5

> The LLM saw frozen scenario facts and experimental mechanism conditions only. Authentic comments, sentiment ratios, and real-data summaries were withheld until scoring. Stated rationales are short observable explanations, not private chain-of-thought.

## Ground-truth scoring targets (scoring only)

| Campaign | Negative | Neutral | Positive |
|---|---:|---:|---:|
| Parameter Gelato | 0.362 | 0.476 | 0.162 |
| KFC Bucket Ware | 0.049 | 0.309 | 0.642 |
| MK Buffet | 0.136 | 0.444 | 0.420 |
| วิ่งแลกแว่น \| Top Charoen | 0.050 | 0.700 | 0.250 |
| ไทยช่วยไทยพลัส | 0.175 | 0.275 | 0.550 |

## Experiment 4: LLM cognitive-agent mechanism diagnostic

This prompt-level panel varies feed and network assumptions. It measures generated reaction/action differences and aggregate sentiment correspondence; it does not create a validated reply cascade.

| Model | Feed | Network | Runs | JSD | Visible action | Positive | Neutral | Negative |
|---|---|---|---:|---:|---:|---:|---:|---:|
| DeepSeek V4 Flash 0731 | chronological | matched_random | 50 | 0.2995 | 0.7825 | 0.4100 | 0.5700 | 0.0200 |
| DeepSeek V4 Flash 0731 | chronological | post_affiliation_proxy | 50 | 0.3211 | 0.7800 | 0.3875 | 0.6050 | 0.0075 |
| DeepSeek V4 Flash 0731 | interest | matched_random | 50 | 0.3159 | 0.7675 | 0.3975 | 0.5800 | 0.0225 |
| DeepSeek V4 Flash 0731 | interest | post_affiliation_proxy | 50 | 0.3154 | 0.7750 | 0.3925 | 0.5925 | 0.0150 |
| DeepSeek V4 Flash 0731 | popularity | matched_random | 50 | 0.3051 | 0.7825 | 0.4100 | 0.5825 | 0.0075 |
| DeepSeek V4 Flash 0731 | popularity | post_affiliation_proxy | 50 | 0.3233 | 0.7600 | 0.3825 | 0.6100 | 0.0075 |
| Qwen3 8B | chronological | matched_random | 50 | 0.3291 | 0.7450 | 0.3575 | 0.6400 | 0.0025 |
| Qwen3 8B | chronological | post_affiliation_proxy | 50 | 0.3277 | 0.7450 | 0.3450 | 0.6500 | 0.0050 |
| Qwen3 8B | interest | matched_random | 50 | 0.3389 | 0.7400 | 0.3375 | 0.6625 | 0.0000 |
| Qwen3 8B | interest | post_affiliation_proxy | 50 | 0.3432 | 0.7400 | 0.3250 | 0.6725 | 0.0025 |
| Qwen3 8B | popularity | matched_random | 50 | 0.3274 | 0.7475 | 0.3575 | 0.6425 | 0.0000 |
| Qwen3 8B | popularity | post_affiliation_proxy | 50 | 0.3431 | 0.7525 | 0.3450 | 0.6550 | 0.0000 |

## Experiment 5: baseline versus clarity frame

| Model | Variant | Runs | JSD | Visible action | Positive | Neutral | Negative |
|---|---|---:|---:|---:|---:|---:|---:|
| DeepSeek V4 Flash 0731 | baseline | 50 | 0.3189 | 0.7775 | 0.4175 | 0.5725 | 0.0100 |
| DeepSeek V4 Flash 0731 | clarity_frame | 50 | 0.3114 | 0.8200 | 0.4050 | 0.5700 | 0.0250 |
| Qwen3 8B | baseline | 50 | 0.3335 | 0.7450 | 0.3475 | 0.6525 | 0.0000 |
| Qwen3 8B | clarity_frame | 50 | 0.3349 | 0.7500 | 0.3300 | 0.6650 | 0.0050 |

### Campaign-level Experiment 5 correspondence

| Model | Campaign | Variant | JSD |
|---|---|---|---:|
| DeepSeek V4 Flash 0731 | KFC Bucket Ware | baseline | 0.2771 |
| DeepSeek V4 Flash 0731 | KFC Bucket Ware | clarity_frame | 0.2696 |
| DeepSeek V4 Flash 0731 | MK Buffet | baseline | 0.2779 |
| DeepSeek V4 Flash 0731 | MK Buffet | clarity_frame | 0.2467 |
| DeepSeek V4 Flash 0731 | Parameter Gelato | baseline | 0.4840 |
| DeepSeek V4 Flash 0731 | Parameter Gelato | clarity_frame | 0.4872 |
| DeepSeek V4 Flash 0731 | วิ่งแลกแว่น \| Top Charoen | baseline | 0.2154 |
| DeepSeek V4 Flash 0731 | วิ่งแลกแว่น \| Top Charoen | clarity_frame | 0.2150 |
| DeepSeek V4 Flash 0731 | ไทยช่วยไทยพลัส | baseline | 0.3401 |
| DeepSeek V4 Flash 0731 | ไทยช่วยไทยพลัส | clarity_frame | 0.3388 |
| Qwen3 8B | KFC Bucket Ware | baseline | 0.3053 |
| Qwen3 8B | KFC Bucket Ware | clarity_frame | 0.3053 |
| Qwen3 8B | MK Buffet | baseline | 0.2918 |
| Qwen3 8B | MK Buffet | clarity_frame | 0.3009 |
| Qwen3 8B | Parameter Gelato | baseline | 0.4722 |
| Qwen3 8B | Parameter Gelato | clarity_frame | 0.4722 |
| Qwen3 8B | วิ่งแลกแว่น \| Top Charoen | baseline | 0.1744 |
| Qwen3 8B | วิ่งแลกแว่น \| Top Charoen | clarity_frame | 0.1924 |
| Qwen3 8B | ไทยช่วยไทยพลัส | baseline | 0.4236 |
| Qwen3 8B | ไทยช่วยไทยพลัส | clarity_frame | 0.4038 |

### Paired clarity-frame effect

Across 100 matched model/campaign/seed pairs, clarity minus baseline JSD was -0.0030 (empirical 95% interval -0.1888 to 0.1261). Negative values mean the clarity frame moved generated sentiment closer to the real aggregate target.

## Execution summary

- Calls: 800
- Failed calls: 0
- Recorded cost: $0.3586
- Full generated texts, actions, narratives, and rationale summaries are stored in `llm_exp45_calls.jsonl`.

## Interpretation boundary

These results test prompt-conditioned cognitive-agent reactions. They do not establish observed network or cascade fidelity, and the all-comment aggregate target is not an independent campaign holdout. A lower JSD is therefore diagnostic correspondence, not proof of forecasting accuracy.
