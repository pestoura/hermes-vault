# tests/isolation/test_hsl_policy_lint.py
#
# Task E2 — HSL signer AppRole exact-path policy + AppRole bootstrap (spec §11.2-§11.3, ADR-014).
#
# The HSL consumer (`hsl-signer` AppRole) gets ONE exact-path least-privilege
# policy binding to the shared-service-owned `hsl` dedicated transit mount/key
# (Task E1, `hsl-transit/hsl-signing`). No wildcard, no sudo, no shared-secret
# access, no paths outside the contract (spec §11.3).
#
# Layout (mirrors tests/isolation/test_hsl_mount.py and
# tests/policy_lint/test_policy_lint.py):
#   1. Live HITL assertions — NOT_RUN here (controller guardrail). The policy is
#      static; live AppRole/policy write belongs to operator HITL steps.
#   2. Offline/static contract validation — proves the committed
#      `policies/hsl/hsl-signer.hcl` passes the exact-path least-privilege
#      linter for identity `hsl-signer`, and that the AppRole bootstrap script
#      is operator-gated/idempotent/data-free — WITHOUT starting Vault or
#      handling any token/key/secret. This is the repo-side E2 GREEN evidence.
from pathlib import Path

import pytest

from src.policy_lint.linter import lint_policy_text, _strip_comments

_POLICY = Path("policies/hsl/hsl-signer.hcl")
_SCRIPT = Path("deployments/vault/scripts/enable-hsl-signer.sh")


# ---------------------------------------------------------------------------
# 1) Live HITL assertion — stays NOT_RUN in this unattended task. Operator must
#    initialize a local TLS Vault, write the policy + AppRole out-of-band, then
#    run. Never relabeled PASS here (controller guardrail).
# ---------------------------------------------------------------------------
def _live_env():
    return all(
        k in __import__("os").environ
        for k in ("VAULT_ADDR", "VAULT_CACERT", "VAULT_TOKEN")
    )


@pytest.mark.hitl
@pytest.mark.skipif(
    not _live_env(),
    reason="E2 HITL: no live Vault endpoint (VAULT_ADDR/VAULT_CACERT/VAULT_TOKEN); "
    "offline static contract tests validate the same contracts below. "
    "LIVE hsl-signer AppRole creation is NOT RUN in this task (controller guardrail).",
)
def test_hsl_signer_approle_present():
    import hvac

    c = hvac.Client(
        url=__import__("os").environ["VAULT_ADDR"],
        token=__import__("os").environ["VAULT_TOKEN"],
        verify=__import__("os").environ["VAULT_CACERT"],
    )
    role = c.auth.approle.read_role("hsl-signer")
    assert "hsl-signer" in (role.get("data", {}).get("token_policies", []))


# ---------------------------------------------------------------------------
# 2) Offline / static contract validation (no Vault runtime, no token, no secrets).
# ---------------------------------------------------------------------------
def test_hsl_signer_policy_clean():
    # The committed exact-path policy must be clean for the `hsl-signer`
    # identity: no wildcard paths, no sudo, only the contract's
    # sign/verify/read capabilities on the canonical hsl-transit mount.
    txt = _POLICY.read_text()
    assert lint_policy_text(txt, identity="hsl-signer") == []


def test_hsl_signer_policy_exact_paths_only():
    # Exact-path least-privilege: only the three contract paths, each with the
    # capability specified (sign/verify -> update, keys read -> read). No
    # wildcard, no sudo, no sys/*, no auth/*, no other consumer mounts.
    txt = _POLICY.read_text()
    assert 'path "hsl-transit/sign/hsl-signing"' in txt
    assert 'path "hsl-transit/verify/hsl-signing"' in txt
    assert 'path "hsl-transit/keys/hsl-signing"' in txt
    # Regression guard: the stale `transit/...` prefix (plan draft) is NOT the
    # accepted E1 source-of-truth mount and would make the AppRole nonfunctional.
    assert 'path "transit/' not in txt, (
        "policy must bind the accepted E1 canonical mount hsl-transit, "
        "not the stale transit/... prefix"
    )
    # No forbidden broad scopes. Assert on comment-stripped text so the
    # explanatory "Explicitly NO path ..." comment never counts as a capability
    # (uses the same comment-preprocessing as lint_policy_text).
    active = _strip_comments(txt)
    for forbidden in ('*"', '"sys/', '"auth/', '"secret/', 'sudo'):
        assert forbidden not in active, (
            f"hsl-signer policy must not contain {forbidden!r} (active, non-comment)"
        )


