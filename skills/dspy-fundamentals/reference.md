# DSPy Fundamentals — API Reference

Extended detail for `dspy-fundamentals`. Source: https://dspy.ai/api/ (DSPy 3.2.x, April 2026).

## `dspy.configure`

```python
dspy.configure(
    lm: dspy.BaseLM | None = None,
    track_usage: bool = False,
    async_max_workers: int = 8,
    adapter: dspy.Adapter | None = None,  # ChatAdapter / JSONAdapter / XMLAdapter
    callbacks: list[dspy.callbacks.BaseCallback] | None = None,
    warn_on_type_mismatch: bool = True,
)
```

Sets thread-local defaults. Use `dspy.context(...)` as a `with`-block to scope overrides.

## `dspy.LM`

```python
dspy.LM(
    model: str,                    # "provider/model-name"
    model_type: Literal["chat", "text", "responses"] = "chat",
    api_key: str | None = None,
    api_base: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
    cache: bool = True,
    callbacks: list[BaseCallback] | None = None,
    num_retries: int = 3,
    provider: dspy.Provider | None = None,
    finetuning_model: str | None = None,
    launch_kwargs: dict | None = None,
    train_kwargs: dict | None = None,
    use_developer_role: bool = False,
    **kwargs,                      # forwarded to the provider backend
)
```

`.copy(rollout_id=n)` creates a deterministic variant that bypasses cache collisions.

## `dspy.Signature`

Two forms:

**String shorthand**: `dspy.Predict("question -> answer")`, `dspy.Predict("context, question -> answer: str")`.

**Class form** (preferred for production):

```python
class Sig(dspy.Signature):
    """Instruction string (docstring becomes the LM instruction)."""
    in_field: str = dspy.InputField(desc="optional field description")
    out_field: MyPydanticType = dspy.OutputField(desc="...")
```

Fields support any serializable type including Pydantic models, `list[T]`, `dict[K, V]`, `Literal[...]`.

In DSPy 3.2.0, `prefix=`, `format=`, and `parser=` on `InputField` / `OutputField` are deprecated no-ops. Use `desc=` plus real Python types instead.

## Predictor constructors

| Class | Signature |
|---|---|
| `dspy.Predict` | `Predict(signature, callbacks=None, **config)` |
| `dspy.ChainOfThought` | `ChainOfThought(signature, rationale_field=None, rationale_field_type=str, **config)` |
| `dspy.ReAct` | `ReAct(signature: type[Signature], tools: list[Callable], max_iters: int = 20)` |
| `dspy.ProgramOfThought` | `ProgramOfThought(signature, max_iters: int = 3, interpreter: PythonInterpreter \| None = None)` |
| `dspy.RLM` | `RLM(signature, max_iterations=20, max_llm_calls=50, max_output_chars=10_000, verbose=False, tools=None, sub_lm=None, interpreter=None)` |

## `dspy.Module`

Base class. Override `forward(self, **kwargs) -> dspy.Prediction`. Key methods:

- `.named_predictors()` → iterator of `(name, Predict)` — used by optimizers.
- `.dump_state()` / `.load_state(state)` — in-memory.
- `.save(path, save_program=False)` / `.load(path)` — JSON state.
- `.save(dir, save_program=True)` then `dspy.load(dir)` — full program via cloudpickle.
- `.inspect_history(n=1)` — print last N LM calls.
- `.get_lm()` — the module's LM (falls back to `dspy.settings.lm`).
- `.batch(examples, num_threads=8)` — parallel execution.

## Custom LM backends (3.2.0+)

If `dspy.LM("provider/model")` is not enough, subclass `dspy.BaseLM`.

```python
class MyLM(dspy.BaseLM):
    @property
    def supports_function_calling(self) -> bool:
        return False

    @property
    def supports_reasoning(self) -> bool:
        return False

    @property
    def supports_response_schema(self) -> bool:
        return False

    @property
    def supported_params(self) -> set[str]:
        return set()

    def forward(self, prompt=None, messages=None, **kwargs):
        ...
```

In 3.2.0, DSPy's adapters read those capability properties directly from `BaseLM`, which makes custom backends less coupled to LiteLLM internals. If your provider throws a context-window exception, translate it to `dspy.ContextWindowExceededError(model=self.model, message=...)` so DSPy's retry/truncation logic can respond correctly.

## Adapters

Controls how signatures serialize to/from the LM:

- `dspy.ChatAdapter` (default) — JSON-in-markdown with section headers.
- `dspy.JSONAdapter` — strict JSON I/O; best for tool-calling models.
- `dspy.XMLAdapter` — XML-tagged fields; good for Claude models with complex structures.

Set via `dspy.configure(adapter=dspy.JSONAdapter())`.

## Common pitfalls (from https://dspy.ai/faqs/)

1. **Context-too-long after optimization** — too many bootstrapped demos. Reduce `max_bootstrapped_demos` or passage count.
2. **Cache churn on serverless** — set `DSPY_CACHEDIR` env var.
3. **Freeze compiled modules** — after multi-stage optimization, set `module._compiled = True` to prevent further tuning.
4. **Vertex AI prefix** — use `vertex_ai/` (not `gemini/`), and `vertex_project` + `vertex_location` kwargs.
5. **`track_usage=True` costs memory** — disable in high-QPS production if not needed.
