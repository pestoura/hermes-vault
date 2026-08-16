from __future__ import annotations

import json
import re
import sys
from pathlib import Path

EXPECTED_SCHEMA = "hermes-vault-lab-l1-source/v1"
EXPECTED_REPOSITORY = "pestoura/hermes-security-labs"
EXPECTED_COMMIT = "c63fee752bfd28868da54eb9650943e2b504f659"
EXPECTED_PATH = "deployment/vault-lab-l1"
EXPECTED_FILES = {
    "README.md": "6aeed8724876ddf6a2c7ae376a0b1bfb3ee9f5ee",
    "compose.yaml": "ba775ef75253737cd7a17e0e85e5bb69401defa1",
    "config/vault.hcl": "48127d7a72a356d33844cf74af1927f83864800c",
    "bootstrap/bootstrap.sh": "071e5b9826ef33a0fbeafd9481bc714833ed8d0f",
    "bootstrap/verify-capability.sh": "7b16f61601cdc1ae6a8dfc5403779920813a3911",
    "policies/operator-observer.hcl": "5d6c51f558739738bf9db29f6613cadfc383ccdc",
    "policies/signer.hcl": "bcc23eaec0381d5820c7573be9592bef0cc2913f",
}
_SHA40 = re.compile(r"^[0-9a-f]{40}$")


def validate_manifest(data: dict) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if data.get("schema") != EXPECTED_SCHEMA:
        errors.append("schema mismatch")

    source = data.get("source")
    if not isinstance(source, dict):
        return False, errors + ["source must be an object"]
    if source.get("repository") != EXPECTED_REPOSITORY:
        errors.append("repository mismatch")
    commit = source.get("commit")
    if commit != EXPECTED_COMMIT or not isinstance(commit, str) or not _SHA40.fullmatch(commit):
        errors.append("commit must be the approved exact 40-hex SHA")
    if source.get("path") != EXPECTED_PATH:
        errors.append("path mismatch")
    if "branch" in source or "tag" in source:
        errors.append("mutable branch/tag authority is forbidden")
    if source.get("files") != EXPECTED_FILES:
        errors.append("files must match approved upstream blob identities exactly")

    adoption = data.get("adoption")
    if not isinstance(adoption, dict):
        errors.append("adoption must be an object")
    else:
        if adoption.get("mode") != "immutable_reference":
            errors.append("adoption.mode must be immutable_reference")
        if adoption.get("copy_upstream_files") is not False:
            errors.append("copy_upstream_files must be false")
        if adoption.get("runtime_status") != "NOT_RUN":
            errors.append("runtime_status must remain NOT_RUN")
        if adoption.get("live_gates_asserted") is not False:
            errors.append("live_gates_asserted must remain false")
    return not errors, errors


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: python tools/validate_lab_l1_source.py baseline/lab-l1-source.json", file=sys.stderr)
        return 3
    path = Path(argv[1])
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"LAB_L1_SOURCE_INVALID {type(exc).__name__}", file=sys.stderr)
        return 3
    ok, errors = validate_manifest(data)
    if not ok:
        for error in errors:
            print(f"LAB_L1_SOURCE_INVALID {error}", file=sys.stderr)
        return 2
    print(f"LAB_L1_SOURCE_OK commit={EXPECTED_COMMIT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
