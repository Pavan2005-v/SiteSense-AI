"""Brand AI-Readiness and Engagement Audit Skills package."""
import sys
import importlib.util
from pathlib import Path

_SKILLS_DIR = Path(__file__).parent.resolve()

# Transparently register Python module aliases with underscores for all hyphenated skill directories
for item in _SKILLS_DIR.iterdir():
    if item.is_dir() and "-" in item.name:
        alias_name = f"skills.{item.name.replace('-', '_')}"
        init_file = item / "__init__.py"
        if not init_file.exists():
            init_file.write_text(f'"""Skill package {item.name}"""\n', encoding="utf-8")
        
        spec = importlib.util.spec_from_file_location(
            alias_name,
            str(init_file),
            submodule_search_locations=[str(item)]
        )
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            sys.modules[alias_name] = mod
            spec.loader.exec_module(mod)

