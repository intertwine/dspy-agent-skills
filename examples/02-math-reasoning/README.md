# Example 02 — Multi-Step Math Reasoning

Grade-school word problems with compound percentages, work-rate, weighted averages, and distractors. A **ChainOfThought** solver must produce the correct final numeric answer and nothing else. GEPA tunes the instruction to unlock systematic reasoning — step enumeration, unit tracking, avoiding the classic traps encoded in the dataset.

## Committed results

| Metric | Baseline | Optimized | Δ |
|---|---:|---:|---:|
| Exact-match (numeric) | 85.00 | **93.33** | **+8.33** |

- **Task LM**: `openrouter/mistralai/ministral-3b-2512`
- **Reflection LM**: `openrouter/qwen/qwen3-30b-a3b-instruct-2507`
- **GEPA mode**: `auto="light"`, seed=0
- **Trainset**: 34 · **valset**: 12
- **Runtime**: ~3.5 min
- **Artifact**: `optimized_program.json` (DSPy `3.2.0` metadata)
- **Comparison**: [`version_comparison.md`](version_comparison.md)

The refreshed DSPy `3.2.0` artifact uses a stronger paid task model than the historical DSPy `3.1.3` free-tier run, so the absolute optimized score is much higher but the visible GEPA headroom is smaller. That tradeoff is documented directly in `version_comparison.md`.

## Task

```
dspy.ChainOfThought("problem -> answer (numeric only)")
```

34 train + 12 val problems (`data/train.jsonl`, `data/val.jsonl`). Each carries a `trap` hint — a one-line description of the typical mistake — which the metric weaves into its feedback so the reflection LM learns *structural* fixes rather than memorizing answers.

Example problem + trap:
```json
{
  "problem": "A $200 item is marked up 25%, then discounted 20% on the marked-up price. What is the final price in dollars?",
  "answer": 200,
  "trap": "200*1.25=250, 250*0.8=200. The sequence matters; do NOT add the percentages."
}
```

## Metric (`pipeline.py:rich_metric`)

Exact-match on the parsed numeric answer, with 0.2 partial credit for near-misses within 10% relative error. Returns `dspy.Prediction(score, feedback)` where the feedback includes the problem's trap hint when wrong. GEPA's reflection LM uses these hints to generalize — the instruction it lands teaches the solver to be explicit about operation order and re-check arithmetic.

## Run it

```bash
# Smoke test
env -u UV_EXCLUDE_NEWER uv run --with dspy==3.2.0 --with python-dotenv python examples/02-math-reasoning/run.py --dry-run

# Exact committed baseline
env -u UV_EXCLUDE_NEWER \
  DSPY_TASK_MODEL=openrouter/mistralai/ministral-3b-2512 \
  DSPY_REFLECTION_MODEL=openrouter/qwen/qwen3-30b-a3b-instruct-2507 \
  DSPY_EXAMPLE_NUM_THREADS=1 \
  DSPY_EXAMPLE_NUM_RETRIES=8 \
  uv run --with dspy==3.2.0 --with python-dotenv \
  python examples/02-math-reasoning/run.py --baseline

# Exact committed GEPA run
rm -rf examples/02-math-reasoning/gepa_logs
env -u UV_EXCLUDE_NEWER \
  DSPY_TASK_MODEL=openrouter/mistralai/ministral-3b-2512 \
  DSPY_REFLECTION_MODEL=openrouter/qwen/qwen3-30b-a3b-instruct-2507 \
  DSPY_EXAMPLE_NUM_THREADS=1 \
  DSPY_EXAMPLE_NUM_RETRIES=8 \
  uv run --with dspy==3.2.0 --with python-dotenv \
  python examples/02-math-reasoning/run.py --optimize --auto light --seed 0
```

## Why Ministral 3B is the current committed task LM

`openrouter/mistralai/ministral-3b-2512` was the fastest paid task model we tested that still left non-trivial headroom on the released dataset. The baseline jumped from the old `45.00` free-tier artifact to `85.00`, but GEPA still improved it to `93.33` by tightening the solver prompt around operation order, units, and trap avoidance.

If you want the old "weak model with huge lift" story, the historical DSPy `3.1.3` artifact in `version_comparison.md` still shows it clearly. The current committed artifact instead prioritizes a clean DSPy `3.2.0` rerun with a model that is still improvable but much less rate-limit-prone.

## Reproducibility

`seed=0`, `auto="light"`, DSPy `3.2.0`, and the paid model pair above reproduce the committed artifact. `run.py` now shares the same `num_threads` and retry hardening as the other examples through `examples/common/config.py`, and GEPA will resume from `gepa_logs/gepa_state.bin` unless you clear it first.
