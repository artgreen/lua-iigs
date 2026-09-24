"""Copy verified containers to a transfer directory such as /Volumes/nas/lua.test.

Only files listed in the source's SHA256SUMS are copied, after those sums
are rechecked. Existing different files are never replaced silently:
without --replace the copy is refused; with it, the previous file is moved
to <dest>/replaced-<utc>/ first and a notice is printed. Every copied file
is read back and compared. Copying the .SHK/.po containers preserves
ProDOS metadata; naked executables are not staged.
"""
from __future__ import annotations

import os
from pathlib import Path
import shutil

from .common import BuildError, rel, say, sha256_file, utc_stamp
from .packaging import verify_sums


def stage(args) -> int:
    source = args.source.resolve()
    if (source / "package" / "SHA256SUMS").is_file():
        source = source / "package"
    if not (source / "SHA256SUMS").is_file():
        raise BuildError(f"{source} has no SHA256SUMS; stage a kit or package directory")
    bad = verify_sums(source)
    if bad:
        raise BuildError(f"checksum mismatch in {source}: {bad}; refusing to stage")
    dest = args.dest
    if not dest.parent.is_dir():
        raise BuildError(f"{dest.parent} does not exist (is the transfer volume mounted?)")
    names = [line.split(None, 1)[1].strip() for line in (source / "SHA256SUMS").read_text().splitlines()]
    names.append("SHA256SUMS")
    conflicts = [n for n in names if (dest / n).exists() and sha256_file(dest / n) != sha256_file(source / n)]
    if conflicts and not args.replace:
        raise BuildError(f"{dest} already has different {', '.join(conflicts)}. Nothing was copied. "
                         "Use a new DEST, or REPLACE=1 to move the old files aside first.")
    dest.mkdir(exist_ok=True)
    if conflicts:
        backup = dest / f"replaced-{utc_stamp()}"
        suffix = 1
        while backup.exists():
            suffix += 1
            backup = dest / f"replaced-{utc_stamp()}-{suffix}"
        backup.mkdir()
        for name in conflicts:
            (dest / name).rename(backup / name)
        say(f"NOTICE: replaced {len(conflicts)} staged file(s) in {dest}; previous copies are in {backup}")
    for name in names:
        target = dest / name
        if target.exists() and sha256_file(target) == sha256_file(source / name):
            say(f"  {name}: already staged (identical)")
            continue
        # Containers carry the ProDOS metadata inside; a plain byte copy suffices
        # and avoids extended-attribute failures on network shares.
        partial = dest / ("." + name + ".partial")
        shutil.copyfile(source / name, partial)
        os.replace(partial, target)
        if sha256_file(target) != sha256_file(source / name):
            raise BuildError(f"read-back mismatch for {target}")
        say(f"  {name}: copied and read back")
    say(f"Staged {rel(source)} -> {dest}")
    return 0
