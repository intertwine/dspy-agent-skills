# DSPy Evaluation Harness — API Reference

Source: https://dspy.ai/api/evaluation/Evaluate/ (DSPy 3.2.x).

## `dspy.Evaluate`

```python
dspy.Evaluate(
    devset: list[dspy.Example],
    metric: Callable | None = None,
    num_threads: int | None = None,
    display_progress: bool = False,
    display_table: bool | int = False,   # True = all rows; int = first N
    max_errors: int | None = None,       # None = use dspy.settings.max_errors
    provide_traceback: bool | None = None,
    failure_score: float = 0.0,
    save_as_csv: str | None = None,
    save_as_json: str | None = None,
)
```

Call the evaluator as `evaluator(program)`; it returns `EvaluationResult`:

```python
@dataclass
class EvaluationResult:
    score: float
    results: list[tuple[dspy.Example, dspy.Prediction, float | dict]]
```

## Metric signatures

A metric callable receives:

```python
metric(
    gold: dspy.Example,          # ground-truth example
    pred: dspy.Prediction,       # program output
    trace: DSPyTrace | None = None,     # set during .compile()
    pred_name: str | None = None,       # GEPA only — which predictor
    pred_trace: DSPyTrace | None = None, # GEPA only — that predictor's trace
) -> float | dspy.Prediction | str
```

Return values:

- `float` — treated as the score; works with `dspy.Evaluate` and most optimizers.
- **`dspy.Prediction(score=float, feedback=str)`** — GEPA-compatible; feedback is fed to the reflection LM. This is the recommended shape for any metric that will be used with an optimizer.
- `str` — rare; GEPA interprets as feedback with score derived separately.
- `bool` — treated as 0.0 / 1.0.

**Why not a dict?** A dict looks like it should work (it has `score` and `feedback` keys), but `dspy.Evaluate`'s parallel executor aggregates per-example outputs via `sum()`, which raises `TypeError: unsupported operand type(s) for +: 'int' and 'dict'`. `dspy.Prediction` defines `__float__`/`__add__` so it aggregates correctly.

GEPA's per-predictor feedback: when `pred_name` is non-None, return feedback targeted at *that* predictor's trace. This lets GEPA assign credit.

## LM-as-judge metric pattern

```python
class Judge(dspy.Signature):
    """Score the predicted answer 0.0–1.0 for factual correctness and cite the weakness."""
    question: str = dspy.InputField()
    gold_answer: str = dspy.InputField()
    pred_answer: str = dspy.InputField()
    score: float = dspy.OutputField()
    critique: str = dspy.OutputField()

judge = dspy.ChainOfThought(Judge)

def judge_metric(gold, pred, trace=None, **kwargs):
    j = judge(question=gold.question, gold_answer=gold.answer, pred_answer=pred.answer)
    return dspy.Prediction(score=float(j.score), feedback=j.critique)
```

Use a stronger LM for the judge than for the program under test (`dspy.context(lm=strong_lm): judge(...)`).

## Tracing integrations

- MLflow autolog: `import mlflow; mlflow.dspy.autolog()` — instruments every predictor and optimizer.
- W&B via GEPA: `dspy.GEPA(..., use_wandb=True, log_dir="./gepa_logs")`.
- OpenTelemetry: `dspy.settings.configure(callbacks=[OTelCallback()])`.

## Common failure modes

| Symptom | Likely cause |
|---|---|
| All scores 0.0 | Metric raised; set `provide_traceback=True`. |
| Optimization plateaus after 1-2 rounds | Metric feedback is generic/empty. Add specifics. |
| Eval takes forever | `num_threads=1`. Bump to 8–16 if the LM allows. |
| Scores non-deterministic between runs | Cache miss. Check `DSPY_CACHEDIR` and `dspy.LM(cache=True)`. |
| Baseline > optimized | Overfitting to trainset; use separate valset in `gepa.compile(..., valset=...)`. |
