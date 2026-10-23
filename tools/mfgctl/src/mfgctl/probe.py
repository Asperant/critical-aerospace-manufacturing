"""Probes of the developer machine and command runners.

Every external command goes through a runner so tests can replace the
machine with a fake and so a missing tool or a hung command becomes a result,
never an exception or an endless wait.
"""

from __future__ import annotations

import os
import shutil
import socket
import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

NOT_FOUND = 127
TIMED_OUT = 124


@dataclass(frozen=True)
class Result:
    returncode: int
    stdout: str = ""
    stderr: str = ""

    @property
    def ok(self) -> bool:
        return self.returncode == 0

    def first_error_line(self) -> str:
        text = self.stderr or self.stdout
        return text.splitlines()[0] if text else f"exit code {self.returncode}"


class Runner(Protocol):
    def __call__(self, args: Sequence[str], timeout: float) -> Result: ...


def run_command(args: Sequence[str], timeout: float) -> Result:
    try:
        completed = subprocess.run(
            list(args), capture_output=True, text=True, timeout=timeout, check=False
        )
    except FileNotFoundError:
        return Result(NOT_FOUND, stderr=f"{args[0]}: command not found")
    except subprocess.TimeoutExpired:
        return Result(TIMED_OUT, stderr=f"{args[0]}: timed out after {timeout:.0f} s")
    return Result(
        completed.returncode, completed.stdout.strip(), completed.stderr.strip()
    )


def disk_free_bytes(path: Path) -> int:
    return shutil.disk_usage(path).free


def port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    """True if something already accepts connections on host:port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex((host, port)) == 0


class StreamRunner(Protocol):
    def __call__(
        self, args: Sequence[str], env: Mapping[str, str], cwd: Path, timeout: float
    ) -> int: ...


def run_streaming(
    args: Sequence[str], env: Mapping[str, str], cwd: Path, timeout: float
) -> int:
    """Run a command with its output going straight to the terminal."""
    try:
        completed = subprocess.run(
            list(args),
            cwd=cwd,
            env={**os.environ, **env},
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError:
        return NOT_FOUND
    except subprocess.TimeoutExpired:
        return TIMED_OUT
    return completed.returncode
