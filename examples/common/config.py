"""Shared DSPy + OpenRouter configuration for example pipelines.

Reads API key from `.env` at the repo root (never committed). Defaults to
free OpenRouter models suitable for reproducible demo runs; override with
`DSPY_TASK_MODEL` / `DSPY_REFLECTION_MODEL` env vars to use a different
provider/model without editing example code.

Example:
    from examples.common import configure_dspy, get_reflection_lm
    configure_dspy()
    reflection_lm = get_reflection_lm()
"""

from __future__ import annotations

import os
from pathlib import Path

DEFAULT_TASK_MODEL = "openrouter/z-ai/glm-4.5-air:free"
DEFAULT_REFLECTION_MODEL = "openrouter/nvidia/nemotron-3-super-120b-a12b:free"
OPENROUTER_API_BASE = "https://openrouter.ai/api/v1"


def _load_dotenv() -> None:
    """Load .env from the repo root if present. No-op if already loaded."""
    try:
        from dotenv import load_dotenv
    except ImportError:
        # Minimal fallback so examples work without python-dotenv.
        env_path = _repo_root() / ".env"
        if not env_path.is_file():
            return
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            k, v = k.strip(), v.strip().strip('"').strip("'")
            os.environ.setdefault(k, v)
        return
    load_dotenv(_repo_root() / ".env")


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def get_task_lm(model: str | None = None, **overrides):
    """Return a dspy.LM for the task model, wired to OpenRouter."""
    import dspy

    _load_dotenv()
    model = model or os.getenv("DSPY_TASK_MODEL") or DEFAULT_TASK_MODEL
    return dspy.LM(
        model,
        api_key=os.getenv("OPENROUTER_API_KEY"),
        api_base=os.getenv("OPENROUTER_API_BASE", OPENROUTER_API_BASE),
        temperature=overrides.pop("temperature", 0.0),
        max_tokens=overrides.pop("max_tokens", 2000),
        cache=overrides.pop("cache", True),
        **overrides,
    )


def get_reflection_lm(model: str | None = None, **overrides):
    """Return a dspy.LM for GEPA's reflection LM (stronger, high-temp)."""
    import dspy

    _load_dotenv()
    model = model or os.getenv("DSPY_REFLECTION_MODEL") or DEFAULT_REFLECTION_MODEL
    return dspy.LM(
        model,
        api_key=os.getenv("OPENROUTER_API_KEY"),
        api_base=os.getenv("OPENROUTER_API_BASE", OPENROUTER_API_BASE),
        temperature=overrides.pop("temperature", 1.0),
        max_tokens=overrides.pop("max_tokens", 8000),
        cache=overrides.pop("cache", True),
        **overrides,
    )


def configure_dspy(model: str | None = None, **overrides) -> "object":
    """Configure the default task LM and return it."""
    import dspy

    lm = get_task_lm(model, **overrides)
    dspy.configure(lm=lm, track_usage=True)
    return lm


def get_example_num_threads(default: int = 1) -> int:
    """Return example parallelism, overridable via env for rate-limited runs."""
    return max(1, _env_int("DSPY_EXAMPLE_NUM_THREADS", default))


def harden_example_lm(lm, default_num_retries: int = 12):
    """Apply conservative retry settings for flaky or rate-limited providers."""
    lm.num_retries = max(0, _env_int("DSPY_EXAMPLE_NUM_RETRIES", default_num_retries))
    return lm
