---
name: dspy-evaluation-harness
description: Build DSPy evaluation harnesses with rich-feedback metrics that are essential for GEPA optimization. Use when writing a metric function, calling dspy.Evaluate, splitting dev/val sets, debugging "why is my optimizer not improving?", or designing CI-ready DSPy eval suites.
when_to_use: >-
  User mentions `dspy.Evaluate`, a "metric", a devset/valset/trainset,
  evaluation, scoring, or asks why their GEPA optimization isn't converging
  (almost always: their metric is too thin).
---

# DSPy Evaluation Harness (3.2.x)

The metric is usually more important than the program. For `dspy.GEPA` especially, the quality of **textual feedback** in your metric determines whether optimization converges.

## Two rules

1. **Return a `dspy.Prediction(score=..., feedback=...)`, not a dict.** `dspy.Evaluate`'s parallel executor aggregates scores via sum, which breaks on dict outputs (`TypeError: unsupported operand type(s) for +: 'int' and 'dict'`). `dspy.Prediction` supports `__float__`/`__add__` and is what GEPA's adapter natively unwraps. A bare float still works for pure `dspy.Evaluate` scoring, but GEPA needs the score+feedback pair.
2. **Separate valset.** Never optimize and evaluate on the same examples. Optimizers overfit fast.

## Canonical rich-feedback metric

```python
import dspy

def rich_metric(gold: dspy.Example, pred: dspy.Prediction, trace=None,
                pred_name: str | None = None, pred_trace=None):
    # 1. Compute sub-scores — multi-axis beats scalar
    correctness = 1.0 if _normalize(pred.answer) == _normalize(gold.answer) else 0.0
    cited = _has_citation(pred.answer, gold.sources) if hasattr(gold, "sources") else 1.0
    concise = 1.0 if len(pred.answer.split()) <= 50 else 0.5
    score = 0.6 * correctness + 0.25 * cited + 0.15 * concise

    # 2. Write feedback that teaches the optimizer
    parts = []
    if correctness < 1.0:
        parts.append(
            f"Answer mismatch. Predicted: {pred.answer!r}. Expected: {gold.answer!r}. "
            f"Likely cause: reasoning skipped the units/quantity in the question."
        )
    if cited < 1.0:
        parts.append("Did not ground the claim in the provided sources. Quote a source fragment.")
    if concise < 1.0:
        parts.append("Answer exceeded 50 words — tighten to one sentence.")
    if not parts:
        parts.append("Correct, grounded, and concise.")
    feedback = " ".join(parts)

    return dspy.Prediction(score=score, feedback=feedback)
```

## Canonical harness

```python
evaluator = dspy.Evaluate(
    devset=valset,
    metric=rich_metric,
    num_threads=8,
    display_progress=True,
    display_table=10,          # pretty-print first 10 rows
    provide_traceback=True,    # surface exceptions, don't swallow them
    max_errors=5,
    failure_score=0.0,
    save_as_json="eval_runs/baseline.json",
)
result = evaluator(program)
print("Overall:", result.score)
for example_result in result.results[:3]:
    print(example_result)
```

`dspy.Evaluate` returns an `EvaluationResult` with `.score` (aggregate float) and `.results` (list of `(example, pred, score)` tuples).

## Dataset hygiene

- **Size**: 20–50 examples is enough for GEPA's reflective loop; 100–500 for MIPROv2-style bootstrapping.
- **Split**: hand-curate two disjoint sets — `trainset` (for optimization) and `valset` (for metric-on-optimized-program). A test set you *never* look at during development is gold.
- **Representativeness** beats size. Include edge cases, ambiguity, adversarial inputs.
- Build `dspy.Example(...).with_inputs("question", "context")` — the `with_inputs` call marks which fields are inputs vs. gold outputs.

```python
trainset = [
    dspy.Example(question="…", answer="…").with_inputs("question"),
    ...
]
```

## Multi-axis metrics (recommended)

Combine correctness, faithfulness, format adherence, latency, and cost. Each axis should be a 0–1 float with a written definition. Weight them explicitly; don't hide weights inside magic numbers — make them constants so optimizers can be told to trade off.

## CI-ready eval suite

```python
# tests/test_dspy_eval.py
import dspy, pytest
from my_program import program, valset, rich_metric

@pytest.fixture(scope="module")
def evaluator():
    return dspy.Evaluate(devset=valset, metric=rich_metric, num_threads=8,
                         display_progress=False, provide_traceback=True)

def test_program_meets_threshold(evaluator):
    result = evaluator(program)
    assert result.score >= 0.75, f"Regression: {result.score:.3f}"
```

Run offline in CI with a cached LM (`dspy.LM(..., cache=True)`) + pre-populated `DSPY_CACHEDIR`.

## Tracing & observability

- `track_usage=True` on `dspy.configure` accumulates token counts on predictions (`pred.get_lm_usage()`).
- MLflow: `import mlflow; mlflow.dspy.autolog()` → traces every prediction.
- W&B: pass `use_wandb=True` to `dspy.GEPA` to log Pareto fronts.
- Always log eval results to a versioned JSON file (`save_as_json=...`) so you can diff runs.

## Anti-patterns

- Scalar-only metrics (float but no feedback) when using GEPA — wasted signal.
- **`return {"score": s, "feedback": f}` (dict)** — crashes `dspy.Evaluate`'s parallel aggregator. Use `dspy.Prediction(score=s, feedback=f)`.
- Exact-match metrics on open-ended generation tasks — use semantic or LM-as-judge scoring.
- Evaluating on the trainset — optimistic by 10–30 points.
- Silently swallowing exceptions (`provide_traceback=False`) — you'll blame the LM for a KeyError.
- Changing the metric mid-experiment without re-baselining — prior numbers become incomparable.

## Next

- Feed this metric into `dspy-gepa-optimizer`.
- Full harness pattern → [reference.md](reference.md).
- Runnable example → [example_metric.py](example_metric.py).
