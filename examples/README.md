# DSPy Agent Skills — Examples

Three runnable end-to-end examples that exercise the skills against real, reproducible tasks. Each runs on **free OpenRouter models**, burns **$0** to reproduce, and ships with committed baseline vs. GEPA-optimized numbers.

The committed metrics and saved `optimized_program.json` artifacts below were produced on DSPy `3.1.3`. The current branch keeps those live results as historical artifacts while smoke-testing the example codepaths and skill docs against DSPy `3.2.0`.

## Committed results

| Example | Task LM | Baseline | Optimized | Δ | Mutations accepted |
|---|---|---:|---:|---:|---:|
| [01-rag-qa](01-rag-qa/) | GLM 4.5 Air (32B) | 81.15 | **100.00** | **+18.85** | 1 |
| [02-math-reasoning](02-math-reasoning/) | Liquid LFM 2.5 (1.2B) | 45.00 | **70.00** | **+25.00** | 5 |
| [03-invoice-extraction](03-invoice-extraction/) | Liquid LFM 2.5 (1.2B) | 0.833 | **0.931** | **+0.098** | 5 |

All runs used `auto="light"`, `seed=0`, reflection LM `nvidia/nemotron-3-super-120b-a12b:free`. See each example's `README.md` for task description, metric details, and reproduction.

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
uv run --with dspy --with python-dotenv --with rank-bm25 python run.py --baseline
uv run --with dspy --with python-dotenv --with rank-bm25 python run.py --optimize --auto light
```

Each `run.py` supports:
- `--baseline` — run and score the un-optimized program on the valset
- `--optimize [--auto light|medium|heavy]` — run GEPA, save the optimized program, re-score
- `--eval path/to/program.json` — score a saved program
- `--dry-run` — construct everything without calling an LM (offline smoke test)

## Model choice matters

These examples were validated against multiple OpenRouter free models. The committed task-LM choice per example is deliberate:

| Role | Default | Why |
|---|---|---|
| Task LM (ex01) | `openrouter/z-ai/glm-4.5-air:free` | GLM 4.5 Air handles retrieval+synthesis well but flubs citation format — real GEPA headroom |
| Task LM (ex02, ex03) | `openrouter/liquid/lfm-2.5-1.2b-instruct:free` | Stronger models saturate these tasks (baseline > 0.95); 1.2B Liquid creates real failure-gradient for GEPA to improve on |
| Reflection LM (all) | `openrouter/nvidia/nemotron-3-super-120b-a12b:free` | 120B MoE — strong critic that can produce specific, actionable mutations |

**Override via env vars** — no code edits needed:

```bash
export DSPY_TASK_MODEL=openrouter/arcee-ai/trinity-large-preview:free
export DSPY_TASK_MODEL=openrouter/openai/gpt-oss-120b:free

# Cheap paid fallbacks if free tier daily cap (2000 req/day) hits:
export DSPY_TASK_MODEL=openrouter/mistralai/ministral-8b-2512            # $0.15/M
export DSPY_TASK_MODEL=openrouter/mistralai/ministral-3b-2512            # $0.10/M
export DSPY_REFLECTION_MODEL=openrouter/qwen/qwen3-235b-a22b-thinking-2507
```

**Rate-limit reality**: free tier is 20 req/min and 2000 req/day. GEPA with `auto="light"` generates 500–2000 LM calls. A single full run may hit the daily cap. `run.py` files set `num_threads=1` and `num_retries=12` to stay polite and survive transient 429s. If you hit the daily cap, either wait for reset or swap to a paid fallback.

## Reproducing the committed results

Each example commits a `results.json` and `results.md` with the baseline and optimized scores from the author's run. To reproduce:

```bash
# For example 01; adjust path/deps for 02 and 03.
cd examples/01-rag-qa
uv run --with dspy --with python-dotenv --with rank-bm25 python run.py --optimize --auto light --seed 0

# The run overwrites the same results.json/results.md in the example dir.
# Compare git-tracked baseline vs. your fresh run:
git diff results.json
```

Runs are single-seed (`seed=0`) by default; re-run with `--seed 1`, `--seed 2`, etc. for per-seed reproducibility. Multi-seed bootstrap intervals are not automated in `run.py` — if you want CI-style rigor, run the same command with multiple seeds and aggregate the JSON outputs yourself.

## Why these examples?

Each showcases a distinct DSPy strength that GEPA optimization amplifies:
- **RAG QA** — multi-axis metric (correctness + citation + conciseness) teaches GEPA how to trade off priorities.
- **Math reasoning** — exact-match is harsh; GEPA learns structural prompt improvements (step enumeration, units, sanity-checks) that unlock accuracy.
- **Structured extraction** — Pydantic-typed outputs + hallucination-aware metric forces the optimizer to tighten field grounding.
