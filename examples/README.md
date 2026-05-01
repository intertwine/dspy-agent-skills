# DSPy Agent Skills — Examples

Three runnable end-to-end examples that exercise the skills against real, reproducible tasks. The current committed artifacts mix refreshed DSPy `3.2.0` reruns with one retained historical DSPy `3.1.3` artifact where clean DSPy `3.2.0` probing left too little honest headroom for a replacement typed-output artifact.

## Current committed artifacts

| Example | Artifact DSPy | Task LM | Reflection LM | Baseline | Optimized | Δ | Status |
|---|---|---|---|---:|---:|---:|---|
| [01-rag-qa](01-rag-qa/) | 3.2.0 | `openrouter/mistralai/ministral-3b-2512` | `openrouter/qwen/qwen3-30b-a3b-instruct-2507` | 80.47 | **100.00** | **+19.53** | Clean comparison refreshed on 2026-04-28 |
| [02-math-reasoning](02-math-reasoning/) | 3.2.0 | `openrouter/mistralai/ministral-3b-2512` | `openrouter/qwen/qwen3-30b-a3b-instruct-2507` | 85.00 | **93.33** | **+8.33** | Refreshed on 2026-04-21 |
| [03-invoice-extraction](03-invoice-extraction/) | 3.1.3 | `openrouter/liquid/lfm-2.5-1.2b-instruct:free` | `openrouter/nvidia/nemotron-3-super-120b-a12b:free` | 0.833 | **0.931** | **+0.098** | Historical artifact retained |

The `01` and `02` reruns were done with DSPy `3.2.0`, `auto="light"`, `seed=0`, and a faster paid model pair that still left real GEPA headroom. `03` intentionally remains on its historical artifact: the clean DSPy `3.1.3` GEPA probe found a strong candidate but did not complete, and the clean DSPy `3.2.0` baseline on the same model pair already matched that best observed score.

## Version comparisons

- [01-rag-qa/version_comparison.md](01-rag-qa/version_comparison.md)
- [02-math-reasoning/version_comparison.md](02-math-reasoning/version_comparison.md)
- [03-invoice-extraction/version_comparison.md](03-invoice-extraction/version_comparison.md)

## What these exercise

| Example | Task | Skills exercised |
|---|---|---|
| 01-rag-qa | Answer factual questions over a 12-doc corpus with citations | `dspy-fundamentals` · `dspy-evaluation-harness` · `dspy-gepa-optimizer` |
| 02-math-reasoning | Multi-step word-problem arithmetic | `dspy-fundamentals` · `dspy-evaluation-harness` · `dspy-gepa-optimizer` |
| 03-invoice-extraction | Extract Pydantic-typed invoice records from unstructured text | `dspy-fundamentals` (typed outputs) · `dspy-evaluation-harness` · `dspy-gepa-optimizer` |

## Quickstart

```bash
cp .env.example .env         # fill in OPENROUTER_API_KEY
cd examples/01-rag-qa
env -u UV_EXCLUDE_NEWER uv run --with dspy==3.2.0 --with python-dotenv --with rank-bm25 python run.py --dry-run
env -u UV_EXCLUDE_NEWER uv run --with dspy==3.2.0 --with python-dotenv --with rank-bm25 python run.py --baseline
env -u UV_EXCLUDE_NEWER uv run --with dspy==3.2.0 --with python-dotenv --with rank-bm25 python run.py --optimize --auto light
```

Each `run.py` supports:
- `--baseline` — run and score the un-optimized program on the valset
- `--optimize [--auto light|medium|heavy]` — run GEPA, save the optimized program, re-score
- `--eval path/to/program.json` — score a saved program
- `--dry-run` — construct everything without calling an LM (offline smoke test)

## Model choice still matters

The refreshed DSPy `3.2.0` artifacts use a different task/reflection pair than the original DSPy `3.1.3` free-tier runs, so the comparisons are intentionally documented per example instead of pretending they are apples-to-apples. The current practical takeaways:

- `openrouter/mistralai/ministral-3b-2512` was the best "small but still improvable" paid task model for `01` and `02`: much faster than the older free-tier stack, but still weak enough to show GEPA movement.
- Invoice extraction is now hard to benchmark honestly with current paid small models. Modern 3B-8B models saturated the task, while the 1B fallback that left headroom produced too many malformed typed outputs to trust as a release artifact.
- The examples remain configurable. You can still override task/reflection models with env vars and rerun the exact same scripts.

**Override via env vars**:

```bash
export DSPY_TASK_MODEL=openrouter/arcee-ai/trinity-large-preview:free
export DSPY_TASK_MODEL=openrouter/openai/gpt-oss-120b:free

# Cheap paid fallbacks if free tier daily cap (2000 req/day) hits:
export DSPY_TASK_MODEL=openrouter/mistralai/ministral-8b-2512            # $0.15/M
export DSPY_TASK_MODEL=openrouter/mistralai/ministral-3b-2512            # $0.10/M
export DSPY_REFLECTION_MODEL=openrouter/qwen/qwen3-235b-a22b-thinking-2507
```

`run.py` now centralizes `num_threads` and retry hardening in `examples/common/config.py`, with `DSPY_EXAMPLE_NUM_THREADS` and `DSPY_EXAMPLE_NUM_RETRIES` overrides when you need to slow a run down.

## Reproducing the committed artifacts

Each example commits a `results.json` and `results.md` with the baseline and optimized scores from the author's run. For an exact DSPy `3.2.0` rerun of the refreshed artifacts:

```bash
cd examples/01-rag-qa
rm -rf gepa_logs
env -u UV_EXCLUDE_NEWER \
  DSPY_TASK_MODEL=openrouter/mistralai/ministral-3b-2512 \
  DSPY_REFLECTION_MODEL=openrouter/qwen/qwen3-30b-a3b-instruct-2507 \
  DSPY_EXAMPLE_NUM_THREADS=1 \
  DSPY_EXAMPLE_NUM_RETRIES=8 \
  uv run --with dspy==3.2.0 --with python-dotenv --with rank-bm25 \
  python run.py --optimize --auto light --seed 0

cd ../02-math-reasoning
rm -rf gepa_logs
env -u UV_EXCLUDE_NEWER \
  DSPY_TASK_MODEL=openrouter/mistralai/ministral-3b-2512 \
  DSPY_REFLECTION_MODEL=openrouter/qwen/qwen3-30b-a3b-instruct-2507 \
  DSPY_EXAMPLE_NUM_THREADS=1 \
  DSPY_EXAMPLE_NUM_RETRIES=8 \
  uv run --with dspy==3.2.0 --with python-dotenv \
  python run.py --optimize --auto light --seed 0

# Example 03 intentionally has no refreshed DSPy 3.2.0 artifact yet.
# See 03-invoice-extraction/version_comparison.md for the clean baseline/probe notes.
```

Clear `gepa_logs/` before cross-version reruns; otherwise GEPA will resume from the previous saved state instead of starting from a clean DSPy `3.2.0` run.

## Why these examples?

Each showcases a distinct DSPy strength that GEPA optimization amplifies:
- **RAG QA** — multi-axis metric (correctness + citation + conciseness) teaches GEPA how to trade off priorities.
- **Math reasoning** — exact-match is harsh; GEPA learns structural prompt improvements (step enumeration, units, sanity-checks) that unlock accuracy.
- **Structured extraction** — Pydantic-typed outputs + hallucination-aware metric forces the optimizer to tighten field grounding.
