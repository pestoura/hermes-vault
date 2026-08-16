from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Sequence

MAX_CAPTURE_BYTES = 16_384
DEFAULT_TIMEOUT_S = 5.0

_SECRET_ASSIGNMENT = re.compile(
    r"(?im)^(?P<prefix>\s*(?:password|passwd|pwd|token|secret|api[_-]?key|access[_-]?key|client[_-]?secret|private[_-]?key)\s*[:=]\s*)(?P<value>[^\r\n]+)$"
)
_BEARER = re.compile(r"(?i)(authorization\s*:\s*bearer\s+)([^\s\r\n]+)")
_PRIVATE_KEY_BLOCK = re.compile(
    r"-----BEGIN(?: [A-Z0-9]+)? PRIVATE KEY-----.*?-----END(?: [A-Z0-9]+)? PRIVATE KEY-----",
    re.DOTALL,
)


@dataclass(frozen=True)
class CommandObservation:
    argv: tuple[str, ...]
    status: str
    returncode: int | None
    stdout: str
    stderr: str
    duration_ms: int
    truncated: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


def _bounded_text(value: str, limit: int = MAX_CAPTURE_BYTES) -> tuple[str, bool]:
    raw = value.encode("utf-8", errors="replace")
    if len(raw) <= limit:
        return value, False
    bounded = raw[:limit].decode("utf-8", errors="ignore")
    return bounded, True


def sanitize_text(text: str) -> str:
    if not text:
        return text
    sanitized = _PRIVATE_KEY_BLOCK.sub("[REDACTED_PRIVATE_KEY]", text)
    sanitized = _BEARER.sub(r"\1[REDACTED]", sanitized)
    sanitized = _SECRET_ASSIGNMENT.sub(
        lambda match: f"{match.group('prefix')}[REDACTED]",
        sanitized,
    )
    return sanitized


def run_command(argv: Sequence[str], timeout_s: float = DEFAULT_TIMEOUT_S) -> CommandObservation:
    if not argv or not all(isinstance(part, str) and part for part in argv):
        raise ValueError("argv must be a non-empty sequence of non-empty strings")
    if timeout_s <= 0 or timeout_s > 30:
        raise ValueError("timeout_s must be > 0 and <= 30")

    started = time.monotonic()
    try:
        completed = subprocess.run(
            list(argv),
            shell=False,
            timeout=timeout_s,
            text=True,
            capture_output=True,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return CommandObservation(
            argv=tuple(argv),
            status="timeout",
            returncode=None,
            stdout="",
            stderr="",
            duration_ms=int((time.monotonic() - started) * 1000),
            truncated=False,
        )
    except FileNotFoundError:
        return CommandObservation(
            argv=tuple(argv),
            status="not_found",
            returncode=None,
            stdout="",
            stderr="",
            duration_ms=int((time.monotonic() - started) * 1000),
            truncated=False,
        )
    except PermissionError:
        return CommandObservation(
            argv=tuple(argv),
            status="permission_denied",
            returncode=None,
            stdout="",
            stderr="",
            duration_ms=int((time.monotonic() - started) * 1000),
            truncated=False,
        )

    stdout, stdout_truncated = _bounded_text(sanitize_text(completed.stdout or ""))
    stderr, stderr_truncated = _bounded_text(sanitize_text(completed.stderr or ""))
    return CommandObservation(
        argv=tuple(argv),
        status="ok" if completed.returncode == 0 else "error",
        returncode=completed.returncode,
        stdout=stdout,
        stderr=stderr,
        duration_ms=int((time.monotonic() - started) * 1000),
        truncated=stdout_truncated or stderr_truncated,
    )


def write_report_atomic(path: Path, report: dict) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    fd, temp_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        dir=str(path.parent),
        text=True,
    )
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
        os.chmod(path, 0o600)
    except Exception:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
        raise
