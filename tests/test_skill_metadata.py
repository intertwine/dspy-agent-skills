"""Validate every SKILL.md against the Claude Code / Codex agent-skills spec.

Rules enforced:
  - File is named exactly `SKILL.md` (uppercase required by Claude Code).
  - YAML frontmatter parses; `name` and `description` present.
  - `name` is kebab-case, ≤64 chars, and matches the parent directory name.
  - Combined length of `description` + optional `when_to_use` ≤1536 chars.
  - No legacy/unsupported fields (`triggers`, `version`, `dspy-compatibility`,
    `dspy-version`).

Run:
    uv run python -m pytest tests/test_skill_metadata.py -v
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO_ROOT / "skills"

SUPPORTED_FIELDS = {
    "name",
    "description",
    "when_to_use",
    "argument-hint",
    "disable-model-invocation",
    "user-invocable",
    "allowed-tools",
    "model",
    "effort",
    "context",
    "agent",
    "hooks",
    "paths",
    "shell",
}
FORBIDDEN_FIELDS = {"triggers", "version", "dspy-compatibility", "dspy-version"}

NAME_RE = re.compile(r"^[a-z][a-z0-9-]{0,63}$")
DESC_LIMIT = 1536


def _parse_frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---\n"):
        raise AssertionError("SKILL.md must start with a YAML frontmatter block '---'.")
    end = text.find("\n---\n", 4)
    assert end != -1, "Missing closing '---' for frontmatter."
    block = text[4:end]
    out: dict[str, str] = {}
    current_key: str | None = None
    buf: list[str] = []
    for line in block.splitlines():
        m = re.match(r"^([A-Za-z][A-Za-z0-9_-]*)\s*:\s*(.*)$", line)
        if m and not line.startswith(" "):
            if current_key is not None:
                out[current_key] = "\n".join(buf).strip()
            current_key = m.group(1)
            buf = [m.group(2)]
        else:
            buf.append(line)
    if current_key is not None:
        out[current_key] = "\n".join(buf).strip()
    return out


def _frontmatter_block(text: str) -> str:
    if not text.startswith("---\n"):
        raise AssertionError("SKILL.md must start with a YAML frontmatter block '---'.")
    end = text.find("\n---\n", 4)
    assert end != -1, "Missing closing '---' for frontmatter."
    return text[4:end]


def _is_inline_plain_scalar(value: str) -> bool:
    value = value.strip()
    if not value:
        return False
    if value in {">", ">-", ">+", "|", "|-", "|+"}:
        return False
    if value.startswith(("'", '"', "[", "{")):
        return False
    return True


def _skill_dirs() -> list[Path]:
    return sorted(p for p in SKILLS_DIR.iterdir() if p.is_dir())


@pytest.mark.parametrize("skill_dir", _skill_dirs(), ids=lambda p: p.name)
def test_skill_md_exists_and_uppercase(skill_dir: Path):
    md = skill_dir / "SKILL.md"
    assert md.is_file(), (
        f"{skill_dir}: SKILL.md not found (must be exactly 'SKILL.md')."
    )
    siblings = {p.name for p in skill_dir.iterdir()}
    lowercase = {"skill.md", "Skill.md", "skill.MD"} & siblings
    assert not lowercase, (
        f"{skill_dir}: found case-variant {lowercase}; Claude Code requires uppercase SKILL.md."
    )


@pytest.mark.parametrize("skill_dir", _skill_dirs(), ids=lambda p: p.name)
def test_frontmatter_valid(skill_dir: Path):
    text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
    fm = _parse_frontmatter(text)

    assert "name" in fm, f"{skill_dir}: missing `name` in frontmatter."
    assert "description" in fm, f"{skill_dir}: missing `description` in frontmatter."

    unsupported = set(fm) - SUPPORTED_FIELDS
    assert not unsupported, (
        f"{skill_dir}: unsupported frontmatter fields {unsupported}. "
        f"Supported: {sorted(SUPPORTED_FIELDS)}"
    )

    banned = set(fm) & FORBIDDEN_FIELDS
    assert not banned, (
        f"{skill_dir}: forbidden fields {banned}. These are ignored by Claude Code "
        f"and Codex — move version/compatibility to plugin.json, use `description` "
        f"instead of `triggers`."
    )


@pytest.mark.parametrize("skill_dir", _skill_dirs(), ids=lambda p: p.name)
def test_frontmatter_plain_scalars_are_yaml_safe(skill_dir: Path):
    """Guard compatibility with strict YAML frontmatter parsers.

    The `npx skills` CLI uses a real YAML parser and skips skills whose
    frontmatter cannot parse. In inline plain scalars, `: ` starts a mapping,
    so values with human prose containing colon-space need quotes or a block
    scalar.
    """

    block = _frontmatter_block((skill_dir / "SKILL.md").read_text(encoding="utf-8"))
    offenders: list[str] = []
    for line_no, line in enumerate(block.splitlines(), 2):
        if line.startswith(" "):
            continue
        m = re.match(r"^([A-Za-z][A-Za-z0-9_-]*)\s*:\s*(.*)$", line)
        if not m:
            continue
        value = m.group(2)
        if _is_inline_plain_scalar(value) and ": " in value:
            offenders.append(f"{skill_dir / 'SKILL.md'}:{line_no}: {line.strip()}")

    assert not offenders, (
        "Inline YAML frontmatter values containing `: ` must be quoted or written "
        "as block scalars for npx skills compatibility:\n  "
        + "\n  ".join(offenders)
    )


@pytest.mark.parametrize("skill_dir", _skill_dirs(), ids=lambda p: p.name)
def test_name_matches_dir_and_is_kebab(skill_dir: Path):
    fm = _parse_frontmatter((skill_dir / "SKILL.md").read_text(encoding="utf-8"))
    name = fm["name"].strip().strip('"').strip("'")
    assert NAME_RE.match(name), (
        f"{skill_dir}: name {name!r} must be kebab-case, start with a letter, "
        f"≤64 chars (spec)."
    )
    assert name == skill_dir.name, (
        f"{skill_dir}: `name` is {name!r} but directory is {skill_dir.name!r}. "
        f"They must match."
    )


@pytest.mark.parametrize("skill_dir", _skill_dirs(), ids=lambda p: p.name)
def test_reference_md_exists(skill_dir: Path):
    """Every skill should ship a reference.md for progressive disclosure."""
    ref = skill_dir / "reference.md"
    assert ref.is_file(), (
        f"{skill_dir.relative_to(REPO_ROOT)}: missing `reference.md`. Each skill "
        f"should have a reference.md alongside SKILL.md for deeper API detail."
    )


@pytest.mark.parametrize("skill_dir", _skill_dirs(), ids=lambda p: p.name)
def test_description_length(skill_dir: Path):
    fm = _parse_frontmatter((skill_dir / "SKILL.md").read_text(encoding="utf-8"))
    desc = fm["description"]
    when = fm.get("when_to_use", "")
    combined = len(desc) + len(when)
    assert combined <= DESC_LIMIT, (
        f"{skill_dir}: description ({len(desc)}) + when_to_use ({len(when)}) "
        f"= {combined} > {DESC_LIMIT}-char spec limit."
    )
    assert len(desc) >= 30, (
        f"{skill_dir}: description too short to be useful ({len(desc)} chars)."
    )
