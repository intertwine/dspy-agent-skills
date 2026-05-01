# Example 03 — clean DSPy 3.1.3 vs 3.2.0 probe

This refresh did **not** replace the committed invoice extraction artifact. The completed historical artifact remains the honest demonstration artifact; the clean 2026-04-28 rerun showed that the current baseline is already high and that full GEPA optimization is still dominated by typed-output reliability.

| Run | DSPy | Task LM | Reflection LM | Baseline | Best observed optimized | Status |
|---|---|---|---|---:|---:|---|
| Historical committed artifact | 3.1.3 | `openrouter/liquid/lfm-2.5-1.2b-instruct:free` | `openrouter/nvidia/nemotron-3-super-120b-a12b:free` | 0.833 | 0.931 | Complete committed artifact |
| Clean GEPA probe | 3.1.3 | `openrouter/liquid/lfm-2.5-1.2b-instruct:free` | `openrouter/nvidia/nemotron-3-super-120b-a12b:free` | 0.739 | 0.944 | Interrupted at 162/416 rollouts after 28m29s |
| Clean baseline | 3.2.0 | `openrouter/liquid/lfm-2.5-1.2b-instruct:free` | `openrouter/nvidia/nemotron-3-super-120b-a12b:free` | 0.944 | n/a | Baseline only |

## Run isolation

- Temporary worktree: `<temp workspace>/repo`
- DSPy 3.1.3 cache: `<temp workspace>/repo/.cache-invoice-313`
- DSPy 3.2.0 cache: `<temp workspace>/repo/.cache-invoice-320-baseline`
- GEPA state: `examples/03-invoice-extraction/gepa_logs` deleted before each run

The clean DSPy `3.1.3` probe found a `0.944` full-valset candidate at iteration 1, then continued spending budget on malformed typed-output variants. The run was stopped rather than promoted as an incomplete compile result.

The clean DSPy `3.2.0` baseline on the same historical Liquid/Nemotron pair scored `0.944` in `33.2s`, which matches the best full-valset score seen in the interrupted 3.1.3 optimize probe. That leaves little useful headroom for a replacement GEPA artifact on this tiny validation set, so `optimized_program.json` remains the completed historical DSPy `3.1.3` artifact.
