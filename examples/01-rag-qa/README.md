# Example 01 — RAG Q&A with Citations

Retrieve, answer, cite. The prototypical DSPy use case. A **ChainOfThought** synthesizer reads BM25-retrieved passages and returns both a concise answer **and** the doc IDs that support it. GEPA optimizes the synthesizer's instruction to tighten correctness, citation grounding, and conciseness simultaneously.

## Committed results

| Metric | Baseline | Optimized | Δ |
|---|---:|---:|---:|
| Overall (weighted multi-axis) | 80.47 | **100.00** | **+19.53** |

- **Task LM**: `openrouter/mistralai/ministral-3b-2512`
- **Reflection LM**: `openrouter/qwen/qwen3-30b-a3b-instruct-2507`
- **GEPA mode**: `auto="light"`, seed=0
- **Trainset**: 15 · **valset**: 10
- **Runtime**: ~14 min
- **Artifact**: `optimized_program.json` (DSPy `3.2.0` metadata)
- **Comparison**: [`version_comparison.md`](version_comparison.md)

The 2026-04-28 refresh reran DSPy `3.1.3` and `3.2.0` from clean temporary state with the same paid model pair, seed, and GEPA mode. DSPy `3.2.0` reached a perfect optimized score; DSPy `3.1.3` improved on the same setup but plateaued at `91.75`.

## Task

Corpus: 12 short solar-system articles (`data/docs.jsonl`). Questions like *"What is the orbital period of Mars?"* / *"How many moons does Jupiter have?"* / *"Who discovered Io and in what year?"* — each with a single authoritative source doc.

```
BM25Retriever(k=3) → dspy.ChainOfThought("context, question -> answer, citations: list[str]")
```

## Metric (`pipeline.py:rich_metric`)

Weighted 3-axis metric returning `dspy.Prediction(score, feedback)`:

| Axis | Weight | Checks |
|---|---:|---|
| Correctness | 0.55 | Fuzzy answer match (substring or ≥ all-token overlap) |
| Citation validity | 0.30 | At least one cited doc ID is in the gold set; extras are penalized |
| Conciseness | 0.15 | 3–25 word answer; penalties for too-short or too-long |

Feedback text is specific per failure axis so GEPA's reflection LM can target the right fix.

## Run it

```bash
# From repo root:
cp .env.example .env    # then edit to add OPENROUTER_API_KEY

# Smoke test (no LM calls)
env -u UV_EXCLUDE_NEWER uv run --with dspy==3.2.0 --with python-dotenv --with rank-bm25 python examples/01-rag-qa/run.py --dry-run

# Exact committed baseline
env -u UV_EXCLUDE_NEWER \
  DSPY_TASK_MODEL=openrouter/mistralai/ministral-3b-2512 \
  DSPY_REFLECTION_MODEL=openrouter/qwen/qwen3-30b-a3b-instruct-2507 \
  DSPY_EXAMPLE_NUM_THREADS=1 \
  DSPY_EXAMPLE_NUM_RETRIES=8 \
  uv run --with dspy==3.2.0 --with python-dotenv --with rank-bm25 \
  python examples/01-rag-qa/run.py --baseline

# Exact committed GEPA run
rm -rf examples/01-rag-qa/gepa_logs
env -u UV_EXCLUDE_NEWER \
  DSPY_TASK_MODEL=openrouter/mistralai/ministral-3b-2512 \
  DSPY_REFLECTION_MODEL=openrouter/qwen/qwen3-30b-a3b-instruct-2507 \
  DSPY_EXAMPLE_NUM_THREADS=1 \
  DSPY_EXAMPLE_NUM_RETRIES=8 \
  uv run --with dspy==3.2.0 --with python-dotenv --with rank-bm25 \
  python examples/01-rag-qa/run.py --optimize --auto light --seed 0

# Score a saved program
env -u UV_EXCLUDE_NEWER \
  DSPY_TASK_MODEL=openrouter/mistralai/ministral-3b-2512 \
  uv run --with dspy==3.2.0 --with python-dotenv --with rank-bm25 \
  python examples/01-rag-qa/run.py --eval optimized_program.json
```

## Why Ministral 3B works here

`openrouter/mistralai/ministral-3b-2512` is still small enough to leave citation-formatting mistakes on the table, but much faster and easier to rerun cleanly than the older free-tier stack. GEPA still has something real to do here: the clean DSPy `3.2.0` baseline missed enough citation/format details to score `80.47`, and the optimized program recovered a perfect `100.00`.

## Reproducibility

`seed=0`, `auto="light"`, DSPy `3.2.0`, and the paid model pair above reproduce the refreshed comparison path. `run.py` now hardens both the task LM and reflection LM for retries, and GEPA checkpoints to `gepa_logs/gepa_state.bin`. Delete `gepa_logs/` and use a fresh `DSPY_CACHEDIR` before cross-version reruns if you want a clean compile instead of a resume or cache replay.
