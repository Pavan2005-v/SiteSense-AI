"""
Test suite validating that every skill conforms to agentskills.io standard.
"""
from pathlib import Path
import yaml
import pytest

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
SKILLS_DIR = PROJECT_ROOT / "skills"


def get_skill_folders():
    folders = []
    for d in SKILLS_DIR.iterdir():
        if d.is_dir() and (d / "SKILL.md").exists():
            folders.append(d)
    return folders


@pytest.mark.parametrize("skill_folder", get_skill_folders(), ids=lambda f: f.name)
def test_skill_md_agentskills_compliance(skill_folder: Path):
    skill_md_path = skill_folder / "SKILL.md"
    assert skill_md_path.exists(), f"SKILL.md missing in {skill_folder.name}"

    content = skill_md_path.read_text(encoding="utf-8")
    
    # 1. Check YAML frontmatter presence
    assert content.startswith("---"), f"SKILL.md in {skill_folder.name} must start with YAML frontmatter delimiter '---'"
    parts = content.split("---", 2)
    assert len(parts) >= 3, f"SKILL.md in {skill_folder.name} has malformed frontmatter delimiters"

    # 2. Parse YAML
    frontmatter_raw = parts[1]
    metadata = yaml.safe_load(frontmatter_raw)
    assert isinstance(metadata, dict), f"Frontmatter in {skill_folder.name} must be a valid YAML dictionary"
    assert "name" in metadata, f"Frontmatter in {skill_folder.name} missing 'name'"
    assert "description" in metadata, f"Frontmatter in {skill_folder.name} missing 'description'"
    assert len(metadata["description"].strip()) > 20, f"Description in {skill_folder.name} is too short"

    # 3. Check mandatory sections in body
    body = parts[2]
    for required_heading in ["## When to use", "## Inputs", "## Procedure", "## Output"]:
        assert required_heading.lower() in body.lower(), (
            f"SKILL.md in {skill_folder.name} missing required section: '{required_heading}'"
        )


@pytest.mark.parametrize("skill_folder", get_skill_folders(), ids=lambda f: f.name)
def test_skill_progressive_disclosure_structure(skill_folder: Path):
    # Every skill must have references/ and scripts/ for progressive disclosure
    scripts_dir = skill_folder / "scripts"
    refs_dir = skill_folder / "references"

    assert scripts_dir.exists() and scripts_dir.is_dir(), f"Skill {skill_folder.name} missing scripts/ directory"
    assert refs_dir.exists() and refs_dir.is_dir(), f"Skill {skill_folder.name} missing references/ directory"

    script_files = list(scripts_dir.glob("*.py"))
    assert len(script_files) >= 1, f"Skill {skill_folder.name} must contain at least 1 Python script in scripts/"

    ref_files = list(refs_dir.glob("*.md"))
    assert len(ref_files) >= 1, f"Skill {skill_folder.name} must contain at least 1 reference doc in references/"

