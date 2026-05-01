# Example 01 — RAG QA Results

| Metric | Baseline | Optimized | Δ |
|---|---:|---:|---:|
| Overall | 80.470 | 100.000 | **+19.530** |

- Task LM: `openrouter/mistralai/ministral-3b-2512`
- Reflection LM: `openrouter/qwen/qwen3-30b-a3b-instruct-2507`
- GEPA mode: `auto="light"`, seed=0
- Trainset: 15 · valset: 10
- Times: baseline 12.6s, optimize 829.4s, optimized-eval 0.0s

Metric axes: correctness (0.55) + citation validity (0.30) + conciseness (0.15).
See `pipeline.py:rich_metric` for the exact scoring.
