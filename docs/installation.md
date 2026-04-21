# Installation

Three installation paths, from easiest to most manual. All of them install the same 5 skills.

## 1. Claude Code: plugin marketplace (recommended)

From inside Claude Code:

```text
/plugin marketplace add intertwine/dspy-agent-skills
/plugin install dspy-agent-skills@dspy-agent-skills
```

The marketplace manifest lives at `.claude-plugin/marketplace.json` and the plugin at `.claude-plugin/plugin.json`. Claude Code caches the plugin under `~/.claude/plugins/cache/<marketplace>/<plugin>/<version>/` and enables it in the current project scope.

## 2. Both Claude Code and Codex: `install.sh`

Clone the repo and run the installer. Symlink mode (default) is idempotent and forwards repo edits live:

```bash
git clone https://github.com/intertwine/dspy-agent-skills
cd dspy-agent-skills
./scripts/install.sh                  # both Claude + Codex, symlinks
./scripts/install.sh --claude-only    # just Claude Code (~/.claude/skills/)
./scripts/install.sh --codex-only     # just Codex (~/.agents/skills/)
./scripts/install.sh --copy           # copy instead of symlink
./scripts/install.sh --uninstall      # remove all skills from both destinations
./scripts/install.sh --dry-run        # show what would happen
```

Restart your agent (or `/reload` in Claude Code) after installing. Skills are discovered by scanning `~/.claude/skills/` (Claude) and `~/.agents/skills/` (Codex) for any directory containing a `SKILL.md`.

## 3. Manual

### Claude Code

```bash
cp -R skills/* ~/.claude/skills/
# or per-project:
mkdir -p .claude/skills && cp -R skills/* .claude/skills/
```

### Codex CLI

```bash
cp -R skills/* ~/.agents/skills/
# or per-repo:
mkdir -p .agents/skills && cp -R skills/* .agents/skills/
```

Codex also scans `.agents/skills/` walking up from cwd to repo root, so project-scoped installs work.

## Verifying the install

```bash
# Claude Code
ls -la ~/.claude/skills/ | grep dspy-
# Codex
ls -la ~/.agents/skills/ | grep dspy-
```

In Claude Code, the auto-invocation test:

> "Use dspy to build a simple QA program."

The agent should pull in `dspy-fundamentals` automatically and mention it by name.

In Codex, invoke explicitly with `$dspy-fundamentals` or let the description match auto-select it.

## Requirements

- **For the skills themselves**: nothing beyond Claude Code or Codex CLI.
- **For running the end-to-end examples under `examples/`**: Python 3.10+, `uv` or `pip`, DSPy `3.2.0`, `python-dotenv`, task-specific extras like `rank-bm25`/`pydantic`, and an `OPENROUTER_API_KEY` loaded from `.env`.
- **For running the smaller skill-local `example_*.py` smoke tests**: any LM provider that matches the example's `--model` string is fine (for example `OPENAI_API_KEY` with `openai/...` models).
- **For the `dspy-rlm-module` examples**: [Deno](https://deno.land) installed (required by DSPy's default PythonInterpreter / Pyodide WASM sandbox).

## Reproducing the tested DSPy 3.2.0 environment

The official DSPy install remains:

```bash
python -m pip install "dspy==3.2.0"
```

If you prefer `uv`, the exact command path we validated for this repo's example runs is:

```bash
env -u UV_EXCLUDE_NEWER uv run --with dspy==3.2.0 --with python-dotenv python -c 'import dspy; print(dspy.__version__)'
```

Why the extra prefix? On this repo's April 21, 2026 DSPy 3.2.0 refresh, the local machine had `UV_EXCLUDE_NEWER=7 days` set globally. That made `uv run --with dspy` resolve DSPy `3.1.3` even though PyPI already had `3.2.0`. If your `uv` commands unexpectedly resolve an older DSPy:

- unset `UV_EXCLUDE_NEWER` for that command, as above
- or wait until the exclude-newer window passes
- or fall back to `python -m pip install "dspy==3.2.0"` in a local virtualenv

## Upgrading

With the marketplace install: `/plugin update dspy-agent-skills`.

With `install.sh --link`: `git pull` is enough; symlinks see the new content immediately.

With `--copy` or manual install: re-run the installer or `cp -R` again.
