---
name: dspy-advanced-workflow
description: Drive a complete DSPy 3.2.x project end-to-end — spec → program → metric → baseline → GEPA optimize → export → deploy. Orchestrates the other four DSPy skills (dspy-fundamentals, dspy-evaluation-harness, dspy-gepa-optimizer, dspy-rlm-module) in the correct order. Use this for any non-trivial DSPy build from scratch.
when_to_use: User wants to build, optimize, and ship a new DSPy pipeline; says "full workflow" / "end to end" / "from scratch"; or needs the standard loop applied to a greenfield task.
---

# DSPy Advanced Workflow (2026)

This skill runs the seven-step loop that turns a natural-language task description into an optimized, saved, deployable DSPy program. Every step delegates to a specific skill — invoke them in order.

## The seven steps

### 1. Spec

Rephrase the user's task in one sentence. Identify inputs, outputs, the quality axis that matters, and any constraints (latency, cost, tool access, context size). Pick predictor shape:

| Task shape | Predictor |
|---|---|
| Single-step structured I/O | `dspy.Predict` / `dspy.ChainOfThought` |
| Tool use / multi-step | `dspy.ReAct` |
| Code execution | `dspy.ProgramOfThought` |
| Long context / codebase | `dspy.RLM` → `dspy-rlm-module` |

### 2. Program

Write the typed `dspy.Signature` + `dspy.Module` subclass per `dspy-fundamentals`. No hard-coded prompts. Keep predictors named so GEPA can target them.

### 3. Data

Build `trainset` (15–50) and **separate** `valset` (15–50) as `dspy.Example(...).with_inputs(...)`. Held-out `testset` is reported on at the end only. See `dspy-evaluation-harness`.

### 4. Rich metric

Write `rich_metric(gold, pred, trace=None, pred_name=None, pred_trace=None)` returning `dspy.Prediction(score=0..1, feedback="natural-language critique")`. The feedback is load-bearing — it's what GEPA's reflection LM learns from. A dict with the same fields crashes `dspy.Evaluate`; only `dspy.Prediction` aggregates correctly. See `dspy-evaluation-harness`.

### 5. Baseline

```python
evaluator = dspy.Evaluate(devset=valset, metric=rich_metric,
                          num_threads=8, display_progress=True,
                          provide_traceback=True,
                          save_as_json="runs/baseline.json")
baseline = evaluator(program)
print("Baseline:", baseline.score)
```

### 6. GEPA optimize

```python
reflection_lm = dspy.LM("openai/gpt-4o", temperature=1.0, max_tokens=8000)
optimizer = dspy.GEPA(
    metric=rich_metric,
    auto="medium",
    reflection_lm=reflection_lm,
    candidate_selection_strategy="pareto",
    track_stats=True,
    track_best_outputs=True,
    log_dir="./gepa_logs",
    num_threads=8,
    seed=0,
)
optimized = optimizer.compile(student=program, trainset=trainset, valset=valset)
print("Optimized:", evaluator(optimized).score)
```

Run `auto="light"` first as a sanity check; move to `auto="medium"`/`"heavy"` for the final run. See `dspy-gepa-optimizer`.

If you need a deliberate multi-stage compile loop, DSPy 3.2.x also exposes `dspy.BetterTogether(metric=..., bootstrap=..., gepa=...)` for chaining named optimizers after you have a clean baseline GEPA setup.

### 7. Export & deploy

```python
optimized.save("artifacts/program.json", save_program=False)     # state, portable
# or for full deployment artifact:
optimized.save("artifacts/program_dir/", save_program=True)
```

Deploy:
- Load with `dspy.load("artifacts/program_dir/")` or reconstruct + `.load("program.json")`.
- Wrap in FastAPI/CLI.
- Enable `track_usage=True` for cost/latency observability.
- Log with MLflow (`mlflow.dspy.autolog()`) or W&B in CI.
- Keep an offline regression test that runs the `evaluator` against the saved program and fails CI below a threshold.

## Full orchestration template

```python
"""DSPy end-to-end pipeline — spec → optimize → deploy."""

import dspy
from pathlib import Path

# ----- 1–2. Spec & program (dspy-fundamentals) -----
class MyTask(dspy.Signature):
    """<one-line instruction from the spec>."""
    input_field: str = dspy.InputField()
    output_field: str = dspy.OutputField()

class MyProgram(dspy.Module):
    def __init__(self):
        super().__init__()
        self.step = dspy.ChainOfThought(MyTask)
    def forward(self, **kw):
        return self.step(**kw)

# ----- 3. Data (dspy-evaluation-harness) -----
trainset = [...]   # list[dspy.Example(...).with_inputs(...)]
valset   = [...]

# ----- 4. Rich metric (dspy-evaluation-harness) -----
def rich_metric(gold, pred, trace=None, pred_name=None, pred_trace=None):
    score = ...          # compute 0..1
    feedback = ...       # detailed critique
    return dspy.Prediction(score=score, feedback=feedback)  # NOT a dict

# ----- 5. Baseline -----
dspy.configure(lm=dspy.LM("openai/gpt-4o"), track_usage=True)
evaluator = dspy.Evaluate(devset=valset, metric=rich_metric, num_threads=8,
                          display_progress=True, provide_traceback=True,
                          save_as_json="runs/baseline.json")
program = MyProgram()
print("Baseline:", evaluator(program).score)

# ----- 6. GEPA optimize (dspy-gepa-optimizer) -----
optimizer = dspy.GEPA(
    metric=rich_metric,
    auto="medium",
    reflection_lm=dspy.LM("openai/gpt-4o", temperature=1.0, max_tokens=8000),
    candidate_selection_strategy="pareto",
    track_stats=True, track_best_outputs=True,
    log_dir="./gepa_logs", num_threads=8, seed=0,
)
optimized = optimizer.compile(student=program, trainset=trainset, valset=valset)
print("Optimized:", evaluator(optimized).score)

# ----- 7. Export (dspy-fundamentals) -----
Path("artifacts").mkdir(exist_ok=True)
optimized.save("artifacts/program.json", save_program=False)
```

## Guardrails

- Never skip step 3 (rich metric). GEPA without feedback ≈ random search.
- Always baseline before optimizing — no baseline, no claim.
- Save both pre- and post-optimization metrics to JSON for auditability.
- If held-out test score drops post-optimization, your valset is too narrow. Expand valset and re-run.
- Freeze optimized program with `module._compiled = True` before multi-stage re-compilation.

## Runnable scaffold → [example_pipeline.py](example_pipeline.py)
