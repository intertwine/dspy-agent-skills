"""Validate .claude-plugin/plugin.json and marketplace.json."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
PLUGIN_MANIFEST = REPO / ".claude-plugin" / "plugin.json"
MARKETPLACE_MANIFEST = REPO / ".claude-plugin" / "marketplace.json"

NAME_RE = re.compile(r"^[a-z][a-z0-9-]*$")


def test_plugin_manifest_exists_and_parses():
    assert PLUGIN_MANIFEST.is_file(), f"Missing {PLUGIN_MANIFEST}"
    data = json.loads(PLUGIN_MANIFEST.read_text())
    assert "name" in data, "plugin.json requires `name`"
    assert NAME_RE.match(data["name"]), (
        f"plugin name {data['name']!r} must be kebab-case"
    )
    # recommended fields present
    for k in ("version", "description", "author", "license", "keywords"):
        assert k in data, f"plugin.json recommended field missing: {k}"


def test_marketplace_manifest_exists_and_parses():
    assert MARKETPLACE_MANIFEST.is_file(), f"Missing {MARKETPLACE_MANIFEST}"
    data = json.loads(MARKETPLACE_MANIFEST.read_text())
    for req in ("name", "owner", "plugins"):
        assert req in data, f"marketplace.json requires {req!r}"
    assert NAME_RE.match(data["name"]), "marketplace name must be kebab-case"
    assert isinstance(data["owner"], dict) and "name" in data["owner"]
    assert isinstance(data["plugins"], list) and data["plugins"], (
        "plugins array must be non-empty"
    )
    for entry in data["plugins"]:
        assert "name" in entry and "source" in entry, (
            "each plugin entry needs name + source"
        )
        assert NAME_RE.match(entry["name"]), (
            f"plugin entry name {entry['name']!r} must be kebab-case"
        )


def test_plugin_name_matches_marketplace_entry():
    plugin = json.loads(PLUGIN_MANIFEST.read_text())
    market = json.loads(MARKETPLACE_MANIFEST.read_text())
    names = {p["name"] for p in market["plugins"]}
    assert plugin["name"] in names, (
        f"plugin.json name {plugin['name']!r} is not listed in marketplace.json plugins {names}"
    )


def test_version_consistent_across_manifests():
    """plugin.json, marketplace.json, and README.md must agree on the version."""
    plugin = json.loads(PLUGIN_MANIFEST.read_text())
    market = json.loads(MARKETPLACE_MANIFEST.read_text())
    readme = (REPO / "README.md").read_text()

    plugin_ver = plugin["version"]
    market_ver = market["plugins"][0]["version"]

    m = re.search(r"\*\*v(\d+\.\d+\.\d+)\*\*", readme)
    assert m, "README.md does not contain a **vX.Y.Z** version string."
    readme_ver = m.group(1)

    assert plugin_ver == market_ver, (
        f"Version mismatch: plugin.json has {plugin_ver!r}, "
        f"marketplace.json has {market_ver!r}"
    )
    assert plugin_ver == readme_ver, (
        f"Version mismatch: plugin.json has {plugin_ver!r}, "
        f"README.md has {readme_ver!r}"
    )


@pytest.mark.parametrize("path", [PLUGIN_MANIFEST, MARKETPLACE_MANIFEST])
def test_json_is_strict(path: Path):
    # Ensure no trailing commas / comments that would break strict JSON parsers.
    raw = path.read_text()
    json.loads(raw)  # strict
    assert "//" not in raw or raw.count("//") == raw.count("https://") + raw.count(
        "http://"
    ), f"{path}: looks like there are // comments — JSON must be strict."
