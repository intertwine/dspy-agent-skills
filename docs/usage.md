# Usage Guide

## The five skills at a glance

| Skill | Invoke when | Depends on |
|---|---|---|
| `dspy-fundamentals` | Any new DSPy code | — |
| `dspy-evaluation-harness` | Writing metrics, splitting devset/valset, debugging eval | `dspy-fundamentals` |
| `dspy-gepa-optimizer` | Optimizing/compiling a DSPy program | `dspy-evaluation-harness` |
| `dspy-rlm-module` | Context >100k tokens, codebase/doc exploration | `dspy-fundamentals` |
| `dspy-advanced-workflow` | Full greenfield DSPy build | all others |

Claude Code / Codex auto-select skills by matching the `description` field. You don't need to invoke them manually in most cases.

## Typical conversation shapes

### Greenfield pipeline

> "Build a DSPy sentiment-classification pipeline on this CSV, optimize it, and save the artifact."

The agent pulls `dspy-advanced-workflow`, which chains the other four skills in order: fundamentals (Signature/Module) → evaluation-harness (metric + Evaluate) → gepa-optimizer (compile) → fundamentals (save).

### Debugging an optimizer

> "My GEPA run plateaus after round 2 — why?"

The agent loads `dspy-gepa-optimizer` and `dspy-evaluation-harness` and walks through the top failure modes: thin metric feedback, weak reflection_lm, train=val overlap, insufficient budget.

### Long-document QA

> "Summarize every error class in this 3M-token log."

The agent loads `dspy-rlm-module` and builds an RLM-backed pipeline with a cheap sub-LM.

### Explicit invocation

You can also force a skill:

- **Claude Code**: `/dspy-gepa-optimizer` (if `user-invocable` is true, which it is by default).
- **Codex**: `$dspy-gepa-optimizer`.

## Minimal happy-path code sample

```python
import dspy

dspy.configure(lm=dspy.LM("openai/gpt-4o"), track_usage=True)

class QA(dspy.Signature):
    """Answer concisely."""
    question: str = dspy.InputField()
    answer: str = dspy.OutputField()

program = dspy.ChainOfThought(QA)

def rich_metric(gold, pred, trace=None, pred_name=None, pred_trace=None):
    correct = pred.answer.strip().lower() == gold.answer.strip().lower()
    return dspy.Prediction(
        score=1.0 if correct else 0.0,
        feedback="Correct." if correct else f"Expected {gold.answer!r}, got {pred.answer!r}.",
    )

trainset = [dspy.Example(question="2+2?", answer="4").with_inputs("question"), ...]
valset   = [dspy.Example(question="5*6?", answer="30").with_inputs("question"), ...]

evaluator = dspy.Evaluate(devset=valset, metric=rich_metric, num_threads=4,
                          provide_traceback=True)
print("Baseline:", evaluator(program).score)

optimizer = dspy.GEPA(
    metric=rich_metric, auto="medium",
    reflection_lm=dspy.LM("openai/gpt-4o", temperature=1.0, max_tokens=8000),
    track_stats=True, log_dir="./gepa_logs",
)
optimized = optimizer.compile(student=program, trainset=trainset, valset=valset)
print("Optimized:", evaluator(optimized).score)

optimized.save("program.json", save_program=False)
```

On DSPy 3.2.x, module calls now warn by default when you pass extra input fields or values that don't match the signature's declared types. Treat those warnings as a callsite bug first; only disable them with `dspy.configure(warn_on_type_mismatch=False)` when you intentionally pass pre-serialized values.

## Running the bundled example scripts

Each skill folder contains a runnable `example_*.py` with a `--dry-run` flag that verifies construction without calling an LM:

```bash
cd skills/dspy-fundamentals
uv run python example_qa.py --dry-run

cd ../dspy-evaluation-harness
uv run python example_metric.py --dry-run

cd ../dspy-gepa-optimizer
uv run python example_gepa.py --dry-run
uv run python example_bettertogether.py --dry-run

cd ../dspy-rlm-module
uv run python example_rlm.py --dry-run

cd ../dspy-advanced-workflow
uv run python example_pipeline.py --dry-run
```

Live runs require `OPENAI_API_KEY` (or equivalent for the chosen `--model`).

## Getting help

- DSPy docs: https://dspy.ai/
- Skill sources: `skills/<name>/reference.md` in this repo
- Issues: https://github.com/intertwine/dspy-agent-skills/issues
