# Example 03 — Typed Invoice Extraction

Extract a **Pydantic-typed** `InvoiceRecord` from unstructured invoice text — vendor, date, line items (description/quantity/unit_price), and total. The example exercises typed DSPy outputs and a multi-axis metric that rewards schema validity, field correctness, and arithmetic consistency simultaneously.

## Committed results

| Metric | Baseline | Optimized | Δ |
|---|---:|---:|---:|
| Weighted multi-axis | 0.833 | **0.931** | **+0.098** |

- **Task LM**: `openrouter/liquid/lfm-2.5-1.2b-instruct:free` (Liquid LFM 2.5, 1.2B, $0)
- **Reflection LM**: `openrouter/nvidia/nemotron-3-super-120b-a12b:free` ($0)
- **GEPA mode**: `auto="light"`, seed=0
- **Trainset**: 20 · **valset**: 9
- **Runtime**: ~36 min on free tier (exhausted OpenRouter's 2000 req/day quota at iter 24 of 25)
- **Artifact**: `optimized_program.json` (historical DSPy `3.1.3` metadata)
- **Comparison**: [`version_comparison.md`](version_comparison.md)

GEPA accepted **5 mutations** (candidate pool 6). Candidate 5 at iteration 22 landed the best full-valset aggregate of 0.931.

> **Note on the final re-eval**: OpenRouter's free-tier daily quota exhausted late in the run, so the very-last end-of-run re-evaluation couldn't execute on fresh LM calls. The baseline and optimized scores come from GEPA's own full-valset evaluations cached in `gepa_state.bin`, which are the same values GEPA uses for candidate selection — they're reliable; they just weren't re-computed after quota reset.

## DSPy 3.2.0 status

This example intentionally still ships the historical DSPy `3.1.3` artifact. The 2026-04-28 refresh reran the historical Liquid/Nemotron path from clean temporary state. The clean DSPy `3.1.3` GEPA probe found a `0.944` full-valset candidate but was interrupted at `162/416` rollouts after `28m29s`; the clean DSPy `3.2.0` baseline on the same model pair already scored `0.944`, leaving little honest headroom for a replacement optimized artifact.

Earlier DSPy `3.2.0` model sweeps also failed to produce a better artifact for one of two reasons:

| Probe | Result | Why it did not become the committed DSPy 3.2.0 artifact |
|---|---:|---|
| `openrouter/meta-llama/llama-3.2-1b-instruct` | 0.773 (reported as 77.31%) | Left headroom, but optimize produced too many malformed typed outputs and became too slow/noisy to trust |
| `openrouter/meta-llama/llama-3.2-3b-instruct` | 0.983 (reported as 98.33%) | Too saturated |
| `openrouter/google/gemma-3-4b-it` | 1.000 (reported as 100.00%) | Saturated |
| `openrouter/mistralai/ministral-3b-2512` | 1.000 (reported as 100.00%) | Saturated |
| `openrouter/mistralai/ministral-8b-2512` | 1.000 (reported as 100.00%) | Saturated |
| `openrouter/qwen/qwen3-1.7b` | unavailable | OpenRouter returned `404: No endpoints found` during validation |

That leaves the current committed artifact as the most honest release artifact for this example: reproducible, instructive, and still meaningfully non-saturated.

## Task

```
dspy.ChainOfThought("invoice_text -> record: InvoiceRecord")
```

where `InvoiceRecord` is a Pydantic model:

```python
class LineItem(BaseModel):
    description: str
    quantity: int
    unit_price: float

class InvoiceRecord(BaseModel):
    vendor: str         # seller — not buyer or shipper
    date: str           # YYYY-MM-DD
    line_items: list[LineItem]
    total: float        # final amount due (post-tax/shipping/discount)
```

Dataset (`data/{train,val}.jsonl`) includes genuinely tricky layouts: discount/rebate rows that reduce the total, seller/bill-to/shipper ambiguity in headers, varied date formats (DD-MM-YYYY, "March 8, 2024", "22 September 2024"), freight/handling lines that are NOT line items, and tax-inclusive vs pre-tax totals.

## Metric (`pipeline.py:rich_metric`)

Five-axis weighted score returning `dspy.Prediction(score, feedback)`:

| Axis | Weight | Checks |
|---|---:|---|
| Schema validity | 0.20 | Output parses as `InvoiceRecord` |
| Vendor match | 0.15 | Normalized equality (prefix-tolerant) |
| Date match | 0.15 | Exact YYYY-MM-DD |
| Line-item F1 | 0.35 | Set-F1 over (fuzzy_description, qty, unit_price) triples |
| Total match | 0.15 | Absolute delta ≤ $0.50 |

Feedback names each failing axis with specifics (e.g., *"DATE: predicted '03-05-2024', expected '2024-05-03' — YYYY-MM-DD format"*), which is what lets GEPA's reflection LM learn per-axis fixes.

## Run it

```bash
# Smoke test
env -u UV_EXCLUDE_NEWER uv run --with dspy==3.2.0 --with python-dotenv --with pydantic python examples/03-invoice-extraction/run.py --dry-run

# Historical committed baseline
DSPY_TASK_MODEL=openrouter/liquid/lfm-2.5-1.2b-instruct:free \
  env -u UV_EXCLUDE_NEWER uv run --with dspy==3.2.0 --with python-dotenv --with pydantic \
  python examples/03-invoice-extraction/run.py --baseline

# Historical committed GEPA run (~30-60 min on free tier)
DSPY_TASK_MODEL=openrouter/liquid/lfm-2.5-1.2b-instruct:free \
  env -u UV_EXCLUDE_NEWER uv run --with dspy==3.2.0 --with python-dotenv --with pydantic \
  python examples/03-invoice-extraction/run.py --optimize --auto light --seed 0
```

## Why this one still points at Liquid 1.2B

The 3.2.0 sweep reinforced the same lesson more strongly than before: invoice extraction is now easy enough that many current 3B-8B models saturate the benchmark outright. The clean Liquid rerun now shows the same issue on the historical model pair: DSPy `3.2.0` baseline alone reached `0.944`. Until the dataset gets harder or a more reliable non-saturated model target is selected, the completed historical Liquid 1.2B artifact remains the clearest demonstration of GEPA headroom on this task.

## Gotchas (patched)

Two non-obvious issues surfaced during validation; both are fixed in the committed code and worth flagging:

1. **Pydantic output signatures + `from __future__ import annotations`** → DSPy's signature builder can't resolve the `ForwardRef('InvoiceRecord')` string it receives. `pipeline.py` deliberately does NOT use the future-annotations import so DSPy sees concrete types at class-body evaluation time.
2. **GEPA state pickling with typed signatures** → stock `pickle` can't serialize the dynamic `StringSignature` subclass that DSPy generates for Pydantic outputs. Fix: `dspy.GEPA(..., gepa_kwargs={"use_cloudpickle": True})`.

## Reproducibility

`seed=0`, `auto="light"`, and the free-tier Liquid/Nemotron pair still reproduce the historical artifact in principle, though the run can hit OpenRouter's daily cap and may spend substantial time on malformed typed-output candidates. For clean cross-version probes, delete `gepa_logs/` and set a fresh `DSPY_CACHEDIR` per DSPy version; this refresh used disposable uv environments rather than `.venv-dspy313` / `.venv-dspy320`.
