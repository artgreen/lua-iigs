"""One packaging implementation for every kit: 800 KB ProDOS images (.po)
and NuFX/ShrinkIt archives (.SHK), verified by independent readback.

Pitfalls this module guards against (all observed):
- acx silently ignores numeric file types ("$B5", "0xB5", "B5") and
  stores NON $00; only type names work. Every member's type/aux is
  therefore read back with cp2 and compared with the intended values.
- nulib2 -p exits 0 and prints an error message for a missing member, so
  extracted bytes (not exit status) decide success.
- ORCA text must use CR line endings; executables must stay byte-exact.

Nothing here builds or modifies executables; callers pass exact bytes.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import subprocess
from typing import Dict, List, Sequence

from .common import BuildError, check_prodos_name, sha256, write_atomic
from .toolchain import Toolchain

# kind: (acx type name, ProDOS file type, auxiliary type)
TYPES = {
    "EXE": ("EXE", 0xB5, 0x0000),   # ORCA shell executable
    "LIB": ("LIB", 0xB2, 0x0000),   # ORCA library (makelib)
    "OBJ": ("OBJ", 0xB1, 0x0000),   # ORCA object module
    "TXT": ("TXT", 0x04, 0x0000),   # text (Lua source, readme)
    "EXEC": ("SRC", 0xB0, 0x0006),  # ORCA EXEC batch file
    "CSRC": ("SRC", 0xB0, 0x0008),  # ORCA/C source or header
    "BIN": ("BIN", 0x06, 0x0000),   # Lua bytecode chunk
}
TEXT_KINDS = {"TXT", "EXEC", "CSRC"}
IMAGE_SIZES = {"800K": 780 * 1024, "1600K": 1580 * 1024}  # usable bytes, with directory margin
CATALOG = re.compile(r"^([A-Z0-9?]{3})\s+\$([0-9A-F]{4})\s.*?\s\*?(\S+)\s*$", re.M)


def native_text(data: bytes) -> bytes:
    return data.replace(b"\r\n", b"\n").replace(b"\n", b"\r")


@dataclass
class Member:
    name: str
    data: bytes
    kind: str

    def __post_init__(self):
        check_prodos_name(self.name)
        if self.kind not in TYPES:
            raise BuildError(f"unknown member kind {self.kind!r} for {self.name}")

    @property
    def native(self) -> bytes:
        return native_text(self.data) if self.kind in TEXT_KINDS else self.data

    def record(self) -> dict:
        _, ftype, aux = TYPES[self.kind]
        return {"name": self.name, "kind": self.kind, "file_type": f"${ftype:02X}",
                "aux_type": f"${aux:04X}", "size": len(self.native), "sha256": sha256(self.native)}


def _run(argv, check=True) -> bytes:
    result = subprocess.run([str(a) for a in argv], stdin=subprocess.DEVNULL,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if check and result.returncode:
        raise BuildError(f"{Path(str(argv[0])).name} failed ({result.returncode}): "
                         + result.stdout.decode(errors="replace").strip()[-300:])
    return result.stdout


def read_attrs(tc: Toolchain, container: Path, name: str):
    text = _run([tc.cp2, "get-attr", container, name]).decode(errors="replace")
    ftype = re.search(r"File Type\s*:\s*\S+\s+0x([0-9a-fA-F]+)", text)
    aux = re.search(r"Aux Type\s*:\s*0x([0-9a-fA-F]+)", text)
    if not ftype or not aux:
        raise BuildError(f"cannot read metadata of {name} in {container.name}")
    return int(ftype.group(1), 16), int(aux.group(1), 16)


def catalog(tc: Toolchain, container: Path) -> Dict[str, tuple]:
    text = _run([tc.cp2, "catalog", container]).decode(errors="replace")
    return {m.group(3).upper(): (m.group(1), int(m.group(2), 16)) for m in CATALOG.finditer(text)}


def verify_container(tc: Toolchain, container: Path, members: Sequence[Member]) -> None:
    """Extract every member and compare bytes and ProDOS metadata; exact member set."""
    is_image = container.suffix.lower() == ".po"
    expected = {m.name.upper() for m in members}
    found = set(catalog(tc, container))
    if found != expected:
        raise BuildError(f"{container.name}: members {sorted(found)} != expected {sorted(expected)}")
    for member in members:
        if is_image:
            data = _run([tc.acx, "export", "-d", container, "--raw", member.name.upper()])
        else:
            data = _run([tc.nulib2, "-p", container, member.name.upper()], check=False)
        if data != member.native:
            raise BuildError(f"{container.name}: {member.name} bytes differ after extraction "
                             f"({len(data)} vs {len(member.native)} bytes)")
        _, ftype, aux = TYPES[member.kind]
        got = read_attrs(tc, container, member.name.upper())
        if got != (ftype, aux):
            raise BuildError(f"{container.name}: {member.name} metadata ${got[0]:02X}/${got[1]:04X}, "
                             f"expected ${ftype:02X}/${aux:04X}")


def build_container(tc: Toolchain, out_dir: Path, basename: str, volume: str,
                    members: List[Member], archive: bool = True, image_size: str = "800K") -> dict:
    """Create and verify <basename>.po (+ <BASENAME>.SHK). Never overwrites.

    Images are 800 KB transfer images unless a kit needs 1600K; the .SHK
    archive is what normally travels to the IIgs.
    """
    tc.require_packaging()
    check_prodos_name(volume)
    names = [m.name.upper() for m in members]
    if len(names) != len(set(names)):
        raise BuildError(f"duplicate member names in {basename}: {sorted(names)}")
    total = sum(len(m.native) + 512 for m in members)
    if total > IMAGE_SIZES[image_size]:
        raise BuildError(f"{basename}: {total:,} bytes do not fit a {image_size} transfer image")
    out_dir.mkdir(parents=True, exist_ok=True)
    image = out_dir / (basename + ".po")
    shk = out_dir / (basename.upper() + ".SHK")
    for path in (image, shk):
        if path.exists():
            raise BuildError(f"refusing to overwrite existing {path}")
    staging = out_dir / "files" / basename  # exact member bytes, kept for audit
    staging.mkdir(parents=True, exist_ok=True)
    try:
        _run([tc.acx, "create", "--prodos", "--prodos-order", "-s", image_size, "-n", volume, "-d", image])
        for member in members:
            source = staging / member.name
            write_atomic(source, member.native)
            typename, _, aux = TYPES[member.kind]
            _run([tc.acx, "import", "-d", image, "--raw", "-t", typename, "--aux", f"0x{aux:04X}",
                  "-n", member.name, source])
        verify_container(tc, image, members)
        record = {"image": {"file": image.name, "volume": volume, "size_class": image_size,
                            "sha256": sha256(image.read_bytes()),
                            "size": image.stat().st_size}}
        if archive:
            _run([tc.cp2, "create-file-archive", shk])
            _run([tc.cp2, "copy", image, shk])
            verify_container(tc, shk, members)
            record["archive"] = {"file": shk.name, "sha256": sha256(shk.read_bytes()),
                                 "size": shk.stat().st_size}
    except BaseException:
        for path in (image, shk):
            path.unlink(missing_ok=True)
        raise
    record["members"] = [m.record() for m in members]
    record["verification"] = ("every member extracted (acx for .po, nulib2 for .SHK) and compared "
                              "byte-for-byte; type/aux read back with cp2; exact member set")
    return record


def write_sums(directory: Path, names: Sequence[str]) -> Path:
    lines = [f"{sha256((directory / n).read_bytes())}  {n}\n" for n in sorted(names)]
    path = directory / "SHA256SUMS"
    write_atomic(path, "".join(lines).encode())
    return path


def verify_sums(directory: Path) -> List[str]:
    bad = []
    for line in (directory / "SHA256SUMS").read_text().splitlines():
        digest, name = line.split(None, 1)
        path = directory / name.strip()
        if not path.is_file() or sha256(path.read_bytes()) != digest:
            bad.append(name.strip())
    return bad
