# DEEDY/MiroFish automated pilot results

Generated from the supplied five-campaign crawl with ten deterministic seeds per condition. 
This is an engineering and non-generative ABM pilot, not the paper's completed LLM/human evaluation.

## Experimental coverage

| Paper experiment | Pilot status |
|---|---|
| Exp. 1 grounding | Not run: independent seed packets and an LLM endpoint were unavailable. |
| Exp. 2 Thai adaptation | Not run: model conditions and native-Thai reference ratings were unavailable. |
| Exp. 3 core model | Non-generative ABM component only; no LLM comparison. |
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

These outputs verify deterministic execution, provenance, parameter sensitivity, and report generation. They do not establish Thai linguistic quality, held-out campaign correspondence, observed cascade fidelity, analyst usefulness, or a benefit from an LLM tier. Those claims remain pending the inputs listed in the manifest.
