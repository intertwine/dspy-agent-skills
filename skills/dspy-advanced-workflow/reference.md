# DSPy Advanced Workflow — Reference

Source: orchestration pattern built on https://dspy.ai/ (DSPy 3.2.x).

This reference complements `SKILL.md` with deeper guidance on each of the seven steps.

## Seven-step orchestration

```
1. Spec → 2. Program → 3. Data → 4. Rich metric → 5. Baseline → 6. GEPA optimize → 7. Export
```

Steps 1–4 are setup. Steps 5–7 are the compile-evaluate-ship loop.

## Step-by-step failure modes

| Step | Common failure | Fix |
|---|---|---|
| 1. Spec | Signature too broad ("do the task") | One-sentence instruction; name specific inputs/outputs |
| 2. Program | Hard-coded prompts in `forward()` | Let predictors own instructions; GEPA can't mutate strings |
| 3. Data | `trainset == valset` | Always split; overlap causes GEPA to overfit silently |
| 3. Data | Fewer than 15 examples | GEPA's reflection minibatch needs enough variety to learn |
| 4. Metric | Generic feedback ("wrong") | Cite the specific field, expected vs. actual, and why |
| 4. Metric | Returns a dict instead of `dspy.Prediction` | `dspy.Evaluate` crashes: `TypeError: int + dict` |
| 5. Baseline | Skipped entirely | No baseline means no claim of improvement |
| 6. GEPA | `reflection_lm` is None | GEPA asserts at construction time, not compile time |
| 6. GEPA | Plateau after round 1–2 | Weak feedback, small `reflection_minibatch_size`, or model saturation |
| 7. Export | `save_program=True` on untested code | Prefer `save_program=False` (state-only) unless deploying standalone |

## `auto` level selection

```python
dspy.GEPA(metric=metric, auto="light" | "medium" | "heavy", ...)
```

| Level | Budget | When to use |
|---|---|---|
| `"light"` | ~50 metric calls | Sanity check; confirm metric and `reflection_lm` work |
| `"medium"` | ~200 metric calls | Default for most tasks |
| `"heavy"` | ~500+ metric calls | Final production run after `"medium"` shows improvement |
| `None` | Set `max_full_evals` / `max_metric_calls` | Fine-grained control for cost-sensitive runs |

Always start with `"light"`. If it shows no movement, the problem is usually the metric feedback or the `reflection_lm`, not the budget.

## Debugging optimizer plateaus

| Check | What to look for |
|---|---|
| Metric feedback quality | Run metric on 5 failing examples manually; if feedback is vague ("incorrect"), GEPA has nothing to learn from |
| `reflection_minibatch_size` | Default is 3; with baseline >0.7, GEPA may sample all-correct subsets. Raise to 6–8 |
| Train/val overlap | Deduplicate `trainset` and `valset`; shared examples cause memorization |
| `reflection_lm` strength | Must be capable enough to critique and propose better instructions; a 7B model reflecting on a 70B model's output rarely helps |
| Model saturation | Baseline >0.95 means GEPA correctly no-ops; use a weaker task LM or harder evaluation set |

## Export formats

```python
# State-only (recommended for production)
optimized.save("artifacts/program.json", save_program=False)

# Full program (includes serialized module code)
optimized.save("artifacts/program_dir/", save_program=True)

# Loading
reloaded = MyProgram()
reloaded.load("artifacts/program.json")
# or
reloaded = dspy.load("artifacts/program_dir/")
```

| Method | What's saved | Portable | Use case |
|---|---|---|---|
| `save_program=False` | Optimized state (instructions, demos) | Yes | Production; reconstruct module in serving code |
| `save_program=True` | State + serialized module via cloudpickle | Partial | Standalone artifacts, quick prototyping |

Prefer `save_program=False`. It decouples the optimized state from the module definition, so you can update module code without re-optimizing.

## `dspy.BetterTogether` chaining (3.2.x)

```python
optimizer = dspy.BetterTogether(
    metric=rich_metric,
    bootstrap=dspy.BootstrapFewShotWithRandomSearch(metric=rich_metric),
    gepa=dspy.GEPA(metric=rich_metric, auto="light", reflection_lm=reflection_lm),
)
optimized = optimizer.compile(
    student=program, trainset=trainset, valset=valset,
    strategy="bootstrap -> gepa",
)
```

Strategy keys come from the constructor kwargs. Default strategy is `"p -> w -> p"`, which assumes keys are literally `p` and `w`. Always pass `strategy=` explicitly with named stages.

Get a clean single-optimizer baseline before using `BetterTogether`.

## Sub-skill cross-references

| Step | Sub-skill | Reference |
|---|---|---|
| 1–2. Spec & Program | `dspy-fundamentals` | [`reference.md`](../dspy-fundamentals/reference.md) |
| 3–4. Data & Metric | `dspy-evaluation-harness` | [`reference.md`](../dspy-evaluation-harness/reference.md) |
| 6. GEPA optimize | `dspy-gepa-optimizer` | [`reference.md`](../dspy-gepa-optimizer/reference.md) |
| Long-context variant | `dspy-rlm-module` | [`reference.md`](../dspy-rlm-module/reference.md) |
