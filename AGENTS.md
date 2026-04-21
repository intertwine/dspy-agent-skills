# Repository Guidelines

## Project Structure & Module Organization

This repository packages DSPy 3.2.x agent skills for Claude Code, Codex CLI, and other agentskills.io-compatible tools. The main product lives in `skills/`: each `skills/<skill-name>/` directory contains a required `SKILL.md`, optional `reference.md`, and runnable `example_*.py` files. End-to-end validation demos live in `examples/`, with shared helpers in `examples/common/` and per-demo data under `examples/*/data/`. Tests are in `tests/`, distribution metadata is in `.claude-plugin/`, installation tooling is in `scripts/`, and contributor/user docs are in `docs/`.

## Build, Test, and Development Commands

- `uv run --with pytest python -m pytest tests/ -v` validates manifests, skill frontmatter, and example syntax.
- `for f in skills/*/example_*.py; do uv run --with dspy python "$f" --dry-run; done` smoke-tests skill examples without LM credentials.
- `./scripts/install.sh` symlinks skills into both `~/.claude/skills/` and `~/.agents/skills/`.
- `./scripts/install.sh --uninstall` removes those local installs.
- `DSPY_TASK_MODEL=openrouter/liquid/lfm-2.5-1.2b-instruct:free uv run --with dspy --with python-dotenv python examples/02-math-reasoning/run.py --optimize --auto light --seed 0` runs a live GEPA example.

If `uv run --with dspy` resolves DSPy `3.1.3`, check for a local resolver policy such as `UV_EXCLUDE_NEWER`. The exact DSPy 3.2.0 override validated in this repo is `env -u UV_EXCLUDE_NEWER uv run --with dspy==3.2.0 ...`.

## Coding Style & Naming Conventions

Use Python 3.10+ and keep examples small, readable, and dry-run capable. Prefer 4-space indentation, typed helper functions, and explicit imports. Skill directory names and `SKILL.md` frontmatter `name` values must be matching kebab-case, for example `dspy-gepa-optimizer`. Keep `SKILL.md` concise; place deeper API detail in `reference.md`.

## Testing Guidelines

Pytest is the validation framework. Add or update tests when changing manifests, metadata rules, example structure, or installer behavior. Every `skills/*/example_*.py` file must parse as Python and expose `--dry-run` so CI can validate it without API keys. Run the full pytest command before opening a PR; live GEPA runs are useful for releases but are not required for every doc-only edit.

## Commit & Pull Request Guidelines

The current history uses short imperative summaries such as `Add three end-to-end validated examples`. Keep commits focused and describe the user-visible change. PRs should include a concise summary, validation commands run, any live-model artifacts or result files changed, and links to related issues. Include screenshots only for rendered docs or marketplace UI changes.

## Security & Configuration Tips

Do not commit `.env`, API keys, DSPy caches, or generated provider credentials. Start from `.env.example`, keep `OPENROUTER_API_KEY` local, and prefer `DSPY_CACHEDIR=.cache/dspy` for reproducible local runs. See `CLAUDE.md` for deeper agent-specific authoring rules and DSPy gotchas.
