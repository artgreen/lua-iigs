"""ORCA EXEC batch files for hardware kits, generated from the same step list
that the local preflight executes, so the two cannot drift apart.

Rules (hardware-confirmed): one command per line, no semicolons anywhere
(including comments), CR line endings on the IIgs, a configurable numeric
executable prefix such as 20: (empty means normal shell lookup). Expected
failures are captured with 'unset exit', '>&file', and 'set var {status}'
before the next command runs.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import List, Optional, Tuple

from .common import BuildError

PREFIX = re.compile(r"(?:[0-9]{1,2}:)?")


@dataclass
class Step:
    name: str
    exe: str                      # lower-case program name in the kit (e.g. luatest)
    args: List[str]
    capture: Optional[Tuple[str, str]] = None  # (error file, status variable): failure expected
    marker: Optional[str] = None  # regex required in local output
    suite_group: Optional[str] = None  # validate the suite summary for this group
    echo: Optional[str] = None    # progress line shown before the step
    notes: List[str] = field(default_factory=list)


def check_prefix(prefix: str) -> str:
    if not PREFIX.fullmatch(prefix):
        raise BuildError("PREFIX must be a prefix number followed by a colon (e.g. 20:), or empty")
    return prefix


def render(title: str, steps: List[Step], prefix: str = "20:") -> str:
    check_prefix(prefix)
    lines = ["* " + title, "set exit on"]
    for step in steps:
        if step.echo:
            lines.append("echo " + step.echo)
        if step.capture:
            lines.append("unset exit")
        command = prefix + step.exe + (" " + " ".join(step.args) if step.args else "")
        if step.capture:
            errfile, var = step.capture
            lines.extend([command + " >&" + errfile, f"set {var} {{status}}", "set exit on"])
        else:
            lines.append(command)
    lines.append("exit 0")
    text = "\n".join(lines) + "\n"
    validate(text)
    return text


def validate(text: str) -> None:
    if ";" in text:
        raise BuildError("ORCA batch text must not contain semicolons (not even in comments)")
    for line in text.splitlines():
        if not line.strip():
            raise BuildError("ORCA batch text must not contain blank lines")
        if len(line) > 200:
            raise BuildError("ORCA batch line too long: " + line[:40])
        if not line.isascii():
            raise BuildError("ORCA batch text must be ASCII")
