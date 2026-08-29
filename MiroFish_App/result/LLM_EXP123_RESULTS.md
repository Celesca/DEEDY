# OpenRouter LLM pilot: Experiments 1--3

Models: `deepseek/deepseek-v4-flash-0731` and `qwen/qwen3-8b`. Each LLM row aggregates five campaigns and ten seeds (50 runs); each call requested 12 synthetic Thai reactions.

> Scope: sentiment is self-labeled by the generating model and compared with an all-comment aggregate target. There are no native-Thai human ratings or independent campaign holdouts, so these are pilot diagnostics rather than final validation.

## Experiment 1: grounding

| Condition | Model | Runs | Sentiment JSD | Thai ratio | Duplicate share | Schema valid | Mean cost/run |
|---|---|---:|---:|---:|---:|---:|---:|
| leaky_invalid_upper_bound | DeepSeek V4 Flash 0731 | 50 | 0.2031 | 0.9894 | 0.0000 | 0.9917 | $0.0001 |
| leaky_invalid_upper_bound | Qwen3 8B | 50 | 0.1966 | 0.9927 | 0.0000 | 1.0000 | $0.0005 |
| seed_only | DeepSeek V4 Flash 0731 | 50 | 0.2572 | 0.9822 | 0.0000 | 0.9833 | $0.0001 |
| seed_only | Qwen3 8B | 50 | 0.2859 | 0.9922 | 0.0000 | 1.0000 | $0.0005 |
| ungrounded | DeepSeek V4 Flash 0731 | 50 | 0.2635 | 0.9734 | 0.0000 | 0.9983 | $0.0001 |
| ungrounded | Qwen3 8B | 50 | 0.2388 | 0.9561 | 0.0017 | 1.0000 | $0.0005 |

## Experiment 2: Thai prompt adaptation

| Condition | Model | Runs | Sentiment JSD | Thai ratio | Duplicate share | Schema valid | Mean cost/run |
|---|---|---:|---:|---:|---:|---:|---:|
| normalization_no_context | DeepSeek V4 Flash 0731 | 50 | 0.2460 | 0.9797 | 0.0000 | 0.9967 | $0.0001 |
| normalization_no_context | Qwen3 8B | 50 | 0.2548 | 0.9736 | 0.0000 | 1.0000 | $0.0004 |
| thai_context_prompt | DeepSeek V4 Flash 0731 | 50 | 0.2572 | 0.9822 | 0.0000 | 0.9833 | $0.0001 |
| thai_context_prompt | Qwen3 8B | 50 | 0.2859 | 0.9922 | 0.0000 | 1.0000 | $0.0005 |
| translated_unadapted | DeepSeek V4 Flash 0731 | 50 | 0.2604 | 0.9978 | 0.0000 | 1.0000 | $0.0001 |
| translated_unadapted | Qwen3 8B | 50 | 0.2523 | 0.9611 | 0.0000 | 1.0000 | $0.0004 |

## Experiment 3: core model

| Condition | Model | Runs | Sentiment JSD | Thai ratio | Duplicate share | Schema valid | Mean cost/run |
|---|---|---:|---:|---:|---:|---:|---:|
| deepseek_v4_flash | DeepSeek V4 Flash 0731 | 50 | 0.2572 | 0.9822 | 0.0000 | 0.9833 | $0.0001 |
| non_generative_uniform_abm | none | 50 | 0.2779 | -- | -- | 1.0000 | $0.0000 |
| qwen3_8b | Qwen3 8B | 50 | 0.2859 | 0.9922 | 0.0000 | 1.0000 | $0.0005 |

## Execution summary

- Unique OpenRouter calls: 500
- Failed calls: 0
- Recorded model cost: $0.1386
- Matched DeepSeek/Qwen pairs in Exp. 3: 50

## Measured interpretation

In Experiment 3, DeepSeek minus Qwen sentiment JSD was -0.0287 with an empirical 2.5--97.5% interval of -0.3592 to 0.2179. Because the interval spans zero, this pilot does not establish a fidelity advantage for either model.

- DeepSeek V4 Flash 0731: 250 calls, 2983/3000 requested samples returned, mean latency 35.51 s, cost $0.0276.
- Qwen3 8B: 250 calls, 3000/3000 requested samples returned, mean latency 15.17 s, cost $0.1109.

The deliberately leaky Exp. 1 row is an invalid diagnostic bound and must never be reported as DEEDY performance. The non-generative ABM emits sentiment states only, so Thai-language and text-diversity cells are intentionally absent.
