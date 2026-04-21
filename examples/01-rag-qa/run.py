"""CLI runner for example 01: RAG QA with citations.

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
    """Import the sibling pipeline module despite hyphenated parent dir.

    The module is registered in ``sys.modules`` so that pickle (used by GEPA's
    checkpointing) can round-trip classes defined in it (signatures, modules).
    """
    import importlib.util

    name = "rag_qa_pipeline"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(
        name, Path(__file__).parent / "pipeline.py"
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
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
    docs = read_jsonl(DATA / "docs.jsonl")
    train_raw = read_jsonl(DATA / "train.jsonl")
    val_raw = read_jsonl(DATA / "val.jsonl")

    retriever = pipeline.BM25Retriever(docs, k=3)
    program = pipeline.build_program(retriever)
    trainset = pipeline.make_examples(train_raw)
    valset = pipeline.make_examples(val_raw)
    return pipeline, program, trainset, valset, docs


def _evaluator(valset, metric):
    import dspy

    return dspy.Evaluate(
        devset=valset,
        metric=lambda g, p, trace=None, **kw: metric(g, p, trace, **kw),
        num_threads=get_example_num_threads(2),
        display_progress=True,
        provide_traceback=True,
        failure_score=0.0,
        save_as_json=str(RUNS / "last_eval.json"),
    )


def _score_wrapper(metric):
    """dspy.Evaluate needs a metric returning a float; unwrap dict→float."""

    def m(g, p, trace=None, **kw):
        out = metric(g, p, trace, **kw)
        if isinstance(out, dict):
            return out.get("score", 0.0)
        return float(out)

    return m


def cmd_dry_run(_args):
    pipeline, program, trainset, valset, docs = _build_context()
    print(f"OK: docs={len(docs)}, trainset={len(trainset)}, valset={len(valset)}")
    for name, _ in program.named_predictors():
        print(f"  predictor: {name}")
    sample = trainset[0]
    hits = program._retriever.retrieve(sample.question)
    print(f"  retrieval probe for {sample.question!r} → {[h['id'] for h in hits]}")
    return 0


def cmd_baseline(_args):
    import dspy  # noqa: F401

    pipeline, program, trainset, valset, _docs = _build_context()
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

    pipeline, program, trainset, valset, _docs = _build_context()
    harden_example_lm(configure_dspy())
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
        reflection_minibatch_size=3,
        candidate_selection_strategy="pareto",
        use_merge=True,
        num_threads=get_example_num_threads(2),
        track_stats=True,
        track_best_outputs=True,
        log_dir=str(HERE / "gepa_logs"),
        seed=args.seed,
        # ChainOfThought synthesises a dynamic signature subclass whose
        # qualname isn't importable; cloudpickle handles that where stdlib
        # pickle chokes when GEPA checkpoints state. ``use_cloudpickle`` is
        # forwarded to the underlying ``gepa`` engine via ``gepa_kwargs``.
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
    print(f"\nSaved → {ARTIFACT}")

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
    print(f"\nWrote {RESULTS_JSON.name} and {RESULTS_MD.name}")
    return 0


def cmd_eval(args):
    pipeline, program, _trainset, valset, _docs = _build_context()
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
        f"""# Example 01 — RAG QA Results

| Metric | Baseline | Optimized | Δ |
|---|---:|---:|---:|
| Overall | {r["baseline_score"]:.3f} | {r["optimized_score"]:.3f} | **{delta:+.3f}** |

- Task LM: `{r["task_model"]}`
- Reflection LM: `{r["reflection_model"]}`
- GEPA mode: `auto="{r["auto"]}"`, seed={r["seed"]}
- Trainset: {r["trainset_size"]} · valset: {r["valset_size"]}
- Times: baseline {r["baseline_seconds"]}s, optimize {r["optimize_seconds"]}s, optimized-eval {r["eval_seconds"]}s

Metric axes: correctness (0.55) + citation validity (0.30) + conciseness (0.15).
See `pipeline.py:rich_metric` for the exact scoring.
"""
    )


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--dry-run", action="store_true")
    g.add_argument("--baseline", action="store_true")
    g.add_argument("--optimize", action="store_true")
    g.add_argument("--eval", metavar="PATH", help="score a saved program JSON")
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
