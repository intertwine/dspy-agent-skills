"""Regression guards for skill doc correctness.

These rules exist because we shipped subtly wrong teaching material once
and caught it in external review. Each guard maps to a specific pitfall:

1. `.overall_score` — wrong attribute. DSPy's `EvaluationResult` uses
   `.score`. An agent that learns `.overall_score` will write code that
   raises `AttributeError` at runtime.
2. Dict-returning metrics — `dspy.Evaluate`'s parallel executor aggregates
   per-example outputs via `sum()`. A dict metric crashes with
   `TypeError: unsupported operand type(s) for +: 'int' and 'dict'`. Metrics
   must return `dspy.Prediction(score=..., feedback=...)`. The guard scans
   code-style returns AND prose mentions AND multi-line dict literals, since
   any of these will teach an agent the wrong contract.
3. Stale RLM defaults — `max_output_chars` is 10_000 in DSPy 3.2.0, not
   100_000. Any reference to the old value is a bug.
4. Stale BetterTogether API guidance — DSPy 3.2.0 uses arbitrary named
   optimizers via `dspy.BetterTogether(metric=..., bootstrap=..., gepa=...)`,
   not the older `prompt_optimizer=` / `weight_optimizer=` pair.
5. Every skill must ship a runnable `example_*.py` — `docs/usage.md` makes
   that claim, and the dry-run smoke-test loop depends on it.
6. `docs/usage.md` must list every per-skill `example_*.py` command that
   contributors are expected to keep runnable.
7. Installation docs must reflect the actual example runtime path — DSPy
   3.2.0, `OPENROUTER_API_KEY` for the end-to-end examples, and the
   `UV_EXCLUDE_NEWER` troubleshooting note we validated locally.
8. Release-status docs must not regress to claiming all committed example
   artifacts are still historical DSPy 3.1.3 runs after the 3.2 refresh.

Rule 2's regex intentionally errs on the side of false positives. To allow an
intentional anti-pattern mention, put one of the marker words (see
`_ANTIPATTERN_MARKERS`) on the same line.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
SKILLS = REPO / "skills"
DOCS = REPO / "docs"
EXAMPLE_PY_GLOB = "skills/*/example_*.py"
TEACHING_FILE_GLOBS = ("skills/**/*.md", "skills/**/*.py", "docs/*.md", "articles/*.md")

# CHANGELOG describes past state ("replaced X with Y"); linting it for
# anti-patterns would be a tautology.
TEACHING_FILE_EXCLUDES = (REPO / "docs" / "CHANGELOG.md",)


def _iter_skill_dirs() -> list[Path]:
    return sorted(p for p in SKILLS.iterdir() if p.is_dir())


def _iter_teaching_files() -> list[Path]:
    files: list[Path] = []
    for glob in TEACHING_FILE_GLOBS:
        files.extend(REPO.glob(glob))
    return sorted(set(files) - set(TEACHING_FILE_EXCLUDES))


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


# --- Shared anti-pattern markers (used by Rules 1 and 2) --------------------

_ANTIPATTERN_MARKERS = (
    "crashes",
    "anti-pattern",
    "wrong",
    "bad",
    "do not",
    "don't",
    "breaks",
    "not a dict",
    "dict)",  # e.g. "`{...}` (dict)" anti-pattern callout
    "typeerror",
    "instead of",
    "no ",  # e.g. "no `.overall_score`" — describing a prohibition
    "enforces",
)


def _is_antipattern_context(line: str) -> bool:
    lower = line.lower()
    return any(m in lower for m in _ANTIPATTERN_MARKERS)


# --- Rule 1: no `.overall_score` anywhere in teaching material -------------


def test_no_overall_score_in_teaching_material():
    """`result.overall_score` is the wrong attribute; DSPy returns `.score`."""
    offenders: list[str] = []
    for path in _iter_teaching_files():
        text = _read(path)
        for i, line in enumerate(text.splitlines(), 1):
            if "overall_score" in line and not _is_antipattern_context(line):
                offenders.append(f"{path.relative_to(REPO)}:{i}: {line.strip()}")
    assert not offenders, (
        "`.overall_score` appears in skill/docs teaching material. DSPy uses "
        "`result.score`. Offending lines:\n  " + "\n  ".join(offenders)
    )


# --- Rule 2: no dict metrics in teaching material (code, prose, multiline) -

# Patterns that indicate a dict-as-metric-return pattern is being taught.
# Each pattern is permissive on purpose — we want to catch prose like
# "return `{"score": s, "feedback": f}`" as well as source-code returns.
_DICT_METRIC_PATTERNS = [
    # Source: `return {"score": ...` on a single line
    re.compile(r"return\s*\{\s*['\"]score['\"]\s*:"),
    # Source or prose: `{"score": ..., "feedback": ...}` on a single line
    re.compile(r"\{\s*['\"]score['\"]\s*:[^}]*['\"]feedback['\"]\s*:"),
    re.compile(r"\{\s*['\"]feedback['\"]\s*:[^}]*['\"]score['\"]\s*:"),
    # Prose: "returns `{"score": float, "feedback": str}`" — catch the type-sig form
    re.compile(r"\{['\"]score['\"]\s*:\s*float\s*,\s*['\"]feedback['\"]\s*:\s*str\}"),
]


def _line_matches_dict_metric(line: str) -> bool:
    return any(pat.search(line) for pat in _DICT_METRIC_PATTERNS)


def _multiline_dict_return_spans(text: str) -> list[tuple[int, str]]:
    """Flag multi-line dict metric returns like:

        return {
            "score": ...,
            "feedback": ...,
        }

    Returns (line_number, snippet) pairs so callers can report precisely.
    """
    hits: list[tuple[int, str]] = []
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        # Opening line: `return {` with nothing past the brace on the same line
        if re.search(r"return\s*\{\s*$", lines[i]):
            # Peek the next up-to-6 lines for both "score" and "feedback" keys.
            window = "\n".join(lines[i : i + 7])
            if re.search(r"['\"]score['\"]\s*:", window) and re.search(
                r"['\"]feedback['\"]\s*:", window
            ):
                hits.append((i + 1, lines[i].strip()))
        i += 1
    return hits


@pytest.mark.parametrize(
    "path", _iter_teaching_files(), ids=lambda p: str(p.relative_to(REPO))
)
def test_no_dict_metric_guidance(path: Path):
    """Every teaching file must use `dspy.Prediction(score, feedback)`, not a dict."""
    text = _read(path)
    offenders: list[str] = []

    for i, line in enumerate(text.splitlines(), 1):
        if _line_matches_dict_metric(line) and not _is_antipattern_context(line):
            offenders.append(f"{path.relative_to(REPO)}:{i}: {line.strip()}")

    for i, snippet in _multiline_dict_return_spans(text):
        # Heuristic: if the block is immediately preceded by a heading or line
        # with an antipattern marker, allow it.
        prev_lines = "\n".join(text.splitlines()[max(0, i - 4) : i - 1])
        if _is_antipattern_context(prev_lines):
            continue
        offenders.append(f"{path.relative_to(REPO)}:{i}: {snippet} (multi-line dict)")

    assert not offenders, (
        "Dict-returning metric guidance detected. Use "
        "`dspy.Prediction(score=..., feedback=...)` — dicts crash "
        "dspy.Evaluate's parallel aggregator:\n  " + "\n  ".join(offenders)
    )


# --- Rule 3: stale RLM defaults should not appear anywhere ------------------


def test_no_stale_rlm_max_output_chars():
    """`max_output_chars` default in DSPy 3.2.0 is 10_000, not 100_000."""
    offenders: list[str] = []
    stale_patterns = (
        re.compile(r"max_output_chars\s*=\s*100_000\b"),
        re.compile(r"max_output_chars\s*=\s*100000\b"),
        re.compile(r"max_output_chars[^\n]*\|\s*100_000\s*\|"),  # table cells
        re.compile(r"max_output_chars[^\n]*\|\s*100000\s*\|"),
        re.compile(r"Output truncated at 100000 chars", re.IGNORECASE),
        re.compile(r"Output truncated at 100_000 chars", re.IGNORECASE),
    )
    for path in _iter_teaching_files():
        text = _read(path)
        for i, line in enumerate(text.splitlines(), 1):
            for pat in stale_patterns:
                if pat.search(line):
                    offenders.append(f"{path.relative_to(REPO)}:{i}: {line.strip()}")
                    break
    assert not offenders, (
        "Stale `max_output_chars` default detected. DSPy 3.2.0 uses 10_000:\n  "
        + "\n  ".join(offenders)
    )


# --- Rule 4: no stale BetterTogether API guidance ---------------------------


def _multiline_bettertogether_legacy_spans(text: str) -> list[tuple[int, str]]:
    """Flag legacy BetterTogether calls that use the pre-3.2.0 argument names."""
    hits: list[tuple[int, str]] = []
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if "BetterTogether(" not in line:
            continue
        window = "\n".join(lines[i : i + 8])
        if re.search(r"\bprompt_optimizer\s*=", window) or re.search(
            r"\bweight_optimizer\s*=", window
        ):
            hits.append((i + 1, line.strip()))
    return hits


@pytest.mark.parametrize(
    "path", _iter_teaching_files(), ids=lambda p: str(p.relative_to(REPO))
)
def test_no_stale_bettertogether_api(path: Path):
    """DSPy 3.2.x BetterTogether uses named `**optimizers`, not the old 2-slot API."""
    text = _read(path)
    offenders: list[str] = []

    for i, line in enumerate(text.splitlines(), 1):
        if "BetterTogether(" in line and (
            "prompt_optimizer=" in line or "weight_optimizer=" in line
        ):
            offenders.append(f"{path.relative_to(REPO)}:{i}: {line.strip()}")

    for i, snippet in _multiline_bettertogether_legacy_spans(text):
        offenders.append(
            f"{path.relative_to(REPO)}:{i}: {snippet} (legacy BetterTogether API)"
        )

    assert not offenders, (
        "Stale BetterTogether API guidance detected. DSPy 3.2.x uses "
        "`dspy.BetterTogether(metric=..., <name>=optimizer, ...)` with strategy "
        "strings, not `prompt_optimizer=` / `weight_optimizer=`:\n  "
        + "\n  ".join(offenders)
    )


# --- Rule 5: every skill ships a runnable example with --dry-run -----------


@pytest.mark.parametrize("skill_dir", _iter_skill_dirs(), ids=lambda p: p.name)
def test_every_skill_has_example(skill_dir: Path):
    """Every skill directory must ship a runnable example_*.py."""
    examples = list(skill_dir.glob("example_*.py"))
    assert examples, (
        f"{skill_dir.relative_to(REPO)}: no `example_*.py` found. Every skill "
        f"must ship a runnable smoke test (see `docs/usage.md`)."
    )
    for ex in examples:
        assert "--dry-run" in ex.read_text(), (
            f"{ex.relative_to(REPO)}: example must support `--dry-run` so it "
            f"can be smoke-tested offline."
        )


# --- Rule 6: docs/usage.md's example command list must mention every skill -


def test_usage_doc_lists_every_skill_example():
    """`docs/usage.md` lists the per-skill example commands; no skill should be missing."""
    usage = _read(DOCS / "usage.md")
    missing: list[str] = []
    for skill_dir in _iter_skill_dirs():
        # Each skill's example filename should appear in the usage doc.
        for ex in skill_dir.glob("example_*.py"):
            if ex.name not in usage:
                missing.append(f"{skill_dir.name}/{ex.name}")
    assert not missing, (
        "`docs/usage.md` does not list these example scripts: " + ", ".join(missing)
    )


# --- Rule 7: installation docs must match the repo's real example runtime ---


def test_installation_doc_matches_example_runtime():
    """The install guide should point example runners at DSPy 3.2.0 + OpenRouter."""
    text = _read(DOCS / "installation.md")
    assert "dspy-ai>=3.1.0" not in text, (
        "`docs/installation.md` still mentions the stale `dspy-ai>=3.1.0` "
        "example runtime requirement."
    )
    assert "OPENROUTER_API_KEY" in text, (
        "`docs/installation.md` should mention `OPENROUTER_API_KEY` for the "
        "end-to-end examples under `examples/`."
    )
    assert ('"dspy==3.2.0"' in text or "`dspy==3.2.0`" in text or "pip install dspy" in text), (
        "`docs/installation.md` should show the tested DSPy 3.2.0 install path."
    )
    assert "UV_EXCLUDE_NEWER" in text, (
        "`docs/installation.md` should document the `UV_EXCLUDE_NEWER` gotcha "
        "that can hide DSPy 3.2.0 from `uv run --with dspy`."
    )


# --- Rule 8: release status docs must not claim all examples are still 3.1.3 -


def test_example_status_docs_reflect_the_3_2_refresh():
    """README docs should not claim every committed example artifact is still historical."""
    checks = {
        REPO / "README.md": (
            re.compile(r"all .*example.*artifacts.*3\.1\.3", re.IGNORECASE),
            re.compile(
                r"full live re-benchmarking is the next release follow-up",
                re.IGNORECASE,
            ),
        ),
        REPO / "examples" / "README.md": (
            re.compile(
                r"keeps .*live results as historical artifacts",
                re.IGNORECASE,
            ),
        ),
    }

    offenders: list[str] = []
    for path, stale_patterns in checks.items():
        text = _read(path)
        for pattern in stale_patterns:
            if pattern.search(text):
                offenders.append(
                    f"{path.relative_to(REPO)}: matches stale-status pattern `{pattern.pattern}`"
                )

    assert not offenders, (
        "Release-status docs still describe the old pre-refresh example state:\n  "
        + "\n  ".join(offenders)
    )
