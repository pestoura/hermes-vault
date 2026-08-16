from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

_SENSITIVE_KEY = re.compile(
    r"(?i)(?:^|_)(?:token|secret|secretid|secret_id|password|passwd|pwd|private_key|authorization|cookie|credential|wrapped_payload|recovery|unseal)(?:$|_)"
)
_BEARER = re.compile(r"(?i)(authorization\s*[:=]\s*bearer\s+)([^\s,;]+)")
_GITHUB_TOKEN = re.compile(r"gh[pousr]_[A-Za-z0-9_]{20,}")
_PRIVATE_KEY = re.compile(
    r"-----BEGIN(?: [A-Z0-9]+)? PRIVATE KEY-----.*?-----END(?: [A-Z0-9]+)? PRIVATE KEY-----",
    re.DOTALL,
)


def _marker_strings(secret_markers: Sequence[bytes | bytearray | str]) -> list[str]:
    result: list[str] = []
    for marker in secret_markers:
        if isinstance(marker, str):
            text = marker
        else:
            text = bytes(marker).decode("utf-8", errors="ignore")
        if text:
            result.append(text)
    return sorted(set(result), key=len, reverse=True)


def _sanitize_string(value: str, markers: list[str]) -> str:
    safe = _PRIVATE_KEY.sub("[REDACTED]", value)
    safe = _BEARER.sub(r"\1[REDACTED]", safe)
    safe = _GITHUB_TOKEN.sub("[REDACTED]", safe)
    for marker in markers:
        safe = safe.replace(marker, "[REDACTED]")
    return safe


def sanitize(value: Any, secret_markers: Sequence[bytes | bytearray | str] = ()) -> Any:
    markers = _marker_strings(secret_markers)

    def walk(item: Any) -> Any:
        if isinstance(item, Mapping):
            safe: dict[str, Any] = {}
            for raw_key, child in item.items():
                key = str(raw_key)
                if _SENSITIVE_KEY.search(key):
                    continue
                safe[key] = walk(child)
            return safe
        if isinstance(item, (list, tuple)):
            return [walk(child) for child in item]
        if isinstance(item, str):
            return _sanitize_string(item, markers)
        if isinstance(item, (bytes, bytearray, memoryview)):
            return "[REDACTED_BINARY]"
        if item is None or isinstance(item, (bool, int, float)):
            return item
        return _sanitize_string(str(item), markers)

    return walk(value)
