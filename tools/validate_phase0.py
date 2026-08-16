from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from tools.phase0_discovery import REPORT_SCHEMA, evaluate_phase0

_FORBIDDEN_KEYS = {
    "stdout", "stderr", "argv", "raw", "raw_output", "content",
    "secret_value", "token_value", "password_value", "private_key_value",
}
_PRIVATE_KEY = re.compile(r"-----BEGIN(?: [A-Z0-9]+)? PRIVATE KEY-----")
_BEARER_VALUE = re.compile(r"(?i)authorization\s*:\s*bearer\s+(?!\[REDACTED\])\S+")
_GITHUB_TOKEN = re.compile(r"gh[pousr]_[A-Za-z0-9_]{20,}")


def _walk(value, path: str = "$"):
    if isinstance(value, dict):
        for key, child in value.items():
            yield path, key, child
            yield from _walk(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _walk(child, f"{path}[{index}]")


def validate_report(report: dict) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if report.get("schema") != REPORT_SCHEMA:
        errors.append("schema mismatch")
    if report.get("mode") != "read_only":
        errors.append("mode must be read_only")
    if report.get("mutation_performed") is not False:
        errors.append("mutation_performed must be false")
    sections = report.get("sections")
    if not isinstance(sections, dict):
        errors.append("sections must be an object")
    else:
        expected_gates = evaluate_phase0(sections)
        if report.get("gates") != expected_gates:
            errors.append("gate evaluation does not match deterministic evaluator")

    for path, key, child in _walk(report):
        if key in _FORBIDDEN_KEYS:
            errors.append(f"forbidden raw field at {path}.{key}")
        if isinstance(child, str):
            if _PRIVATE_KEY.search(child):
                errors.append(f"private-key material marker at {path}.{key}")
            if _BEARER_VALUE.search(child):
                errors.append(f"unredacted bearer value at {path}.{key}")
            if _GITHUB_TOKEN.search(child):
                errors.append(f"GitHub token-shaped value at {path}.{key}")
    return not errors, errors


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: python tools/validate_phase0.py REPORT.json", file=sys.stderr)
        return 3
    path = Path(argv[1])
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"PHASE0_INVALID {type(exc).__name__}", file=sys.stderr)
        return 3
    ok, errors = validate_report(report)
    if not ok:
        for error in errors:
            print(f"PHASE0_INVALID {error}", file=sys.stderr)
        return 2
    discovery = report["gates"]["DISCOVERY_COMPLETE"]["status"]
    print(f"PHASE0_REPORT_OK discovery={discovery}")
    return 0 if discovery == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
