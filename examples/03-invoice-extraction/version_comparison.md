# Example 03 — DSPy 3.2.0 probe status

| Committed Artifact | DSPy | Task LM | Reflection LM | Baseline | Optimized | Δ | Status |
|---|---|---|---|---:|---:|---:|---|
| Historical | 3.1.3 | `openrouter/liquid/lfm-2.5-1.2b-instruct:free` | `openrouter/nvidia/nemotron-3-super-120b-a12b:free` | 0.833 | 0.931 | +0.098 | Still committed |

## DSPy 3.2.0 probe sweep

| Probe | Result | Outcome |
|---|---:|---|
| `openrouter/meta-llama/llama-3.2-1b-instruct` | 0.773 (reported as 77.31%) | Left headroom, but optimize became too noisy and malformed on typed outputs to trust as a release artifact |
| `openrouter/meta-llama/llama-3.2-3b-instruct` | 0.983 (reported as 98.33%) | Too saturated |
| `openrouter/google/gemma-3-4b-it` | 1.000 (reported as 100.00%) | Saturated |
| `openrouter/mistralai/ministral-3b-2512` | 1.000 (reported as 100.00%) | Saturated |
| `openrouter/mistralai/ministral-8b-2512` | 1.000 (reported as 100.00%) | Saturated |
| `openrouter/qwen/qwen3-1.7b` | unavailable | OpenRouter returned `404: No endpoints found` during validation |

The probe table normalizes the DSPy `3.2.0` console percentages back onto the same 0-1 scale used by the historical committed artifact.

## Decision

No credible DSPy `3.2.0` optimize rerun landed for this example, so the release keeps the historical DSPy `3.1.3` artifact and records the sweep results instead. That is more honest than overwriting the example with a saturated benchmark or a malformed typed-output run.
