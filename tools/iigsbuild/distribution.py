"""Source distribution inventory, also usable without a Git checkout."""
from pathlib import Path

ROOT_FILES = ("README.md", "LICENSE.txt", "CHANGELOG.md", "VERSION", "Makefile",
              "local.mk.example", ".gitignore", "SOURCE-MANIFEST.json")
TREES = ("src", "examples", "docs", "tests", "tools", "packaging", ".github")
SUFFIXES = {".c", ".h", ".hpp", ".lua", ".py", ".md", ".txt", ".json", ".yml", ".yaml"}


def source_files(root: Path):
    files = {name for name in ROOT_FILES if (root / name).is_file()}
    for tree in TREES:
        files.update(str(p.relative_to(root)) for p in (root / tree).rglob("*")
                     if p.is_file() and p.suffix in SUFFIXES and "__pycache__" not in p.parts)
    return sorted(files)
