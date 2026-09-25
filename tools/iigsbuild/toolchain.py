"""Tool discovery and toolchain identity.

Lookup order for the ORCA/C SDK (GoldenGate root):
  1. --sdk / GOLDEN_GATE (the Makefile exports GOLDEN_GATE from local.mk)
  2. <repository>/.orca-sdk-2.2.1
  3. .orca-sdk-2.2.1 in the primary Git worktree (for linked worktrees)
The system /Library/GoldenGate install is never selected implicitly: it
has carried ORCA/C 2.1.0, which cannot compile this source.

Other tools come from IIX / ACX / CP2 / NULIB2, then PATH, then ~/.local/bin.
Machine-specific paths belong in the untracked local.mk (see local.mk.example).
"""
from __future__ import annotations

from dataclasses import dataclass, field
import os
from pathlib import Path
import re
import shutil
import subprocess
from typing import Dict, Optional

from .common import ROOT, BuildError, digest_json, sha256_file

SDK_DIRNAME = ".orca-sdk-2.2.1"
MIN_ORCA_C = (2, 2, 0)
# Toolchain files whose bytes can change compiler or linker output.
IDENTITY_FILES = ("Languages/cc", "Languages/Linker", "Libraries/ORCALib",
                  "Libraries/SysLib", "Libraries/SysFloat", "Utilities/MakeLib")
IDENTITY_TREES = ("Libraries/ORCACDefs",)


def _primary_worktree() -> Optional[Path]:
    try:
        common = subprocess.run(["git", "rev-parse", "--path-format=absolute", "--git-common-dir"],
                                cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None
    primary = Path(common).parent
    return None if primary.resolve() == ROOT.resolve() else primary


def find_tool(name: str, env_var: str) -> Optional[str]:
    explicit = os.environ.get(env_var)
    if explicit:
        found = shutil.which(explicit)
        return found or (explicit if Path(explicit).is_file() else None)
    found = shutil.which(name)
    if found:
        return found
    local = Path.home() / ".local/bin" / name
    return str(local) if local.is_file() and os.access(local, os.X_OK) else None


def find_sdk(explicit: Optional[str] = None):
    """Return (path, how-it-was-selected) or raise BuildError."""
    if explicit:
        return Path(explicit).expanduser().resolve(), "--sdk"
    env = os.environ.get("GOLDEN_GATE")
    if env:
        return Path(env).expanduser().resolve(), "GOLDEN_GATE"
    local = ROOT / SDK_DIRNAME
    if local.is_dir():
        return local.resolve(), "repository " + SDK_DIRNAME
    primary = _primary_worktree()
    if primary and (primary / SDK_DIRNAME).is_dir():
        return (primary / SDK_DIRNAME).resolve(), "primary worktree " + SDK_DIRNAME
    raise BuildError("No ORCA/C 2.2.x SDK found. Set GOLDEN_GATE (for example in local.mk) "
                     "or install it at ./" + SDK_DIRNAME + "; see docs/BUILDING.md.")


def orca_c_version(sdk: Path) -> Optional[str]:
    try:
        data = (sdk / "Languages/cc").read_bytes()
    except OSError:
        return None
    match = re.search(rb"ORCA/C (\d\.\d\.\d)", data)
    return match.group(1).decode() if match else None


def _version_text(argv) -> str:
    try:
        out = subprocess.run(argv, capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return "unavailable"
    lines = (out.stdout + out.stderr).strip().splitlines()
    return lines[0].strip() if lines else "unknown"


@dataclass
class Toolchain:
    sdk: Path
    sdk_source: str
    iix: Optional[str]
    acx: Optional[str] = None
    cp2: Optional[str] = None
    nulib2: Optional[str] = None
    _identity: Optional[dict] = field(default=None, repr=False)

    @classmethod
    def discover(cls, sdk: Optional[str] = None) -> "Toolchain":
        path, source = find_sdk(sdk)
        return cls(sdk=path, sdk_source=source, iix=find_tool("iix", "IIX"),
                   acx=find_tool("acx", "ACX"), cp2=find_tool("cp2", "CP2"),
                   nulib2=find_tool("nulib2", "NULIB2"))

    def env(self) -> Dict[str, str]:
        return dict(os.environ, GOLDEN_GATE=str(self.sdk))

    def require_compiler(self) -> None:
        if not self.iix:
            raise BuildError("GoldenGate 'iix' was not found (set IIX or add it to PATH).")
        if not (self.sdk / "Languages/cc").is_file():
            raise BuildError(f"SDK has no Languages/cc: {self.sdk} (selected by {self.sdk_source}).")
        version = orca_c_version(self.sdk)
        if not version or tuple(map(int, version.split("."))) < MIN_ORCA_C:
            raise BuildError(f"ORCA/C {version or 'unknown'} in {self.sdk} is not supported; "
                             "ORCA/C 2.2.x is required (the recorded builds used 2.2.1).")

    def require_packaging(self) -> None:
        missing = [name for name, path in (("acx", self.acx), ("cp2", self.cp2), ("nulib2", self.nulib2))
                   if not path]
        if missing:
            raise BuildError("Packaging tools missing: " + ", ".join(missing)
                             + " (set ACX/CP2/NULIB2 or add them to PATH; see docs/BUILDING.md).")

    def identity(self) -> dict:
        """Hashes of everything in the toolchain that can change output bytes.

        Contains no local paths, so it is safe for public manifests.
        """
        if self._identity is None:
            files = {}
            for name in IDENTITY_FILES:
                path = self.sdk / name
                if path.is_file():
                    files[name] = sha256_file(path)
            for tree in IDENTITY_TREES:
                root = self.sdk / tree
                if root.is_dir():
                    entries = {str(p.relative_to(root)): sha256_file(p)
                               for p in sorted(root.rglob("*")) if p.is_file()}
                    files[tree + "/*"] = digest_json(entries)
            iix = Path(self.iix).resolve() if self.iix else None
            self._identity = {
                "orca_c": orca_c_version(self.sdk),
                "iix": _version_text([self.iix, "--version"]) if self.iix else None,
                "iix_sha256": sha256_file(iix) if iix and iix.is_file() else None,
                "sdk_files_sha256": files,
            }
        return self._identity

    def fingerprint(self) -> str:
        return digest_json(self.identity())[:16]

    def packaging_identity(self) -> dict:
        return {"acx": _version_text([self.acx, "--version"]) if self.acx else None,
                "cp2": _version_text([self.cp2, "version"]) if self.cp2 else None,
                "nulib2": "present" if self.nulib2 else None}
