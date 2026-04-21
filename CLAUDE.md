# CLAUDE.md

Guidance for Claude Code (or any agent) working inside this repo.

## What this repo is

A pack of five agent skills that teaches coding agents to build, optimize, and ship DSPy 3.2.x programs. It is designed to install cleanly into both **Claude Code** (`~/.claude/skills/`) and **Codex CLI** (`~/.agents/skills/`).

The skills themselves are in `skills/<name>/SKILL.md`. The product is Markdown; Python files in `skills/*/example_*.py` are runnable smoke tests, not library code.

## Repo layout

```
.claude-plugin/    # plugin.json + marketplace.json for Claude Code distribution
skills/            # 5 skills; each dir has SKILL.md + reference.md + example_*.py
scripts/           # install.sh (dual-target installer)
tests/             # pytest validators for SKILL.md spec, JSON manifests, example AST
docs/              # installation.md, usage.md, CHANGELOG.md
```

## Commands you'll actually run

```bash
# Validate all skill metadata, manifests, example syntax, and skill-doc correctness (80+ tests)
uv run --with pytest python -m pytest tests/ -v

# Smoke-test every example offline (no API key needed)
for f in skills/*/example_*.py; do uv run --with dspy python "$f" --dry-run; done

# Install skills locally into Claude Code and Codex (symlinks, idempotent)
./scripts/install.sh

# Uninstall
./scripts/install.sh --uninstall

# Live GEPA run (requires OPENAI_API_KEY)
cd skills/dspy-advanced-workflow
OPENAI_API_KEY=... uv run --with dspy python example_pipeline.py --auto light
```

If `uv run --with dspy` unexpectedly resolves DSPy `3.1.3`, check for `UV_EXCLUDE_NEWER` or another resolver policy that hides recent uploads. For an exact DSPy 3.2.0 validation run, use:

```bash
env -u UV_EXCLUDE_NEWER uv run --with dspy==3.2.0 python -c 'import dspy; print(dspy.__version__)'
```

## Authoring / editing conventions

### SKILL.md frontmatter — spec-only fields

Claude Code and Codex both follow the agentskills.io spec. Only these fields are honored in `SKILL.md` frontmatter:

- `name` (required, kebab-case, ≤64 chars, must equal the parent directory name)
- `description` (required; combined with `when_to_use` must stay ≤1536 chars)
- `when_to_use`, `argument-hint`, `disable-model-invocation`, `user-invocable`,
  `allowed-tools`, `model`, `effort`, `context`, `agent`, `hooks`, `paths`, `shell`

**Do NOT add** `triggers`, `version`, `dspy-compatibility`, or `dspy-version`. These are silently ignored by the harness and are rejected by `tests/test_skill_metadata.py`. Version lives in `.claude-plugin/plugin.json`.

Filename must be exactly `SKILL.md` (uppercase).

### Progressive disclosure

Keep `SKILL.md` focused and under ~500 lines. Push deep API detail into `reference.md` and reference it from the skill body. Runnable examples go in `example_*.py` with a `--dry-run` flag.

### Grounding claims

Every DSPy API claim must be verifiable against https://dspy.ai/ for DSPy 3.2.x. If you update a signature or parameter, re-check the docs and update `reference.md` in lockstep.

### When adding a new skill

1. Create `skills/<new-name>/SKILL.md` with spec-compliant frontmatter.
2. Add `reference.md` for the longer-form API detail.
3. Add at least one `example_*.py` with a `--dry-run` path that constructs the relevant DSPy objects without calling an LM.
4. Run `uv run --with pytest python -m pytest tests/ -v` — all 80+ tests must pass. Frontmatter, correctness, and docs-completeness guards will catch drift automatically.
5. Update the skill table in `README.md` and `docs/usage.md`.
6. Bump `version` in `.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json`.
7. Add a `docs/CHANGELOG.md` entry describing what changed and why.

### When fixing a bug

Per the project-wide policy: grep for the same anti-pattern across all skills. If one SKILL.md has a wrong import path, others likely do too.

## Gotchas

- **`dspy.GEPA` asserts `reflection_lm is not None` at construction time**, not compile time. Dry-run code paths must construct a stub `dspy.LM(...)` (no network call on construction).
- **`dspy.RLM` needs Deno** for its default Pyodide/WASM interpreter.
- **`SKILL.md` case is enforced** — `skill.md` or `Skill.md` won't be loaded by Claude Code.
- **Plugin vs. skill metadata**: version/author metadata belongs in `.claude-plugin/plugin.json`, not in individual `SKILL.md` files.
- **Symlink install** (`./scripts/install.sh`) means edits in this repo appear live in the installed skills — great for iteration, but means a broken edit immediately breaks the agent's skill invocation.

## Testing philosophy

The validators in `tests/` are the guardrail — they enforce the skill spec so that frontmatter drift doesn't silently break agent discovery. Run them before committing. Live DSPy runs are optional and token-expensive; the `--dry-run` paths are the default smoke test.

## References

- DSPy: https://dspy.ai/
- Claude Code skills: https://code.claude.com/docs/en/skills.md
- Claude Code plugin spec: https://code.claude.com/docs/en/plugins-reference.md
- Codex skills: https://developers.openai.com/codex/skills
- CHANGELOG (corrections vs. the original draft): [docs/CHANGELOG.md](docs/CHANGELOG.md)
