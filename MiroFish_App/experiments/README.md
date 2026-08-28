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
