# Example 02 — DSPy 3.1.3 vs 3.2.0

| Artifact | DSPy | Task LM | Reflection LM | Baseline | Optimized | Δ | Baseline Time | Optimize Time |
|---|---|---|---|---:|---:|---:|---:|---:|
| Historical | 3.1.3 | `openrouter/liquid/lfm-2.5-1.2b-instruct:free` | `openrouter/nvidia/nemotron-3-super-120b-a12b:free` | 45.00 | 70.00 | +25.00 | 0.2s | 1399.9s |
| Current | 3.2.0 | `openrouter/mistralai/ministral-3b-2512` | `openrouter/qwen/qwen3-30b-a3b-instruct-2507` | 85.00 | 93.33 | +8.33 | 21.9s | 210.7s |

## What changed

- The absolute optimized score improved sharply, from `70.00` to `93.33`.
- The visible GEPA delta shrank because the current paid task model starts much stronger than the historical free-tier 1.2B model.
- The refreshed DSPy `3.2.0` run was much faster and more stable than the older free-tier reproduction path.

## Caveat

This comparison is deliberately not apples-to-apples. The DSPy version changed, and the task/reflection model pair changed with it. The historical artifact is still useful if you want the "small weak model with huge GEPA lift" story; the refreshed artifact is useful if you want a current, clean DSPy `3.2.0` result.
