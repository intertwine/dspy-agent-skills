# Example 02 — Math Reasoning Results

| Metric | Baseline | Optimized | Δ |
|---|---:|---:|---:|
| Exact-match (numeric) | 85.000 | 93.330 | **+8.330** |

- Task LM: `openrouter/mistralai/ministral-3b-2512`
- Reflection LM: `openrouter/qwen/qwen3-30b-a3b-instruct-2507`
- GEPA mode: `auto="light"`, seed=0
- Trainset: 34 · valset: 12
- Times: baseline 21.9s, optimize 210.7s, optimized-eval 0.0s

Metric: exact match on final numeric answer (partial credit 0.2 for near-misses
within 10% relative error). Feedback includes per-problem `trap` hints so the
reflection LM can learn structural fixes rather than memorize answers.
See `pipeline.py:rich_metric`.
