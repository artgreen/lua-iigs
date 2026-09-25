"""Resolve organized test sources and stage a flat IIgs-compatible test directory."""
from pathlib import Path
import shutil
from .common import ROOT, BuildError


def sources():
    result = {}
    names = set()
    for group in ("upstream", "regression", "hardware"):
        for path in sorted((ROOT / "tests" / group).glob("*.lua")):
            if path.name.casefold() in names:
                raise BuildError(f"duplicate test filename: {path.name}")
            names.add(path.name.casefold())
            result[path.name] = path
    return result


def test_source(name):
    try:
        return sources()[name]
    except KeyError:
        raise BuildError(f"unknown test source: {name}") from None


def stage_sources(directory: Path):
    directory.mkdir(parents=True, exist_ok=True)
    for name, source in sources().items():
        shutil.copyfile(source, directory / name)
