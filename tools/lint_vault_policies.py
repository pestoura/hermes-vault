from __future__ import annotations

import re
import sys
from pathlib import Path

EXPECTED_POLICIES = {
    "hermes-runtime",
    "hermes-controller",
    "jarvas-operations",
    "github-tool",
}
SELF_PATHS = {
    "auth/token/lookup-self": {"read"},
    "sys/capabilities-self": {"update"},
}
GITHUB_PATHS = {
    "secret/data/jarvas/github/runtime": {"read"},
    "secret/metadata/jarvas/github/runtime": {"read"},
}
_FORBIDDEN_ADMIN_PREFIXES = (
    "sys/policies",
    "sys/auth",
    "sys/mounts",
    "sys/plugins",
    "sys/seal",
    "sys/step-down",
    "auth/approle/role",
)
_PATH_BLOCK = re.compile(r'path\s+"([^"]+)"\s*\{(.*?)\}', re.DOTALL)
_CAPS = re.compile(r'capabilities\s*=\s*\[(.*?)\]', re.DOTALL)
_QUOTED = re.compile(r'"([^"]+)"')


def _blocks(text: str) -> tuple[list[tuple[str, set[str]]], list[str]]:
    blocks: list[tuple[str, set[str]]] = []
    errors: list[str] = []
    matches = list(_PATH_BLOCK.finditer(text))
    if not matches:
        return [], ["policy contains no path blocks"]
    for match in matches:
        path = match.group(1).strip()
        body = match.group(2)
        cap_match = _CAPS.search(body)
        if not cap_match:
            errors.append(f"path {path} has no capabilities list")
            continue
        caps = set(_QUOTED.findall(cap_match.group(1)))
        if not caps:
            errors.append(f"path {path} has an empty capabilities list")
        blocks.append((path, caps))
    return blocks, errors


def lint_policy_text(name: str, text: str) -> list[str]:
    errors: list[str] = []
    if name not in EXPECTED_POLICIES:
        errors.append(f"unknown policy name {name}")
        return errors
    blocks, parse_errors = _blocks(text)
    errors.extend(parse_errors)

    seen: dict[str, set[str]] = {}
    for path, caps in blocks:
        if path in seen:
            errors.append(f"duplicate path {path}")
        seen[path] = caps
        if "sudo" in caps:
            errors.append(f"sudo capability forbidden on {path}")
        if any(cap in caps for cap in {"create", "patch", "delete"}):
            errors.append(f"mutating capability forbidden in EPIC-02 on {path}")
        if "*" in path or "+" in path:
            errors.append(f"wildcard/catch-all path forbidden: {path}")
        if path == "*" or path.startswith("secret/*"):
            errors.append(f"global wildcard forbidden: {path}")
        if any(path == prefix or path.startswith(prefix + "/") for prefix in _FORBIDDEN_ADMIN_PREFIXES):
            errors.append(f"administrative path forbidden: {path}")

    expected = dict(SELF_PATHS)
    if name == "github-tool":
        expected.update(GITHUB_PATHS)
    if seen != expected:
        errors.append(f"policy {name} path/capability set does not match the approved exact contract")
    return errors


def lint_directory(directory: Path) -> tuple[bool, list[str]]:
    errors: list[str] = []
    files = {path.stem: path for path in Path(directory).glob("*.hcl")}
    if set(files) != EXPECTED_POLICIES:
        errors.append("policy directory must contain exactly the four approved policy files")
        return False, errors
    for name, path in sorted(files.items()):
        for error in lint_policy_text(name, path.read_text(encoding="utf-8")):
            errors.append(f"{path}: {error}")
    return not errors, errors


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: python tools/lint_vault_policies.py identity/policies", file=sys.stderr)
        return 3
    ok, errors = lint_directory(Path(argv[1]))
    if not ok:
        for error in errors:
            print(f"VAULT_POLICY_INVALID {error}", file=sys.stderr)
        return 2
    print("VAULT_POLICIES_OK policies=4 wildcard=none sudo=none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
