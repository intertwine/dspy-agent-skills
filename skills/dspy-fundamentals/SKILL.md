---
name: dspy-fundamentals
description: Write idiomatic DSPy 3.2.x programs — typed Signatures, dspy.Module subclasses, Predict/ChainOfThought/ReAct/ProgramOfThought, and save/load. Use this when starting any new DSPy project or when fixing non-idiomatic DSPy code (hard-coded prompts, ad-hoc string templates, untyped outputs, non-serializable classes).
when_to_use: User mentions DSPy, writes a file that imports `dspy`, asks to build an LLM pipeline/program/agent with structured inputs/outputs, or requests refactoring of prompt-engineering code into a programmatic framework.
---

# DSPy Fundamentals (3.2.x)

DSPy is the "PyTorch for prompts" — you declare **Signatures** (typed I/O contracts), compose them into **Modules**, and let optimizers (not you) tune the instructions and few-shot examples. Never write raw prompts.

## The one-paragraph model

Configure a single LM globally with `dspy.configure(lm=...)`. Define a `dspy.Signature` subclass with `dspy.InputField()` / `dspy.OutputField()` (docstring becomes the instruction). Wrap it in a predictor — `dspy.Predict` (direct), `dspy.ChainOfThought` (adds reasoning), `dspy.ReAct` (tool-using agent), `dspy.ProgramOfThought` (code-executing), or `dspy.RLM` (long-context). Subclass `dspy.Module` to compose multi-step programs. For built-in providers, use `dspy.LM("provider/model")`; for a truly custom backend, subclass `dspy.BaseLM`. Optimize later with GEPA.

## Canonical template

```python
import dspy

dspy.configure(lm=dspy.LM("openai/gpt-4o"), track_usage=True)

class QuestionAnswer(dspy.Signature):
    """Answer questions with rigorous step-by-step reasoning."""
    question: str = dspy.InputField()
    answer: str = dspy.OutputField(desc="concise final answer")

class QAProgram(dspy.Module):
    def __init__(self):
        super().__init__()
        self.solve = dspy.ChainOfThought(QuestionAnswer)

    def forward(self, question: str) -> dspy.Prediction:
        return self.solve(question=question)

program = QAProgram()
pred = program(question="What is 2 + 2?")
print(pred.reasoning, pred.answer)
```

## Predictor cheatsheet (DSPy 3.2.x)

| Predictor | When to use | Adds |
|---|---|---|
| `dspy.Predict(sig)` | Simple structured I/O | nothing — just the signature |
| `dspy.ChainOfThought(sig)` | Reasoning tasks | a `reasoning` output field |
| `dspy.ReAct(sig, tools=[...], max_iters=20)` | Tool-using agent | Thought/Action/Observation loop |
| `dspy.ProgramOfThought(sig, max_iters=3)` | Math/data tasks | generates & runs Python (needs Deno) |
| `dspy.RLM(sig, ...)` | Long context / codebases | recursive REPL exploration (see `dspy-rlm-module`) |

## Typed outputs — use Pydantic on fields, not `TypedPredictor`

`dspy.TypedPredictor` is superseded; `dspy.Predict` now handles Pydantic types natively via field annotations.

```python
from pydantic import BaseModel
from typing import Literal

class Entity(BaseModel):
    name: str
    kind: Literal["person", "org", "place"]

class ExtractEntities(dspy.Signature):
    """Extract named entities from text."""
    text: str = dspy.InputField()
    entities: list[Entity] = dspy.OutputField()

extractor = dspy.Predict(ExtractEntities)
```

## Save & load

Two modes — know the difference:

```python
# State-only (portable JSON; you must rebuild the architecture to load)
program.save("program.json", save_program=False)
new = QAProgram(); new.load("program.json")

# Full program (cloudpickle into a directory; restores everything)
program.save("./program_dir/", save_program=True)
restored = dspy.load("./program_dir/")
```

Prefer state-only for version control; full-program for deployment artifacts.

## Ten anti-patterns to refuse

1. Hard-coded prompt strings (`"You are a helpful assistant..."`) — write a Signature.
2. `dspy.TypedPredictor(...)` in new code — use `dspy.Predict` with Pydantic fields.
3. `dspy.OpenAI(...)` / `dspy.settings.configure(...)` — use `dspy.configure(lm=dspy.LM(...))`.
4. Provider-specific LM classes for built-in providers — use `dspy.LM("provider/model")`. If DSPy doesn't ship your backend, subclass `dspy.BaseLM`.
5. Giant monolithic predictors that do five jobs — decompose into a `Module` with named sub-predictors.
6. Mutating `signature.instructions` by hand — let the optimizer do it.
7. In-lining few-shot demos in the Signature docstring — bootstrap/optimize them.
8. Using `pickle.dump(program)` — use `program.save(...)`.
9. Setting an LM per module at construction time without reason — configure globally, override only when you need model mixing.
10. Vague metrics (yes/no, exact-match only) when training an optimizer — see `dspy-evaluation-harness`.

## Configuring the LM

```python
dspy.configure(
    lm=dspy.LM("openai/gpt-4o", temperature=0.0, max_tokens=2000),
    track_usage=True,        # accumulate token counts on predictions
    async_max_workers=4,     # for .acall / batch
)
```

DSPy 3.2.x warns by default when a module call passes extra input fields or values that don't match the signature's declared types. Treat those warnings as a callsite bug first; if you're intentionally passing pre-serialized values, disable them with `dspy.configure(warn_on_type_mismatch=False)`.

Common provider prefixes: `openai/`, `anthropic/`, `azure/`, `vertex_ai/`, `bedrock/`, `ollama/`. For local Ollama: `dspy.LM("ollama_chat/llama3.1:8b", api_base="http://localhost:11434")`.

## Where to go next

- Measuring quality → `dspy-evaluation-harness`
- Automatic optimization → `dspy-gepa-optimizer`
- Context >100k tokens → `dspy-rlm-module`
- Full pipeline → `dspy-advanced-workflow`
- Full API reference → [reference.md](reference.md)
- Runnable example → [example_qa.py](example_qa.py)
