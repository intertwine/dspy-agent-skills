"""DSPy 3.2.x BetterTogether chaining demo.

This example showcases DSPy 3.2.0's generalized BetterTogether API, where
named optimizers are passed as keyword arguments and chained via a strategy
string. The --dry-run path constructs the whole setup without calling an LM.

Usage:
    uv run python example_bettertogether.py --dry-run
    OPENAI_API_KEY=... uv run python example_bettertogether.py --strategy "bootstrap -> gepa"
"""

from __future__ import annotations

import argparse
from pathlib import Path


def build():
    import dspy

    class QA(dspy.Signature):
        """Answer the question with a concise final answer."""

        question: str = dspy.InputField()
        answer: str = dspy.OutputField()

    class QAProgram(dspy.Module):
        def __init__(self):
            super().__init__()
            self.solve = dspy.ChainOfThought(QA)

        def forward(self, question: str) -> dspy.Prediction:
            return self.solve(question=question)

    def make_example(question: str, answer: str):
        return dspy.Example(question=question, answer=answer).with_inputs("question")

    trainset = [
        make_example("2 + 2?", "4"),
        make_example("Capital of Japan?", "Tokyo"),
        make_example("Largest planet?", "Jupiter"),
        make_example("Square root of 144?", "12"),
        make_example("H2O is the formula for?", "water"),
        make_example("What gas do plants breathe in?", "carbon dioxide"),
    ]
    valset = [
        make_example("5 * 6?", "30"),
        make_example("Capital of Italy?", "Rome"),
        make_example("What planet do humans live on?", "Earth"),
    ]

    def rich_metric(gold, pred, trace=None, pred_name=None, pred_trace=None):
        pred_answer = str(getattr(pred, "answer", "")).strip().lower()
        gold_answer = gold.answer.strip().lower()
        correct = pred_answer == gold_answer
        score = 1.0 if correct else 0.0
        if correct:
            feedback = "Correct and concise."
        else:
            feedback = (
                f"Incorrect. Got {pred_answer!r}, expected {gold_answer!r}. "
                "End with only the final answer value and avoid extra prose."
            )
        return dspy.Prediction(score=score, feedback=feedback)

    return QAProgram(), trainset, valset, rich_metric


def build_optimizer(task_model: str, reflection_model: str | None, rich_metric, auto: str):
    import dspy

    task_lm = dspy.LM(task_model)
    reflection_lm = dspy.LM(
        reflection_model or task_model,
        temperature=1.0,
        max_tokens=8000,
    )

    optimizer = dspy.BetterTogether(
        metric=rich_metric,
        bootstrap=dspy.BootstrapFewShotWithRandomSearch(
            metric=rich_metric,
            max_bootstrapped_demos=2,
            max_labeled_demos=2,
            max_rounds=1,
            num_candidate_programs=4,
        ),
        gepa=dspy.GEPA(
            metric=rich_metric,
            auto=auto,
            reflection_lm=reflection_lm,
            track_stats=True,
            seed=0,
        ),
    )
    return task_lm, optimizer


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--model", default="openai/gpt-4o")
    parser.add_argument("--reflection-model", default=None)
    parser.add_argument("--auto", default="light", choices=["light", "medium", "heavy"])
    parser.add_argument("--strategy", default="bootstrap -> gepa")
    args = parser.parse_args()

    import dspy

    program, trainset, valset, rich_metric = build()
    task_lm, optimizer = build_optimizer(
        task_model=args.model,
        reflection_model=args.reflection_model,
        rich_metric=rich_metric,
        auto=args.auto,
    )

    if args.dry_run:
        program.set_lm(task_lm)
        print("OK: constructed dspy.BetterTogether with named optimizers.")
        print(f"    optimizers: {sorted(optimizer.optimizers.keys())}")
        print(f"    example strategy: {args.strategy}")
        print(f"    trainset={len(trainset)} valset={len(valset)}")
        return 0

    dspy.configure(lm=task_lm, track_usage=True)
    program.set_lm(task_lm)

    evaluator = dspy.Evaluate(
        devset=valset,
        metric=rich_metric,
        num_threads=4,
        display_progress=True,
        provide_traceback=True,
    )
    print(f"Baseline: {evaluator(program).score:.3f}")

    optimized = optimizer.compile(
        student=program,
        trainset=trainset,
        valset=valset,
        strategy=args.strategy,
        num_threads=4,
        provide_traceback=True,
        seed=0,
    )

    print(f"Optimized: {evaluator(optimized).score:.3f}")
    best_strategy = optimized.candidate_programs[0]["strategy"] or "baseline"
    print(f"Best strategy: {best_strategy}")

    out = Path("optimized_program.json")
    optimized.save(str(out), save_program=False)
    print(f"Saved -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
