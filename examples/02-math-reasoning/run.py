"""CLI runner for example 02: multi-step math reasoning.

Subcommands:
    --dry-run                 construct everything; no LM calls
    --baseline                evaluate un-optimized program on valset
    --optimize [--auto X]     GEPA-optimize; save program + rescore
    --eval PATH               evaluate a saved program on valset
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from examples.common import (  # noqa: E402
    configure_dspy,
    get_example_num_threads,
    get_reflection_lm,
    harden_example_lm,
)
from examples.common.data import read_jsonl  # noqa: E402


def _import_pipeline():
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "math_pipeline", Path(__file__).parent / "pipeline.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
RUNS = HERE / "runs"
ARTIFACT = HERE / "optimized_program.json"
RESULTS_JSON = HERE / "results.json"
RESULTS_MD = HERE / "results.md"


def _build_context():
    pipeline = _import_pipeline()
    trainset = pipeline.make_examples(read_jsonl(DATA / "train.jsonl"))
    valset = pipeline.make_examples(read_jsonl(DATA / "val.jsonl"))
    program = pipeline.build_program()
    return pipeline, program, trainset, valset


def _score_wrapper(metric):
    def m(g, p, trace=None, **kw):
        out = metric(g, p, trace, **kw)
        # `out` may be a bare float, a {"score": ...} dict, or a
        # ``dspy.Prediction(score=..., feedback=...)`` (the GEPA-native shape).
        if isinstance(out, dict):
            return out.get("score", 0.0)
        if hasattr(out, "score"):
            return float(out["score"])
        return float(out)

    return m


def _evaluator(valset, metric_for_eval):
    import dspy

    return dspy.Evaluate(
        devset=valset,
        metric=metric_for_eval,
        num_threads=get_example_num_threads(1),
        display_progress=True,
        provide_traceback=True,
        failure_score=0.0,
        save_as_json=str(RUNS / "last_eval.json"),
    )


def cmd_dry_run(_):
    pipeline, program, trainset, valset = _build_context()
    print(f"OK: trainset={len(trainset)}, valset={len(valset)}")
    for name, _ in program.named_predictors():
        print(f"  predictor: {name}")
    # Exercise the metric offline.
    import dspy

    fake = dspy.Prediction(answer="42", reasoning="therefore 42")
    out = pipeline.rich_metric(trainset[0], fake)
    score = (
        out["score"] if hasattr(out, "score") or isinstance(out, dict) else float(out)
    )
    feedback = (
        out["feedback"] if (hasattr(out, "feedback") or isinstance(out, dict)) else ""
    )
    print(f"  metric probe: score={score:.2f} feedback={feedback[:80]!r}")
    return 0


def cmd_baseline(_):
    pipeline, program, _train, valset = _build_context()
    harden_example_lm(configure_dspy())
    RUNS.mkdir(exist_ok=True)
    evaluator = _evaluator(valset, _score_wrapper(pipeline.rich_metric))
    t0 = time.time()
    result = evaluator(program)
    dt = time.time() - t0
    print(
        f"\nBASELINE overall={result.score:.3f}  ({dt:.1f}s over {len(valset)} examples)"
    )
    (RUNS / "baseline.json").write_text(
        json.dumps({"score": result.score, "n": len(valset)}, indent=2)
    )
    return 0


def cmd_optimize(args):
    import dspy

    pipeline, program, trainset, valset = _build_context()
    task_lm = harden_example_lm(configure_dspy())
    reflection_lm = harden_example_lm(get_reflection_lm())
    RUNS.mkdir(exist_ok=True)
    (HERE / "gepa_logs").mkdir(exist_ok=True)

    evaluator = _evaluator(valset, _score_wrapper(pipeline.rich_metric))

    print(">>> Baseline")
    t0 = time.time()
    baseline_score = evaluator(program).score
    baseline_dt = time.time() - t0
    print(f"BASELINE overall={baseline_score:.3f}  ({baseline_dt:.1f}s)")

    print(f"\n>>> GEPA optimize (auto={args.auto})")
    optimizer = dspy.GEPA(
        metric=pipeline.rich_metric,
        auto=args.auto,
        reflection_lm=reflection_lm,
        # With ~83% baseline accuracy on this task, minibatch=3 kept sampling
        # all-correct subsets for 139 iterations (reflection LM never called).
        # 8 lifts P(at-least-one-failure) above ~0.75 per iteration on a trainset
        # with ~4/25 failures, so GEPA actually gets signal to mutate on.
        reflection_minibatch_size=8,
        candidate_selection_strategy="pareto",
        use_merge=True,
        num_threads=get_example_num_threads(1),
        track_stats=True,
        track_best_outputs=True,
        log_dir=str(HERE / "gepa_logs"),
        seed=args.seed,
        # DSPy signatures defined inside helpers (as done in pipeline.py) are
        # dynamically generated classes that stdlib pickle cannot serialize.
        # cloudpickle handles these; see dspy.GEPA docstring -> gepa_kwargs.
        gepa_kwargs={"use_cloudpickle": True},
    )
    t1 = time.time()
    optimized = optimizer.compile(student=program, trainset=trainset, valset=valset)
    opt_dt = time.time() - t1
    print(f"GEPA compile took {opt_dt:.1f}s")

    print("\n>>> Optimized eval")
    t2 = time.time()
    optimized_score = evaluator(optimized).score
    eval_dt = time.time() - t2
    print(f"OPTIMIZED overall={optimized_score:.3f}  ({eval_dt:.1f}s)")

    optimized.save(str(ARTIFACT), save_program=False)

    results = {
        "task_model": str(dspy.settings.lm.model),
        "reflection_model": str(reflection_lm.model),
        "auto": args.auto,
        "seed": args.seed,
        "trainset_size": len(trainset),
        "valset_size": len(valset),
        "baseline_score": baseline_score,
        "optimized_score": optimized_score,
        "improvement": optimized_score - baseline_score,
        "baseline_seconds": round(baseline_dt, 1),
        "optimize_seconds": round(opt_dt, 1),
        "eval_seconds": round(eval_dt, 1),
    }
    RESULTS_JSON.write_text(json.dumps(results, indent=2))
    _write_results_md(results)
    return 0


def cmd_eval(args):
    pipeline, program, _train, valset = _build_context()
    harden_example_lm(configure_dspy())
    path = Path(args.eval)
    if not path.exists():
        print(f"error: {path} not found", file=sys.stderr)
        return 2
    program.load(str(path))
    evaluator = _evaluator(valset, _score_wrapper(pipeline.rich_metric))
    score = evaluator(program).score
    print(f"{path.name}: {score:.3f}")
    return 0


def _write_results_md(r: dict) -> None:
    delta = r["optimized_score"] - r["baseline_score"]
    RESULTS_MD.write_text(
        f"""# Example 02 — Math Reasoning Results

