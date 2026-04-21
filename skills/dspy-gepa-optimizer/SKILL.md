---
name: dspy-gepa-optimizer
description: Optimize DSPy programs with dspy.GEPA — the reflective/evolutionary optimizer that is the 2026 gold standard for DSPy (beats MIPROv2 on complex tasks with far fewer rollouts when the metric returns rich feedback). Use when the user says optimize, compile, GEPA, reflective optimization, or "make this program better" and a DSPy program + metric + trainset exist.
when_to_use: User asks to optimize/compile/tune a DSPy program, mentions GEPA or reflective optimization, or has a working program with a non-trivial metric and wants to improve it.
---

# DSPy GEPA Optimizer (3.2.x)

GEPA (Genetic-Pareto) is a reflective optimizer: it mutates a program's instructions and few-shots using an LM that reads your metric's **textual feedback** and proposes improvements. It maintains a Pareto frontier across validation tasks and is the default recommendation for complex DSPy workloads in 2026.

> The expansion "Genetic-Evolutionary Prompt Adaptation" that appears in some AI-generated summaries is an LLM-hallucinated backronym. The [paper](https://arxiv.org/abs/2507.19457) defines GEPA as Genetic-Pareto; the "Pareto" is load-bearing (GEPA keeps a frontier of candidates rather than collapsing to one).

## Prerequisites — do these first or GEPA wastes rollouts

1. A `dspy.Module` that runs end-to-end (see `dspy-fundamentals`).
2. A rich-feedback metric returning `dspy.Prediction(score=float, feedback=str)` (see `dspy-evaluation-harness`). **A float-only metric makes GEPA no better than MIPRO.** A dict with the same fields crashes `dspy.Evaluate`'s parallel aggregator — use `dspy.Prediction`.
3. `trainset` (15–50 examples) and a **separate** `valset` (15–50 examples). Optimizer will overfit trainset; valset selects the best candidate.
4. A `reflection_lm` — a strong LM (often the same or stronger than the task LM) set to `temperature=1.0` for creative proposals.

## Canonical call

```python
import dspy

dspy.configure(lm=dspy.LM("openai/gpt-4o"))
reflection_lm = dspy.LM("openai/gpt-4o", temperature=1.0, max_tokens=8000)

optimizer = dspy.GEPA(
    metric=rich_metric,
    auto="medium",                       # "light" / "medium" / "heavy"
    reflection_lm=reflection_lm,
    reflection_minibatch_size=3,
    candidate_selection_strategy="pareto",  # or "current_best"
    skip_perfect_score=True,
    use_merge=True,
    num_threads=8,
    track_stats=True,
    track_best_outputs=True,             # enables inference-time best-of selection
    log_dir="./gepa_logs",               # resume/checkpoint
    seed=0,
)

optimized = optimizer.compile(
    student=program,
    trainset=trainset,
    valset=valset,
)

# Pareto inspection
pareto = optimized.detailed_results.val_aggregate_scores
print("Pareto frontier:", sorted(pareto, reverse=True)[:5])

optimized.save("optimized_program.json", save_program=False)
```

## Import paths

Either works; use the top-level in new code:

```python
import dspy
dspy.GEPA(...)                              # preferred
# equivalently:
from dspy.teleprompt import GEPA
```

## Metric contract (precise)

```python
import dspy

def rich_metric(gold, pred, trace=None, pred_name=None, pred_trace=None):
    score = ...      # 0.0..1.0
    feedback = ...   # detailed natural-language critique
    return dspy.Prediction(score=score, feedback=feedback)
```

**Return `dspy.Prediction`, not a dict.** A dict with the same keys crashes `dspy.Evaluate`'s parallel aggregator (`TypeError: unsupported operand type(s) for +: 'int' and 'dict'`). GEPA uses `dspy.Evaluate` internally for candidate scoring, so the dict-return will fail inside GEPA too, not just in your explicit `Evaluate(...)` calls.

- `pred_name` / `pred_trace` are set during reflection on a specific predictor inside your module — write per-predictor feedback when possible (credit assignment).
- Feedback quality is the load-bearing part: specifics about *why* it failed and *what good looks like* are what the reflection LM acts on.

## Budget knobs

Use **either** `auto=...` **or** explicit budget — not both.

| Mode | Rough rollouts | When to use |
|---|---|---|
| `auto="light"` | ~20–40 full evals | Sanity-check GEPA works on your metric |
| `auto="medium"` | ~80–150 full evals | Everyday optimization |
| `auto="heavy"` | ~300–600 full evals | Final run before ship |
| `max_full_evals=N` | Explicit | Deterministic budget |
| `max_metric_calls=N` | Explicit | Hard cap on metric invocations (more predictable cost) |

Each "full eval" ≈ `len(valset)` metric calls. Budget accordingly for cost.

## Constructor parameters (every one, DSPy 3.2.x)

```python
dspy.GEPA(
    metric,                                  # required
    auto=None,                               # Literal["light","medium","heavy"] | None
    max_full_evals=None,
    max_metric_calls=None,
    reflection_minibatch_size=3,
    candidate_selection_strategy="pareto",   # or "current_best"
    reflection_lm=None,                      # required in practice
    skip_perfect_score=True,
    add_format_failure_as_feedback=False,
    instruction_proposer=None,               # custom ProposalFn
    component_selector="round_robin",        # or a callable
    use_merge=True,
    max_merge_invocations=5,
    num_threads=None,
    failure_score=0.0,
    perfect_score=1.0,
    log_dir=None,
    track_stats=False,
    use_wandb=False,
    wandb_api_key=None,                      # overrides WANDB_API_KEY env var
    wandb_init_kwargs=None,                  # dict forwarded to wandb.init(...)
    track_best_outputs=False,
    warn_on_score_mismatch=True,
    use_mlflow=False,
    seed=0,
    gepa_kwargs=None,                        # e.g. {"use_cloudpickle": True} for dynamic signatures
)
```

`.compile(student, *, trainset, valset=None, teacher=None)` — `teacher` is not currently used.

## BetterTogether in DSPy 3.2.x

If you want a multi-stage optimizer loop, DSPy 3.2.0's `BetterTogether` now accepts arbitrary named optimizers instead of the older fixed `prompt_optimizer` / `weight_optimizer` pair:

```python
optimizer = dspy.BetterTogether(
    metric=rich_metric,
    bootstrap=dspy.BootstrapFewShotWithRandomSearch(metric=rich_metric),
    gepa=dspy.GEPA(metric=rich_metric, auto="light", reflection_lm=reflection_lm),
)

optimized = optimizer.compile(
    student=program,
    trainset=trainset,
    valset=valset,
    strategy="bootstrap -> gepa",
)
```

Pass `strategy=` explicitly when you use named stages like `bootstrap=...` and `gepa=...`. DSPy 3.2.0's default strategy is still `"p -> w -> p"`, which only works if your optimizer keys are literally `p` and `w`.

Keep plain GEPA as the default first pass. Reach for `BetterTogether` only when you have a specific reason to chain optimizers and want the valset to pick the best intermediate program.

## When GEPA > MIPROv2

- Your metric can produce specific, teachable critiques (GEPA's superpower).
- The program has multiple predictors that need targeted improvements (GEPA gives per-predictor feedback; MIPRO doesn't).
- Rollout budget is small (GEPA converges faster with rich feedback).

## When MIPROv2 > GEPA

- Metric is scalar-only (no signal to reflect on) — use `dspy.MIPROv2`.
- You want pure few-shot bootstrapping with no instruction mutation.
- Very large trainset (500+) where Bayesian search over demos pays off.

## Resume & checkpointing

`log_dir` writes candidate programs + scores per round. To resume an interrupted run, point `log_dir` at the same directory — GEPA picks up from the last checkpoint. Inspect `<log_dir>/candidates/` to see every proposed program.

## Inference-time best-of with `track_best_outputs`

With `track_best_outputs=True`, GEPA records, per task, the best prediction seen across all candidates. At inference time on held-out data, you can ensemble or select among the top-Pareto programs for robustness. Access via `optimized.detailed_results.best_outputs_valset`.

## Anti-patterns

- Float-only metric ("score is 0.7") with no feedback — GEPA collapses to random search.
- Same set used for train and val — Pareto selection overfits.
- `reflection_lm` = small model — it can't critique; use the strongest LM you can afford for this role.
- Running `auto="heavy"` on an untested metric — burn money to learn the metric was bugged. Run `auto="light"` first.
- Ignoring `log_dir` — losing a 4-hour run to a disconnect is very painful.

## Gotcha: `reflection_lm` is required at construction, not compile

`dspy.GEPA(...)` asserts `reflection_lm is not None` (or a custom `instruction_proposer`) *at init time* — you cannot defer it to `.compile()`. If you see

```
AssertionError: GEPA requires a reflection language model...
```

add `reflection_lm=dspy.LM("openai/gpt-4o", temperature=1.0, max_tokens=8000)` to the constructor. `dspy.LM(...)` is a cheap stub until you actually call it, so constructing one doesn't hit the network.

## Next

- Build the metric → `dspy-evaluation-harness`.
- End-to-end pipeline → `dspy-advanced-workflow`.
- Parameter reference → [reference.md](reference.md).
- Runnable example → [example_gepa.py](example_gepa.py).
- BetterTogether chaining example → [example_bettertogether.py](example_bettertogether.py).
