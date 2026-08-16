from __future__ import annotations

import json
import re
import sys
from pathlib import Path

SCHEMA = "hermes-vault-workload-identities/v1"
EXPECTED_ROLES = {
    "hermes-runtime",
    "hermes-controller",
    "jarvas-operations",
    "github-tool",
}
FORBIDDEN_ROLE_MARKERS = ("admin", "root", "recovery", "break-glass", "breakglass")
_DURATION = re.compile(r"^(\d+)(s|m|h)$")


def _seconds(value: object) -> int | None:
    if not isinstance(value, str):
        return None
    match = _DURATION.fullmatch(value)
    if not match:
        return None
    amount = int(match.group(1))
    unit = match.group(2)
    return amount * {"s": 1, "m": 60, "h": 3600}[unit]


def validate_identity_contract(data: dict) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if data.get("schema") != SCHEMA:
        errors.append("schema mismatch")
    if data.get("auth_method") != "approle":
        errors.append("auth_method must be approle")

    roles = data.get("roles")
    if not isinstance(roles, dict) or set(roles) != EXPECTED_ROLES:
        errors.append("roles must be exactly hermes-runtime, hermes-controller, jarvas-operations and github-tool")
        return False, errors

    policies: set[str] = set()
    for name, role in roles.items():
        if any(marker in name.lower() for marker in FORBIDDEN_ROLE_MARKERS):
            errors.append(f"role {name} is an administrative/break-glass identity")
        if not isinstance(role, dict):
            errors.append(f"role {name} must be an object")
            continue
        policy = role.get("policy")
        if policy != name:
            errors.append(f"role {name} policy must equal role name")
        if policy in policies:
            errors.append(f"role {name} reuses policy {policy}")
        if isinstance(policy, str):
            policies.add(policy)
        if role.get("token_no_default_policy") is not True:
            errors.append(f"role {name} token_no_default_policy must be true")
        if role.get("secret_id_num_uses") != 1:
            errors.append(f"role {name} secret_id_num_uses must be 1")
        if role.get("secret_id_ttl") != "10m":
            errors.append(f"role {name} secret_id_ttl must be 10m")
        if role.get("wrap_ttl") != "5m":
            errors.append(f"role {name} wrap_ttl must be 5m")

        ttl = _seconds(role.get("token_ttl"))
        max_ttl = _seconds(role.get("token_max_ttl"))
        if ttl is None or ttl <= 0 or ttl > 900:
            errors.append(f"role {name} token_ttl must be >0 and <=15m")
        if max_ttl is None or max_ttl <= 0 or max_ttl > 1800:
            errors.append(f"role {name} token_max_ttl must be >0 and <=30m")
        if ttl is not None and max_ttl is not None and ttl > max_ttl:
            errors.append(f"role {name} token_ttl exceeds token_max_ttl")

        if name == "github-tool":
            if role.get("direct_kv") is not True:
                errors.append("github-tool direct_kv must be true")
            if role.get("kv_data_path") != "secret/data/jarvas/github/runtime":
                errors.append("github-tool kv_data_path mismatch")
            if role.get("kv_metadata_path") != "secret/metadata/jarvas/github/runtime":
                errors.append("github-tool kv_metadata_path mismatch")
        elif role.get("direct_kv") is not False:
            errors.append(f"role {name} must not receive direct KV access")

    live = data.get("live_status")
    if not isinstance(live, dict) or any(value is not False for value in live.values()):
        errors.append("all live_status values must remain false in repository implementation")
    return not errors, errors


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: python tools/validate_identity_contract.py identity/workload-roles.json", file=sys.stderr)
        return 3
    try:
        data = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"IDENTITY_CONTRACT_INVALID {type(exc).__name__}", file=sys.stderr)
        return 3
    ok, errors = validate_identity_contract(data)
    if not ok:
        for error in errors:
            print(f"IDENTITY_CONTRACT_INVALID {error}", file=sys.stderr)
        return 2
    print("IDENTITY_CONTRACT_OK roles=4 auth=approle")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
