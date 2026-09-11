"""
Test suite for marketplace.json manifest compliance.
Verifies all Adobe Round 3 rules: valid JSON, all paths exist, exactly one entrypoint.
"""
import json
from pathlib import Path
import pytest

PROJECT_ROOT = Path(__file__).parent.parent.resolve()


def test_marketplace_json_exists_and_valid():
    manifest_path = PROJECT_ROOT / "marketplace.json"
    assert manifest_path.exists(), "marketplace.json must exist at project root"

    with open(manifest_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert "name" in data, "marketplace.json must have 'name'"
    assert "version" in data, "marketplace.json must have 'version'"
    assert "skills" in data, "marketplace.json must list 'skills'"
    assert isinstance(data["skills"], list), "'skills' must be a list"
    assert len(data["skills"]) >= 4, "Must have at least 4 specialized skills"


def test_exactly_one_entrypoint():
    manifest_path = PROJECT_ROOT / "marketplace.json"
    with open(manifest_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    entrypoints = [s for s in data["skills"] if s.get("entrypoint") is True]
    assert len(entrypoints) == 1, f"Expected exactly 1 entrypoint, found {len(entrypoints)}"
    assert entrypoints[0]["id"] == "audit-orchestrator", "audit-orchestrator must be the designated entrypoint"


def test_all_skill_paths_and_skills_exist():
    manifest_path = PROJECT_ROOT / "marketplace.json"
    with open(manifest_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    for skill in data["skills"]:
        skill_id = skill["id"]
        rel_path = skill["path"]
        abs_path = PROJECT_ROOT / rel_path

        assert abs_path.exists() and abs_path.is_dir(), f"Skill directory does not exist: {rel_path}"
        skill_md = abs_path / "SKILL.md"
        assert skill_md.exists() and skill_md.is_file(), f"Missing SKILL.md for skill {skill_id} at {rel_path}"

