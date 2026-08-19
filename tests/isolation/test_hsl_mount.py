# tests/isolation/test_hsl_mount.py
#
# Task E1 — HSL dedicated transit mount/key profile (spec §13, ADR-014).
#
# HSL consumes via the `hsl-transit/` mount + `hsl-signing` key. This generalizes
# HSL's `deployment/vault-lab-l1` transit pattern into the shared service; HSL
# does NOT own this deployment (shared ownership, spec §3/§15/§17). The mount and
# key are dedicated to the HSL consumer and provider-owned by hermes-vault.
#
# Layout (mirrors tests/audit/test_audit_redaction.py and
# tests/recovery/test_restore_drill.py):
#   1. Live HITL assertions — VERBATIM from the E1 brief. Require a locally
#      started, operator-initialized Vault over TLS (HITL). Skipped offline/CI
#      (NOT_RUN). Under the E1 controller guardrails the live mount/key creation
#      and these acceptance tests are NOT permitted in this task; they stay
#      NOT_RUN and must never be relabeled PASS.
#   2. Offline/static contract validation — proves the HSL Transit mount/key
#      contract, the HITL operator-only boundary, and the idempotency contract
#      WITHOUT starting Vault, touching a live mount/key, or using any
#      token/key/secret. These are the repo-side E1 GREEN evidence.
import os
import re
from pathlib import Path

import pytest

_SCRIPT = Path("deployments/vault/scripts/enable-hsl-transit.sh")

# HSL dedicated Transit contract (spec §13): mount path + signing key name.
_MOUNT_PATH = "hsl-transit"
_KEY_NAME = "hsl-signing"


# ---------------------------------------------------------------------------
# 1) Live HITL assertion — VERBATIM from the brief, guarded to skip offline.
#    The brief's source code imports hvac at module top; we keep the same calls
#    but only execute when a live Vault endpoint is present, so offline runs
#    (and this unattended, repo-side E1 task) leave them NOT_RUN, never PASS.
# ---------------------------------------------------------------------------
def _live_env():
    return all(k in os.environ for k in ("VAULT_ADDR", "VAULT_CACERT", "VAULT_TOKEN"))


@pytest.mark.hitl
@pytest.mark.skipif(
    not _live_env(),
    reason="E1 HITL: no live Vault endpoint (VAULT_ADDR/VAULT_CACERT/VAULT_TOKEN); "
    "offline static contract tests validate the same contracts below. "
    "LIVE hsl-transit mount/key creation is NOT RUN in this task (controller guardrail).",
)
def test_hsl_transit_mount_present():
    import hvac

    c = hvac.Client(
        url=os.environ["VAULT_ADDR"],
        token=os.environ["VAULT_TOKEN"],
        verify=os.environ["VAULT_CACERT"],
    )
    assert "hsl-transit/" in c.sys.list_mounted_secrets_engines()["data"]


@pytest.mark.hitl
@pytest.mark.skipif(
    not _live_env(),
    reason="E1 HITL: no live Vault endpoint (VAULT_ADDR/VAULT_CACERT/VAULT_TOKEN); "
    "offline static contract tests validate the same contracts below. "
    "LIVE hsl-transit mount/key creation is NOT RUN in this task (controller guardrail).",
)
def test_hsl_signing_key_present():
    import hvac

    c = hvac.Client(
        url=os.environ["VAULT_ADDR"],
        token=os.environ["VAULT_TOKEN"],
        verify=os.environ["VAULT_CACERT"],
    )
    assert "hsl-signing" in c.secrets.transit.read_key(
        name="hsl-signing", mount_point="hsl-transit"
    )["data"]


# ---------------------------------------------------------------------------
# 2) Offline / static contract validation (no Vault runtime, no token, no secrets).
#    Proves the E1 contract from the brief's objective against the committed E1
#    artifact (enable-hsl-transit.sh) without starting Vault, creating the
#    mount/key live, or handling secret material. These are the repo-side E1
#    GREEN evidence.
# ---------------------------------------------------------------------------
def test_enable_hsl_transit_script_present():
    # The HITL enable script exists and encodes the E1 contract.
    assert _SCRIPT.is_file(), f"missing HSL transit enable script: {_SCRIPT}"
    src = _SCRIPT.read_text()
    # Dedicated HSL Transit mount + signing key — the exact spec §13 contract.
    assert f'"{_MOUNT_PATH}/"' in src or f"{_MOUNT_PATH}/" in src, \
        "script must reference the dedicated hsl-transit/ mount"
    assert _KEY_NAME in src, "script must reference the hsl-signing key"
    # Idempotency: re-enable / re-create are skipped when already present.
    assert re.search(r"already (enabled|present)|skipping", src, re.IGNORECASE), \
        "enable-hsl-transit.sh must be idempotent (skip when already enabled/present)"
    # The exact vault commands from the brief's Step 3 implementation.
    assert "vault secrets enable" in src and "-path=hsl-transit" in src, \
        "script must enable the hsl-transit transit mount"
    assert "vault write hsl-transit/keys/hsl-signing" in src, \
        "script must create the hsl-signing key"


def test_enable_hsl_transit_is_operator_hitl_only():
    # Hard boundary: unattended tasks / CI must NOT enable the HSL Transit
    # mount/key live. The script refuses to run without an explicit operator
    # acknowledgement and never starts Vault or reads/writes token/key/SecretID.
    src = _SCRIPT.read_text()
    assert re.search(r"VAULT_HSL_TRANSIT_OPERATOR_ACK", src), \
        "missing HITL acknowledgement gate"
    # No runtime bootstrap / secret-handling commands.
    for forbidden in (
        "vault operator init",
        "vault operator unseal",
        "vault server",
        "vault token create",
        "approle",
        "secret-id",
    ):
        assert forbidden not in src, f"forbidden live/secret op present: {forbidden!r}"


def test_enable_hsl_transit_is_data_free():
    # The script must contain NO real secret shapes anywhere in its source.
    src = _SCRIPT.read_text()
    secret_shapes = (
        re.compile(r"(root_token|recovery_key|s\.[A-Za-z0-9]{20,})"),
        # Allow operator guards that READ an env var (e.g. `${VAULT_TOKEN:-}`),
        # but reject any ASSIGNMENT of a real value (`VAULT_TOKEN=...` /
        # `VAULT_TOKEN: ...`).
        re.compile(r"(VAULT_TOKEN|SecretID)\s*[:=]\s*(?![-}])"),
    )
    for pat in secret_shapes:
        assert not pat.search(src), \
            f"enable-hsl-transit.sh must not contain secret material: {pat.pattern}"


def test_enable_hsl_transit_never_claims_live_pass_unattended():
    # Fail-closed: without the operator acknowledgement the script MUST exit
    # NON-zero and never emit a "live PASS" style claim. Honest ledger
    # vocabulary: live enable is gated, NOT_RUN until an operator runs it.
    src = _SCRIPT.read_text()
    assert "HITL REFUSES" in src, "script must refuse unattended execution"
    assert re.search(r"exit 1", src), "script must fail-closed without operator ACK"
    # The contract scope (HSL consumer does not own this deployment) is recorded.
    assert "shared ownership" in src.lower() or "provider-owned" in src.lower(), \
        "script must record the shared-ownership / provider-owned contract"
