# GLM-5.3-Flash LLM-as-a-judge: Experiments 4--5

> One authentic same-campaign comment and one synthetic reaction were judged twice with reversed A/B order. The judge never received source identity, author data, URLs, aggregate sentiment targets, or campaign-level sentiment analyses.

## Global diagnostic

- Pairs: 741; judge calls: 1482
- Real-preferred share: 0.5931
- Synthetic-preferred share: 0.4055
- Tie share: 0.0013
- Simulated realism score (synthetic win + 0.5 tie): 0.4062
- Bootstrap 95% CI for simulated realism score: 0.3742 to 0.4379
- Reversed-order preference consistency: 0.8354
- Raw A-choice share among non-ties: 0.5588
- Recorded cost: $0.5580

## Global score comparison

| Dimension | Real mean | Synthetic mean | Synthetic-minus-real gap | Bootstrap 95% CI |
|---|---:|---:|---:|---:|
| Thai Naturalness | 3.7686 | 4.1896 | 0.4211 | [0.2895, 0.5661] |
| Campaign Relevance | 2.8252 | 4.4629 | 1.6377 | [1.5115, 1.7672] |
| Social Media Plausibility | 3.8360 | 3.8806 | 0.0445 | [-0.1134, 0.1978] |
| Pragmatic Cultural Fit | 3.5695 | 4.0702 | 0.5007 | [0.3502, 0.6511] |
| Contextual Specificity | 2.2254 | 3.1363 | 0.9109 | [0.7638, 1.0479] |
| Unsupported Claim Risk | 1.8300 | 1.8704 | 0.0405 | [-0.0641, 0.1363] |

The judge-labeled real-comment sentiment distribution had JSD 0.0769 from the supplied aggregate reference; the synthetic distribution had JSD 0.2151.

## Experiment-condition summary

| Experiment | Generator | Feed | Network | Variant | Pairs | Real win | Synthetic win | Tie | Realism score | Thai gap | Plausibility gap | Unsupported-risk gap |
|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| exp4_social_mechanism | DeepSeek V4 Flash 0731 | chronological | matched_random | baseline | 50 | 0.6000 | 0.4000 | 0.0000 | 0.4000 | 0.4600 | 0.1600 | 0.0200 |
| exp4_social_mechanism | DeepSeek V4 Flash 0731 | chronological | post_affiliation_proxy | baseline | 50 | 0.6100 | 0.3900 | 0.0000 | 0.3900 | 0.5300 | 0.1300 | -0.1900 |
| exp4_social_mechanism | DeepSeek V4 Flash 0731 | interest | matched_random | baseline | 50 | 0.5500 | 0.4500 | 0.0000 | 0.4500 | 0.4900 | 0.0200 | -0.1300 |
| exp4_social_mechanism | DeepSeek V4 Flash 0731 | interest | post_affiliation_proxy | baseline | 50 | 0.4800 | 0.5200 | 0.0000 | 0.5200 | 0.6800 | 0.4600 | 0.2100 |
| exp4_social_mechanism | DeepSeek V4 Flash 0731 | popularity | matched_random | baseline | 50 | 0.5700 | 0.4300 | 0.0000 | 0.4300 | 0.4500 | 0.0400 | 0.3300 |
| exp4_social_mechanism | DeepSeek V4 Flash 0731 | popularity | post_affiliation_proxy | baseline | 50 | 0.5100 | 0.4900 | 0.0000 | 0.4900 | 0.5100 | 0.3400 | -0.1000 |
| exp4_social_mechanism | Qwen3 8B | chronological | matched_random | baseline | 43 | 0.6744 | 0.3256 | 0.0000 | 0.3256 | 0.2093 | -0.4767 | 0.3256 |
| exp4_social_mechanism | Qwen3 8B | chronological | post_affiliation_proxy | baseline | 45 | 0.6222 | 0.3778 | 0.0000 | 0.3778 | 0.3889 | -0.0111 | -0.0778 |
| exp4_social_mechanism | Qwen3 8B | interest | matched_random | baseline | 42 | 0.5833 | 0.4167 | 0.0000 | 0.4167 | 0.6786 | 0.0238 | 0.1548 |
| exp4_social_mechanism | Qwen3 8B | interest | post_affiliation_proxy | baseline | 41 | 0.5732 | 0.4268 | 0.0000 | 0.4268 | 0.7805 | 0.4390 | -0.2195 |
| exp4_social_mechanism | Qwen3 8B | popularity | matched_random | baseline | 44 | 0.6818 | 0.3068 | 0.0114 | 0.3125 | -0.0227 | -0.2955 | 0.0682 |
| exp4_social_mechanism | Qwen3 8B | popularity | post_affiliation_proxy | baseline | 45 | 0.7444 | 0.2556 | 0.0000 | 0.2556 | -0.2111 | -0.6667 | 0.1444 |
| exp5_application | DeepSeek V4 Flash 0731 | interest | post_affiliation_proxy | baseline | 50 | 0.5500 | 0.4500 | 0.0000 | 0.4500 | 0.8400 | 0.4500 | 0.5000 |
| exp5_application | DeepSeek V4 Flash 0731 | interest | post_affiliation_proxy | clarity_frame | 50 | 0.5300 | 0.4700 | 0.0000 | 0.4700 | 0.6000 | 0.3700 | 0.0900 |
| exp5_application | Qwen3 8B | interest | post_affiliation_proxy | baseline | 45 | 0.5667 | 0.4333 | 0.0000 | 0.4333 | 0.4889 | 0.2222 | -0.4667 |
| exp5_application | Qwen3 8B | interest | post_affiliation_proxy | clarity_frame | 36 | 0.7083 | 0.2778 | 0.0139 | 0.2847 | -0.4028 | -0.8472 | -0.0833 |

## Interpretation boundary

This is a single-model secondary diagnostic, not human ground truth. The rule-based ABM is excluded from text judging because it emits states rather than comments. Pairwise realism does not establish behavioral forecasting, message-treatment effects, or network/cascade fidelity. Native-Thai human ratings and judge-human agreement remain required.