def test_enable_hsl_signer_script_present():
    # The HITL AppRole bootstrap script exists and encodes the E2 contract.
    assert _SCRIPT.is_file(), f"missing HSL signer enable script: {_SCRIPT}"
    src = _SCRIPT.read_text()
    # Dedicated hsl-signer AppRole name declared via APPROLE_NAME="hsl-signer"
    # (spec §11.2-§11.3). The script is templated: it builds the API path from
    # that variable rather than hardcoding the literal, so recognize the
    # variable declaration AND its use in the approle path.
    assert 'APPROLE_NAME="hsl-signer"' in src, \
        "script must declare the hsl-signer AppRole name via APPROLE_NAME"
    assert 'auth/approle/role/${APPROLE_NAME}' in src, \
        "script must create the hsl-signer AppRole via the APPROLE_NAME path"
    # Policy binding: the AppRole binds the exact-path hsl-signer policy.
    assert 'POLICY_NAME="hsl-signer"' in src, \
        "script must declare the hsl-signer policy name via POLICY_NAME"
    assert "token_policies" in src, "AppRole must bind a policy"
    # Idempotency: re-creation is skipped when already present.
    assert "already present" in src or "skipping" in src, \
        "enable-hsl-signer.sh must be idempotent (skip when already present)"
    # The script creates the AppRole via `vault write auth/approle/role/<name>`.
    assert "vault write" in src and "auth/approle/role/${APPROLE_NAME}" in src, \
        "script must create the hsl-signer AppRole via vault write"


def test_enable_hsl_signer_token_lease_contract():
    # Least-privilege lease contract (spec §11.3): short-lived signer token with
    # an explicit max TTL, bound to exactly the hsl-signer policy.
    src = _SCRIPT.read_text()
    assert 'TOKEN_TTL="15m"' in src, "AppRole must declare token_ttl=15m"
    assert 'TOKEN_MAX_TTL="1h"' in src, "AppRole must declare token_max_ttl=1h"
    assert 'token_ttl="${TOKEN_TTL}"' in src, "token_ttl must be passed to vault write"
    assert 'token_max_ttl="${TOKEN_MAX_TTL}"' in src, \
        "token_max_ttl must be passed to vault write"
    assert 'token_policies="${POLICY_NAME}"' in src, \
        "token_policies must bind exactly the hsl-signer policy"


def test_enable_hsl_signer_cidr_is_operator_supplied_optional():
    # CIDR binding must be operator-supplied and optional — never a hardcoded
    # broad CIDR (0.0.0.0/0 or similar) baked into the provider artifact.
    src = _SCRIPT.read_text()
    assert 'CIDR_BIND="${VAULT_HSL_SIGNER_CIDR:-}"' in src, \
        "CIDR must come from the operator-supplied VAULT_HSL_SIGNER_CIDR, defaulting empty"
    assert '[[ -n "${CIDR_BIND}" ]]' in src, \
        "token_bound_cidrs must only be applied when the operator supplies a CIDR"
    for broad in ("0.0.0.0/0", "::/0", "/0\"", "0.0.0.0"):
        assert broad not in src, f"hardcoded broad CIDR forbidden: {broad!r}"


def test_enable_hsl_signer_is_operator_hitl_only():
    # Hard boundary: unattended tasks / CI must NOT create the AppRole live.
    # The script refuses to run without an explicit operator acknowledgement and
    # never starts Vault, reads/writes tokens, or issues/generates a SecretID.
    src = _SCRIPT.read_text()
    assert "VAULT_HSL_SIGNER_OPERATOR_ACK" in src, "missing HITL acknowledgement gate"
    for forbidden in (
        "vault operator init",
        "vault operator unseal",
        "vault server",
        "vault token create",
        "secret-id",
        "secret_id",
        "approle role secret-id",
    ):
        assert forbidden not in src, f"forbidden live/secret op present: {forbidden!r}"


def test_enable_hsl_signer_is_data_free():
    # The script must contain NO real secret shapes anywhere in its source.
    src = _SCRIPT.read_text()
    secret_shapes = (
        # real token/SecretID/recovery/key literal
        __import__("re").compile(r"(root_token|recovery_key|s\.[A-Za-z0-9]{20,})"),
        # Allow operator guards that READ an env var (e.g. `${VAULT_TOKEN:-}`),
        # but reject any ASSIGNMENT of a real value (`VAULT_TOKEN=...`).
        __import__("re").compile(r"(VAULT_TOKEN|SecretID)\s*[:=]\s*(?![-}])"),
    )
    for pat in secret_shapes:
        assert not pat.search(src), \
            f"enable-hsl-signer.sh must not contain secret material: {pat.pattern}"


def test_enable_hsl_signer_never_claims_live_pass_unattended():
    # Fail-closed: without the operator acknowledgement the script MUST exit
    # NON-zero and never emit a "live PASS" style claim. Honest ledger
    # vocabulary: live AppRole creation is gated, NOT_RUN until an operator runs it.
    src = _SCRIPT.read_text()
    assert "HITL REFUSES" in src, "script must refuse unattended execution"
    assert __import__("re").search(r"exit 1", src), "script must fail-closed without operator ACK"
    # Role-secret issuance is an operator HITL step, explicitly NOT performed here.
    assert "NOT performed here" in src or "operator HITL" in src, \
        "script must record that role-secret issuance is operator HITL"
    # The contract scope (HSL consumer does not own this deployment) is recorded.
    assert "shared ownership" in src.lower() or "provider-owned" in src.lower(), \
        "script must record the shared-ownership / provider-owned contract"


def test_enable_hsl_signer_ensures_approle_auth_method_idempotently():
    src = _SCRIPT.read_text()
    assert 'vault auth list -format=json' in src
    assert '"approle/"' in src
    assert 'vault auth enable approle' in src
    auth_enable = src.index('vault auth enable approle')
    role_write = src.index('vault write "auth/approle/role/${APPROLE_NAME}"')
    assert auth_enable < role_write
