# `dspy.RLM` — Reference

Source: https://dspy.ai/api/modules/RLM/ (DSPy 3.2.x).

## Constructor

```python
dspy.RLM(
    signature: type[Signature] | str,
    max_iterations: int = 20,
    max_llm_calls: int = 50,
    max_output_chars: int = 10_000,
    verbose: bool = False,
    tools: list[Callable] | None = None,
    sub_lm: dspy.LM | None = None,
    interpreter: CodeInterpreter | None = None,
)
```

## Parameter reference

| Param | Default | Purpose |
|---|---|---|
| `signature` | required | Standard DSPy signature (string or class) |
| `max_iterations` | 20 | Max REPL steps before returning |
| `max_llm_calls` | 50 | Hard cap across the whole RLM invocation |
| `max_output_chars` | 10_000 | Truncates each REPL stdout blob before it reaches the LM |
| `verbose` | False | Stream thought/code/output to stdout |
| `tools` | None | Python callables exposed inside the sandbox |
| `sub_lm` | None → `dspy.settings.lm` | Model used for internal recursive calls |
| `interpreter` | None → `PythonInterpreter` | Custom `CodeInterpreter` subclass |

## Interpreter

Default is `dspy.utils.PythonInterpreter`, a Deno-hosted Pyodide WASM sandbox. Requires Deno installed (`brew install deno` / https://deno.land). The sandbox has no network or filesystem access by default.

To use a custom runtime, subclass `dspy.utils.CodeInterpreter` and implement `execute(code: str) -> str`.

## Tools

Tools are regular Python callables. DSPy introspects type hints and docstrings to expose them to the LLM. In DSPy 3.2.x, tool dispatch is kwargs-only, so use explicit named parameters:

```python
def read_file(path: str) -> str:
    """Return the full text of a file."""
    return open(path).read()

def grep(pattern: str, text: str) -> list[str]:
    """Return lines matching the regex."""
    import re
    return [l for l in text.splitlines() if re.search(pattern, l)]

rlm = dspy.RLM("repo, q -> answer", tools=[read_file, grep])
```

## Return value

Calling `rlm(...)` returns a `dspy.Prediction` with the signature's output fields. With `track_usage=True` on the outer config, `.get_lm_usage()` aggregates tokens across every inner call.

## Common failures

| Symptom | Fix |
|---|---|
| `deno: command not found` | Install Deno. |
| `RLM hit max_iterations` | Raise `max_iterations`, or narrow the query. |
| `Sub-LM call count exceeded` | Raise `max_llm_calls`; check for infinite recursion in tools. |
| `Output truncated at 10000 chars` | Raise `max_output_chars`, or have the LM sample/aggregate. |
| `KeyError` in final `.answer` | The RLM gave up; print `verbose=True` trace to see why. |
