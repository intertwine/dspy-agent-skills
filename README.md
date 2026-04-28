# DSPy Agent Skills

[![DSPy 3.2.x](https://img.shields.io/badge/DSPy-3.2.x-0A7B83)](https://dspy.ai/)

**Production-grade DSPy 3.2.x skills for coding agents.** A synthesized, spec-compliant pack of five agent skills that turns Claude Code, Codex CLI, and any other [agentskills.io](https://agentskills.io)-compatible agent into a DSPy expert.

- ✅ Validated against DSPy 3.2.0 (the real API, not inferred from stale docs)
- ✅ Single source of truth for both **Claude Code** and **Codex CLI**
- ✅ Progressive disclosure (short `SKILL.md` + deep `reference.md`)
- ✅ Runnable `example_*.py` scripts with offline `--dry-run`
- ✅ Includes a DSPy 3.2.0 `BetterTogether` chaining example
- ✅ Plugin manifest + marketplace manifest for one-click install
- ✅ 80 validation tests (frontmatter spec, JSON schema, Python AST, skill-doc correctness guards)

## What's inside

| Skill | When it auto-invokes |
|---|---|
| [`dspy-fundamentals`](skills/dspy-fundamentals/SKILL.md) | Any new DSPy code: Signatures, Modules, Predict/ChainOfThought/ReAct, save/load |
| [`dspy-evaluation-harness`](skills/dspy-evaluation-harness/SKILL.md) | Writing metrics, splitting dev/val sets, calling `dspy.Evaluate` |
| [`dspy-gepa-optimizer`](skills/dspy-gepa-optimizer/SKILL.md) | Optimizing/compiling DSPy programs with `dspy.GEPA` |
| [`dspy-rlm-module`](skills/dspy-rlm-module/SKILL.md) | Long context, codebase QA, recursive exploration via `dspy.RLM` |
| [`dspy-advanced-workflow`](skills/dspy-advanced-workflow/SKILL.md) | End-to-end builds — orchestrates the other four |

## Install

### Claude Code (via marketplace)

```text
/plugin marketplace add intertwine/dspy-agent-skills
/plugin install dspy-agent-skills@dspy-agent-skills
```

### Agent Skills CLI (`npx skills`)

```bash
npx skills add intertwine/dspy-agent-skills --list
npx skills add intertwine/dspy-agent-skills --skill '*' -a codex -y
```

The Vercel `skills` CLI currently expects a GitHub `owner/repo`, URL, well-known HTTPS endpoint, or local path as its source. The bare form `npx skills add dspy-agent-skills` is not resolvable unless the upstream CLI adds a source alias, so use `intertwine/dspy-agent-skills`.

### Claude Code + Codex (repo checkout)

```bash
git clone https://github.com/intertwine/dspy-agent-skills
cd dspy-agent-skills
./scripts/install.sh           # symlinks into ~/.claude/skills/ and ~/.agents/skills/
```

Flags: `--claude-only`, `--codex-only`, `--copy` (copy instead of symlink), `--uninstall`, `--dry-run`.

### Manual

Drop `skills/*` into `~/.claude/skills/` (Claude Code) or `~/.agents/skills/` (Codex CLI). See [docs/installation.md](docs/installation.md) for all options.

## Five-second demo

In your agent, say:

> "Build a DSPy sentiment classifier, optimize it with GEPA, and save the artifact."

The agent auto-loads `dspy-advanced-workflow`, which chains the other skills and outputs a full baseline → GEPA → export pipeline. No further prompting needed.

## End-to-end examples (current committed artifacts)

Three runnable demos under [`examples/`](examples/) exercise every skill against real LMs and ship with **committed baseline vs. GEPA-optimized numbers** plus explicit `3.1.3` vs. `3.2.0` comparison notes.

| Example | Artifact DSPy | Task LM | Baseline | Optimized | Δ | Status |
|---|---|---|---:|---:|---:|---|
| [01-rag-qa](examples/01-rag-qa/) | 3.2.0 | Ministral 3B 2512 | 75.77 | **100.00** | **+24.23** | Refreshed on 2026-04-21 |
| [02-math-reasoning](examples/02-math-reasoning/) | 3.2.0 | Ministral 3B 2512 | 85.00 | **93.33** | **+8.33** | Refreshed on 2026-04-21 |
| [03-invoice-extraction](examples/03-invoice-extraction/) | 3.1.3 | Liquid LFM 2.5 1.2B (free) | 0.833 | **0.931** | **+0.098** | Historical artifact retained |

The refreshed `01` and `02` artifacts use the paid pair `openrouter/mistralai/ministral-3b-2512` + `openrouter/qwen/qwen3-30b-a3b-instruct-2507`. `03` stays on its historical DSPy `3.1.3` artifact because the DSPy `3.2.0` probe sweep either saturated immediately (`gemma-3-4b-it`, `ministral-3b-2512`, `ministral-8b-2512`) or became too noisy to trust for typed extraction (`llama-3.2-1b-instruct`). See [`examples/README.md`](examples/README.md) and each example's `version_comparison.md` for the exact commands and caveats.

## Grounding

Every API claim is grounded in:

- https://dspy.ai/ (official docs, DSPy 3.2.x)
- https://code.claude.com/docs/en/skills.md (Claude Code skill spec)
- https://developers.openai.com/codex/skills (Codex skill spec)

## Development

```bash
# Run validation suite
uv run --with pytest python -m pytest tests/ -v

# Smoke-test every example offline (no API key needed)
for f in skills/*/example_*.py; do uv run --with dspy python "$f" --dry-run; done

# Live GEPA run (requires OPENAI_API_KEY)
cd skills/dspy-advanced-workflow
OPENAI_API_KEY=... uv run --with dspy python example_pipeline.py --auto light
```

If `uv run --with dspy` resolves DSPy `3.1.3` instead of `3.2.0`, check whether `UV_EXCLUDE_NEWER` or a stale package mirror is hiding the new release. The exact 3.2.0 override we validated for this repo is:

```bash
env -u UV_EXCLUDE_NEWER uv run --with dspy==3.2.0 python -c 'import dspy; print(dspy.__version__)'
```

## Compatibility

- **DSPy**: 3.2.x (tested against 3.2.0)
- **Claude Code**: current (skill spec as of 2026-04-17)
- **Codex CLI**: current Agent Skills format
- **Python**: 3.10+
- **Deno**: required only for `dspy.RLM` examples (Pyodide sandbox)

## Layout

```
dspy-agent-skills/
├── .claude-plugin/
│   ├── plugin.json
│   └── marketplace.json
├── skills/
│   ├── dspy-fundamentals/{SKILL.md, reference.md, example_qa.py}
│   ├── dspy-evaluation-harness/{SKILL.md, reference.md, example_metric.py}
│   ├── dspy-gepa-optimizer/{SKILL.md, reference.md, example_gepa.py}
│   ├── dspy-rlm-module/{SKILL.md, reference.md, example_rlm.py}
│   └── dspy-advanced-workflow/{SKILL.md, example_pipeline.py}
├── scripts/install.sh           # dual-target installer
├── tests/                       # spec validators
├── docs/{installation,usage,CHANGELOG}.md
├── README.md  LICENSE  .gitignore
```

## Version

**v0.2.1** • Targets DSPy 3.2.x

## License

MIT — see [LICENSE](LICENSE).

## Credits

Draft contributors: Bryan Young ([@intertwine](https://github.com/intertwine)) with Grok (xAI).
Validation, spec-alignment, and dual-agent packaging: Claude Opus 4.7, April 2026.