| Metric | Baseline | Optimized | Δ |
|---|---:|---:|---:|
| Exact-match (numeric) | {r["baseline_score"]:.3f} | {r["optimized_score"]:.3f} | **{delta:+.3f}** |

- Task LM: `{r["task_model"]}`
- Reflection LM: `{r["reflection_model"]}`
- GEPA mode: `auto="{r["auto"]}"`, seed={r["seed"]}
- Trainset: {r["trainset_size"]} · valset: {r["valset_size"]}
- Times: baseline {r["baseline_seconds"]}s, optimize {r["optimize_seconds"]}s, optimized-eval {r["eval_seconds"]}s

Metric: exact match on final numeric answer (partial credit 0.2 for near-misses
within 10% relative error). Feedback includes per-problem `trap` hints so the
reflection LM can learn structural fixes rather than memorize answers.
See `pipeline.py:rich_metric`.
"""
    )


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--dry-run", action="store_true")
    g.add_argument("--baseline", action="store_true")
    g.add_argument("--optimize", action="store_true")
    g.add_argument("--eval", metavar="PATH")
    ap.add_argument("--auto", default="light", choices=["light", "medium", "heavy"])
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    if args.dry_run:
        return cmd_dry_run(args)
    if args.baseline:
        return cmd_baseline(args)
    if args.optimize:
        return cmd_optimize(args)
    if args.eval:
        return cmd_eval(args)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
