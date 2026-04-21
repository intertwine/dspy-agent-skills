---
name: dspy-rlm-module
description: Use dspy.RLM (Recursive Language Model) for reasoning over contexts too large to fit in an LLM's working window — entire codebases, long logs, massive documents, or multi-step data exploration that needs a sandboxed Python REPL. Use when the input is >100k tokens, needs recursive chunking, or benefits from the LLM writing and running code to probe data.
when_to_use: User has a very long document/codebase/log, asks about "long context", mentions RLM or recursive reasoning, or is trying to stuff a huge context into a single predictor and hitting token limits.
---

# `dspy.RLM` — Recursive Language Model

`dspy.RLM` runs the LLM in a sandboxed Python REPL (Pyodide/WASM via Deno) with access to the full context as variables. The LLM writes code to slice, grep, summarize, and recursively sub-query the data, iterating until it can answer. Use it when the context is too large to cram into a single prompt.

## Prerequisites

- **Deno installed** (for the default `PythonInterpreter`): `brew install deno` or see https://deno.land. The interpreter is a Pyodide-in-WASM sandbox spawned by Deno.
- A sub-LM for inner calls — usually a cheaper model than the outer LM. Defaults to `dspy.settings.lm`.

## Canonical usage

```python
import dspy

dspy.configure(lm=dspy.LM("openai/gpt-4o"))
sub_lm = dspy.LM("openai/gpt-4o-mini")    # cheap inner model

rlm = dspy.RLM(
    "context, query -> answer",
    max_iterations=20,
    max_llm_calls=50,
    max_output_chars=10_000,
    sub_lm=sub_lm,
    tools=[],
    verbose=False,
)

result = rlm(
    context=open("huge_log.txt").read(),   # can be 500k+ tokens
    query="Summarize every unique error class and how many times each appeared.",
)
print(result.answer)
```

## Full constructor

```python
dspy.RLM(
    signature: type[Signature] | str,
    max_iterations: int = 20,       # REPL loop cap
    max_llm_calls: int = 50,        # sub-LM call cap (stops runaway recursion)
    max_output_chars: int = 10_000, # truncate REPL stdout per step
    verbose: bool = False,          # print the REPL trace
    tools: list[Callable] | None = None,
    sub_lm: dspy.LM | None = None,
    interpreter: CodeInterpreter | None = None,  # custom sandbox
)
```

## When to reach for RLM vs. alternatives

| Situation | Use |
|---|---|
| Context <100k, answer fits one LM call | `dspy.Predict` / `dspy.ChainOfThought` |
| Need external tools (web, db) | `dspy.ReAct(tools=[...])` |
| Math/code that must run | `dspy.ProgramOfThought` |
| **Huge context, recursive chunking, or data-exploration loop** | **`dspy.RLM`** |
| Entire-codebase reasoning where the LM should grep/read files | `dspy.RLM` with file-reading `tools=[...]` |

## Composition — RLM as a module inside a larger program

Wrap the RLM in your own `dspy.Module` and optimize the enclosing program with GEPA. GEPA can tune both the RLM's outer signature instruction and the surrounding predictors.

```python
class RepoAuditor(dspy.Module):
    def __init__(self):
        super().__init__()
        self.explore = dspy.RLM("repo_tree, question -> findings",
                                max_iterations=30, sub_lm=dspy.LM("openai/gpt-4o-mini"))
        self.synth = dspy.ChainOfThought("findings, question -> report")

    def forward(self, repo_tree, question):
        f = self.explore(repo_tree=repo_tree, question=question).findings
        return self.synth(findings=f, question=question)
```

Then: `dspy.GEPA(metric=..., ...).compile(student=RepoAuditor(), trainset=..., valset=...)`.

## Practical tips

- **Budget carefully.** A single RLM call can issue dozens of sub-LM calls. Keep `max_llm_calls` tight (20–50) in production; raise for research.
- **The default stdout cap is smaller in DSPy 3.2.x.** `max_output_chars` now defaults to `10_000`; raise it deliberately if your REPL tools print large tables or document slices.
- **Use a cheap `sub_lm`.** The outer LM orchestrates; inner calls (summarize, filter, score) don't need the flagship model.
- **Pass data as kwargs, not in the instruction.** `rlm(context=huge_string, query="...")` lets the REPL treat `context` as a Python variable. Avoid concatenating it into the prompt.
- **`verbose=True` while debugging.** Prints every REPL step — invaluable when the RLM appears to hang or loop.
- **Custom tools** are regular Python callables passed via `tools=[...]`; they are exposed inside the sandbox. Useful for `read_file`, `grep`, `vector_search`, etc. In DSPy 3.2.x they are invoked by keyword, so give them named, typed parameters rather than positional-only signatures.
- **Deno install is required.** Missing Deno is the #1 RLM error. Check `which deno` before reporting bugs.

## Security note

The default interpreter is a Deno-sandboxed Pyodide WASM runtime — no filesystem, network, or subprocess access by default. If you pass custom `tools` that do I/O, your tools' security posture is yours. Never hand raw `subprocess.run` to the RLM.

## Anti-patterns

- Using RLM when a 32k-token prompt would fit — overhead is not worth it.
- Missing Deno → hard-to-diagnose failures. Install it.
- `max_llm_calls` left at default in a production path — runaway cost.
- Passing secrets in the `context` string — they get echoed into REPL state.

## Next

- Wrap-and-optimize with GEPA → `dspy-gepa-optimizer`.
- Full reference → [reference.md](reference.md).
