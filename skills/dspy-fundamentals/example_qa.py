"""Minimal DSPy 3.2.x QA program — runnable as a smoke test.

Usage:
    uv run python example_qa.py --dry-run         # syntax/import check only
    OPENAI_API_KEY=... uv run python example_qa.py

The --dry-run path exercises Signature/Module construction without calling an LM.
"""

from __future__ import annotations

import argparse
import os


def build_program():
    import dspy

    class QuestionAnswer(dspy.Signature):
        """Answer questions with rigorous step-by-step reasoning."""

        question: str = dspy.InputField()
        answer: str = dspy.OutputField(desc="concise final answer")

    class QAProgram(dspy.Module):
        def __init__(self):
            super().__init__()
            self.solve = dspy.ChainOfThought(QuestionAnswer)

        def forward(self, question: str):
            return self.solve(question=question)

    return QAProgram()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Skip LM call")
    parser.add_argument("--model", default=os.getenv("DSPY_MODEL", "openai/gpt-4o"))
    parser.add_argument("--question", default="What is 17 * 23?")
    args = parser.parse_args()

    import dspy

    program = build_program()

    if args.dry_run:
        print(f"OK: constructed {type(program).__name__} with predictors:")
        for name, _ in program.named_predictors():
            print(f"  - {name}")
        return 0

    dspy.configure(lm=dspy.LM(args.model), track_usage=True)
    pred = program(question=args.question)
    print("Reasoning:", pred.reasoning)
    print("Answer:", pred.answer)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
