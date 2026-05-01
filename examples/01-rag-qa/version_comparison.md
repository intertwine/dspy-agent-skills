# Example 01 — clean DSPy 3.1.3 vs 3.2.0

Both rows below were regenerated on 2026-04-28 from a temporary clean repo copy, with a separate empty DSPy cache per version and `examples/01-rag-qa/gepa_logs` removed before each run.

| DSPy | Task LM | Reflection LM | Baseline | Optimized | Delta | Baseline Time | Optimize Time |
|---|---|---|---:|---:|---:|---:|---:|
| 3.1.3 | `openrouter/mistralai/ministral-3b-2512` | `openrouter/qwen/qwen3-30b-a3b-instruct-2507` | 86.10 | 91.75 | +5.65 | 11.6s | 906.0s |
| 3.2.0 | `openrouter/mistralai/ministral-3b-2512` | `openrouter/qwen/qwen3-30b-a3b-instruct-2507` | 80.47 | 100.00 | +19.53 | 12.6s | 829.4s |

## Run isolation

- Temporary worktree: `/tmp/dspy-refresh.OFDQCq/repo`
- DSPy 3.1.3 cache: `/tmp/dspy-refresh.OFDQCq/repo/.cache-rag-313`
- DSPy 3.2.0 cache: `/tmp/dspy-refresh.OFDQCq/repo/.cache-rag-320`
- GEPA state: `examples/01-rag-qa/gepa_logs` deleted before each run

The committed `optimized_program.json` remains the DSPy `3.2.0` artifact. The temporary DSPy `3.1.3` optimized program was used only for this comparison and was not copied back into the repo.
