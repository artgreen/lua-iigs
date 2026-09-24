"""Small shared helpers: paths, hashing, atomic files, locking, processes."""
from __future__ import annotations

import datetime
import errno
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]
BUILD = ROOT / "build"
DEV = BUILD / "dev"              # disposable per-configuration dev builds
TEST_RUNS = BUILD / "test-runs"  # disposable local test scratch
IDENTIFIED = BUILD / "builds"    # immutable identified builds (preserved)
PACKAGES = BUILD / "packages"    # verified release-style packages (preserved)
KITS = BUILD / "hardware-suites"  # hardware test kits (preserved)
REPORTS = BUILD / "test-reports"  # test reports for identified builds (preserved)

PRODOS_NAME = re.compile(r"[A-Za-z][A-Za-z0-9.]{0,14}")


class BuildError(Exception):
    """A failure the user must act on; the message is printed without a traceback."""


def say(message: str) -> None:
    print(message, flush=True)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def digest_json(value) -> str:
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode())


def utc_stamp() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def utc_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()


def rel(path: Path) -> str:
    """Repository-relative path for messages and public records."""
    try:
        return str(Path(path).resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def write_atomic(path: Path, data: bytes) -> None:
    """Replace 'path' with complete contents or leave it untouched."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix="." + path.name + ".", suffix=".partial", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def write_json(path: Path, value) -> None:
    write_atomic(path, (json.dumps(value, indent=2, sort_keys=False) + "\n").encode())


def read_json(path: Path, default=None):
    try:
        return json.loads(Path(path).read_text())
    except FileNotFoundError:
        return default


def copy_with_metadata(src: Path, dst: Path) -> None:
    """Copy bytes and ProDOS/Finder metadata (extended attributes).

    ORCA objects and libraries carry their file type in extended attributes;
    a byte-only copy can be rejected by the linker. macOS cp preserves them.
    """
    dst = Path(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_name("." + dst.name + ".partial")
    if tmp.exists():
        tmp.unlink()
    flags = ["-p"] if sys.platform == "darwin" else ["--preserve=all"]
    result = subprocess.run(["cp", *flags, str(src), str(tmp)], capture_output=True, text=True)
    if result.returncode:
        tmp.unlink(missing_ok=True)
        raise BuildError(f"copy failed: {src} -> {dst}: {result.stderr.strip()}")
    os.replace(tmp, dst)


def remove_tree(path: Path) -> None:
    path = Path(path)
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.exists():
        # Identified builds are made read-only; restore write permission first.
        for dirpath, dirnames, _ in os.walk(path):
            os.chmod(dirpath, 0o755)
        shutil.rmtree(path)


def make_read_only(path: Path) -> None:
    """Protect finished evidence from accidental modification (not a security boundary)."""
    for dirpath, _, filenames in os.walk(path):
        for name in filenames:
            file = Path(dirpath) / name
            file.chmod(file.stat().st_mode & ~0o222)


def new_unique_dir(parent: Path, prefix: str) -> Path:
    parent.mkdir(parents=True, exist_ok=True)
    return Path(tempfile.mkdtemp(prefix=prefix + "-", dir=parent))


class DirLock:
    """Exclusive advisory lock serializing work on one build directory.

    Concurrent 'make' invocations (including make -j across goals, or two
    terminals) wait here instead of interleaving ORCA runs in one tree.
    """

    def __init__(self, directory: Path, label: str):
        self.path = Path(directory) / ".lock"
        self.label = label
        self.handle = None

    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.handle = self.path.open("a+")
        try:
            fcntl.flock(self.handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            if exc.errno not in (errno.EAGAIN, errno.EACCES):
                raise
            say(f"Waiting for another build using {rel(self.path.parent)} ({self.label})...")
            started = time.monotonic()
            fcntl.flock(self.handle, fcntl.LOCK_EX)
            say(f"Lock acquired after {time.monotonic() - started:.0f}s")
        return self

    def __exit__(self, *exc):
        fcntl.flock(self.handle, fcntl.LOCK_UN)
        self.handle.close()


def run_logged(argv, cwd: Path, env: dict, log: Path, timeout: int = 600,
               check: bool = True) -> subprocess.CompletedProcess:
    """Run a tool with stdin closed, saving combined output to 'log'."""
    argv = [str(a) for a in argv]
    log.parent.mkdir(parents=True, exist_ok=True)
    try:
        result = subprocess.run(argv, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        log.write_bytes((exc.stdout or b"") + b"\n[timed out]\n")
        raise BuildError(f"timed out after {timeout}s: {' '.join(argv[:3])}; see {rel(log)}") from exc
    log.write_bytes(result.stdout)
    if check and result.returncode:
        tail = result.stdout.decode(errors="replace").strip().splitlines()[-8:]
        raise BuildError(f"command failed ({result.returncode}): {' '.join(argv[:4])}\n"
                         + "\n".join("    " + line for line in tail) + f"\n  log: {rel(log)}")
    return result


def check_prodos_name(name: str) -> str:
    if not PRODOS_NAME.fullmatch(name):
        raise BuildError(f"not a valid ProDOS file name (letter, then letters/digits/periods, max 15): {name!r}")
    return name
