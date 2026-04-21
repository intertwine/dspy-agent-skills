# `dspy.GEPA` — Full Reference

Source: https://dspy.ai/api/optimizers/GEPA/overview/ (DSPy 3.2.x, April 2026).

## Location

- Top-level: `dspy.GEPA`
- Module path: `dspy.teleprompt.gepa.gepa.GEPA`
- Both imports resolve to the same class.

## Signature

```python
dspy.GEPA(
    metric: GEPAFeedbackMetric,
    auto: Literal["light", "medium", "heavy"] | None = None,
    max_full_evals: int | None = None,
    max_metric_calls: int | None = None,
    reflection_minibatch_size: int = 3,
    candidate_selection_strategy: Literal["pareto", "current_best"] = "pareto",
    reflection_lm: dspy.LM | None = None,
    skip_perfect_score: bool = True,
    add_format_failure_as_feedback: bool = False,
    instruction_proposer: ProposalFn | None = None,
    component_selector: ReflectionComponentSelector | str = "round_robin",
    use_merge: bool = True,
    max_merge_invocations: int | None = 5,
    num_threads: int | None = None,
    failure_score: float = 0.0,
    perfect_score: float = 1.0,
    log_dir: str | None = None,
    track_stats: bool = False,
    use_wandb: bool = False,
    wandb_api_key: str | None = None,
    wandb_init_kwargs: dict | None = None,
    track_best_outputs: bool = False,
    warn_on_score_mismatch: bool = True,
    use_mlflow: bool = False,
    seed: int | None = 0,
    gepa_kwargs: dict | None = None,
)
```

## `.compile()`

```python
compile(
    student: dspy.Module,
    *,
    trainset: list[dspy.Example],
    teacher: dspy.Module | None = None,   # not currently used
    valset: list[dspy.Example] | None = None,
) -> dspy.Module
```

Returns the best program found. If `track_stats=True`, the returned module has `.detailed_results` with:

- `val_aggregate_scores`: list of Pareto frontier scores.
- `candidate_programs`: every candidate GEPA proposed.
- `best_outputs_valset` (when `track_best_outputs=True`): per-task best predictions seen.
- `reflection_traces`: record of LM reflections.

## Metric contract

```python
metric(
    gold: dspy.Example,
    pred: dspy.Prediction,
    trace: DSPyTrace | None = None,
    pred_name: str | None = None,
    pred_trace: DSPyTrace | None = None,
) -> float | dspy.Prediction | str
```

Recommended return: `dspy.Prediction(score=float, feedback=str)`. When `pred_name` is set, return feedback targeted at that specific predictor's `pred_trace`. A plain dict with the same keys crashes `dspy.Evaluate`'s parallel aggregator (`TypeError: unsupported operand type(s) for +: 'int' and 'dict'`); GEPA uses `dspy.Evaluate` internally for candidate scoring, so the crash happens inside GEPA too. `dspy.Prediction` defines `__float__`/`__add__` so it aggregates correctly.

## `component_selector` options

- `"round_robin"` (default): cycle through predictors evenly.
- `"random"`: uniform random.
- Callable: `ReflectionComponentSelector` that decides which predictors get mutated this round based on past success.

## `instruction_proposer`

Custom function `(program, reflections, trace) -> str` that generates the next instruction candidate. Default uses the built-in reflective proposer. Override when you want domain-specific mutation operators (e.g. for code synthesis).

## Observability

```python
dspy.GEPA(..., log_dir="./gepa_logs", use_wandb=True, use_mlflow=True)
```

Writes per-round artifacts: `candidates/<id>.json`, `scores.jsonl`, `reflections/`. Resume by pointing `log_dir` at the same path.

## `dspy.BetterTogether` in 3.2.0

DSPy 3.2.0 expanded `dspy.BetterTogether` from a fixed prompt/weight pair into an arbitrary optimizer-chain wrapper:

```python
optimizer = dspy.BetterTogether(
    metric=metric,
    bootstrap=dspy.BootstrapFewShotWithRandomSearch(metric=metric),
    gepa=dspy.GEPA(metric=metric, auto="light", reflection_lm=reflection_lm),
)

optimized = optimizer.compile(
    student,
    trainset=trainset,
    valset=valset,
    strategy="bootstrap -> gepa",
)
```

The strategy keys come directly from the constructor kwargs (`bootstrap`, `gepa`, etc.), and `BetterTogether` evaluates each stage on the valset before returning the best program. Pass `strategy=` explicitly for named stages: DSPy 3.2.0's default remains `"p -> w -> p"`, which assumes your optimizer keys are literally `p` and `w`.

## Tuning guide

| Symptom | Lever |
|---|---|
| No improvement in first rounds | Check metric feedback is specific, not generic. Raise `reflection_lm` strength. |
| Oscillates between candidates | Lower `reflection_minibatch_size` from 3 to 2; prefer `candidate_selection_strategy="pareto"`. |
| OOM during reflection | Lower `reflection_lm` `max_tokens`; reduce trainset size. |
| Cost too high | Set explicit `max_metric_calls` instead of `auto="heavy"`. |
| Optimized program worse on held-out test | Valset too small / not representative; expand valset, set `skip_perfect_score=True`. |

## Related optimizers (for comparison)

- `dspy.MIPROv2` — Bayesian optimization over instructions + demos; best for large trainsets and scalar metrics.
- `dspy.BootstrapFewShot` — vanilla few-shot extraction; fast, low-signal.
- `dspy.BetterTogether` — as of DSPy 3.2.0, chains arbitrary named optimizers via `**optimizers` and a strategy string.
- `dspy.SIMBA` — simpler reflective optimizer, lighter-weight than GEPA.
