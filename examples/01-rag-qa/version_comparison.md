# Example 01 — DSPy 3.1.3 vs 3.2.0

| Artifact | DSPy | Task LM | Reflection LM | Baseline | Optimized | Δ | Baseline Time | Optimize Time |
|---|---|---|---|---:|---:|---:|---:|---:|
| Historical | 3.1.3 | `openrouter/z-ai/glm-4.5-air:free` | `openrouter/nvidia/nemotron-3-super-120b-a12b:free` | 81.15 | 100.00 | +18.85 | 0.2s | 1695.4s |
| Current | 3.2.0 | `openrouter/mistralai/ministral-3b-2512` | `openrouter/qwen/qwen3-30b-a3b-instruct-2507` | 75.77 | 100.00 | +24.23 | 22.8s | 839.9s |

## What changed

- The optimized score stayed perfect across both versions.
- The baseline moved down on the DSPy `3.2.0` rerun, so the visible GEPA lift grew from `+18.85` to `+24.23`.
- The run became much faster overall because the current paid model pair avoided the older free-tier rate-limit drag.

## Caveat

This is a release-refresh comparison, not an apples-to-apples benchmark. Both the task LM and reflection LM changed between the historical DSPy `3.1.3` artifact and the refreshed DSPy `3.2.0` artifact.
