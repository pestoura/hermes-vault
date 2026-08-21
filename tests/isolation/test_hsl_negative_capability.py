# tests/isolation/test_hsl_negative_capability.py
#
# Task E3 — Negative-capability matrix for hsl-signer (spec §11.4). Core
# isolation proof for the HSL consumer AppRole (spec §13, E1/E2 contract).
#
# Layout (mirrors tests/isolation/test_hsl_mount.py and
# tests/isolation/test_hsl_policy_lint.py):
#   1. Live HITL denial assertions — VERBATIM from the E3 brief. They require a
#      locally started, operator-initialized Vault over TLS with a wrapped
#      SecretID issued out-of-band (HITL). Guarded to skip offline/CI
#      (NOT_RUN). Under the E3 controller guardrails the live deny tests are
#      NOT permitted in this task; they stay NOT_RUN and must never be
#      relabeled PASS.
#   2. Offline / static negative-capability matrix — PROVES repo-side that the
#      committed `policies/hsl/hsl-signer.hcl` policy grants access ONLY to the
#      canonical HSL contract paths and is therefore DENIED every
#      administrative / cross-consumer / over-broad path enumerated in
#      spec §11.4. Uses semantic policy parsing via the existing policy linter
#      (comment stripping + exact-path extraction), not naive raw-substring
#      checks. No Vault runtime, no token, no secrets. This is the repo-side
#      E3 GREEN evidence.
import os

import pytest

# ---------------------------------------------------------------------------
# 1) Live HITL denial assertions — VERBATIM from the brief (§738-§777), guarded
#    to skip unless a live Vault endpoint + HITL-issued credentials are present.
#    These are NEVER executed in this unattended task (controller guardrail).
# ---------------------------------------------------------------------------
def _live_env():
    return all(
        k in os.environ
        for k in ("VAULT_ADDR", "VAULT_CACERT", "HSL_ROLE_ID", "HSL_WRAPPED_SECRETID")
    )


def _client_role():  # obtain HSL-signer token via wrapped SecretID (HITL-issued)
    import hvac

    c = hvac.Client(
        url=os.environ["VAULT_ADDR"], verify=os.environ["VAULT_CACERT"]
    )
    c.auth.approle.login(
        role_id=os.environ["HSL_ROLE_ID"],
        secret_id=os.environ["HSL_WRAPPED_SECRETID"],
    )
    return c


@pytest.mark.hitl
@pytest.mark.skipif(
    not _live_env(),
    reason="E3 HITL: no live Vault endpoint / HITL-issued SecretID "
    "(VAULT_ADDR/VAULT_CACERT/HSL_ROLE_ID/HSL_WRAPPED_SECRETID); "
    "offline static negative-capability matrix validates the same denials "
    "below. LIVE hsl-signer deny tests are NOT RUN in this task "
    "(controller guardrail).",
)
def test_deny_outside_dedicated_mount():
    c = _client_role()
    with pytest.raises(Exception):  # hvac.exceptions.Forbidden offline-equivalent
        c.secrets.kv.v2.read_secret(path="other/runtime/x", mount_point="kv-other")


@pytest.mark.hitl
@pytest.mark.skipif(
    not _live_env(),
    reason="E3 HITL: no live Vault endpoint / HITL-issued SecretID "
    "(controller guardrail); live deny tests NOT RUN.",
)
def test_deny_sys_and_auth_paths():
    c = _client_role()
    for p in ["sys/health", "auth/approle/role/hsl-signer"]:
        with pytest.raises(Exception):
            c.adapter.get(f"/v1/{p}")


@pytest.mark.hitl
@pytest.mark.skipif(
    not _live_env(),
    reason="E3 HITL: no live Vault endpoint / HITL-issued SecretID "
    "(controller guardrail); live deny tests NOT RUN.",
)
def test_deny_other_consumer_transit():
    c = _client_role()
    with pytest.raises(Exception):
        c.secrets.transit.sign_data(
            mount_point="github-transit", name="github-signing", plaintext="eA=="
        )


@pytest.mark.hitl
@pytest.mark.skipif(
    not _live_env(),
    reason="E3 HITL: no live Vault endpoint / HITL-issued SecretID "
    "(controller guardrail); live deny tests NOT RUN.",
)
def test_deny_list_delete_other_mounts():
    c = _client_role()
    with pytest.raises(Exception):
        c.secrets.kv.v2.list_secrets(mount_point="github-kv", path="")


# ---------------------------------------------------------------------------
# 2) Offline / static negative-capability matrix (no Vault runtime, no token,
#    no secrets). Proves the hsl-signer policy cannot reach any path outside
#    its dedicated mount(s), any sys/* / auth/* / identity/* administrative
#    path, other consumers' mounts/transit keys, or any over-broad capability
#    (spec §11.4). Robustness comes from the shared policy linter's semantic
#    parsing — the same comment-stripping + exact-path extraction used by E2.
# ---------------------------------------------------------------------------
from pathlib import Path

from src.isolation.negative_matrix import (
    CONTRACT_GRANTS,
    HSL_KEY,
    HSL_MOUNT,
    build_hsl_negative_matrix,
)
from src.policy_lint.linter import lint_policy_text

_POLICY = Path("policies/hsl/hsl-signer.hcl")
_IDENTITY = "hsl-signer"


def _matrix():
    txt = _POLICY.read_text()
    return build_hsl_negative_matrix(txt, identity=_IDENTITY)


def test_hsl_signer_grants_exactly_contract_paths():
    # The policy may grant ONLY the three canonical HSL contract paths with
    # exactly the contract capabilities. Anything else is over-broad and must
    # fail the isolation proof (spec §11.4 "any capability broader than the
    # contract").
    m = _matrix()
    granted = {(g.path, tuple(sorted(g.capabilities))) for g in m.grants}
    expected = {(p, tuple(sorted(c))) for p, c in CONTRACT_GRANTS.items()}
    assert granted == expected, (
        f"hsl-signer grants differ from contract: "
        f"granted={sorted(granted)} expected={sorted(expected)}"
    )
    assert m.over_broad_grants == [], (
        f"over-broad grants present: {m.over_broad_grants}"
    )


def test_hsl_signer_no_lint_violations():
    # Reuse the E2 linter: no wildcard path and no sudo capability for the
    # normal hsl-signer identity (spec §11.3, §11.4, ADR-013).
    txt = _POLICY.read_text()
    assert lint_policy_text(txt, identity=_IDENTITY) == []


def test_hsl_signer_denies_spec_11_4_matrix():
    # Explicit per-category denial proof covering every spec §11.4 bullet:
    #   - any path outside its dedicated mount(s)
    #   - sys/*, auth/*, identity/* administrative paths
    #   - transit/sign|verify for other consumers' keys
    #   - list/delete/read on other consumers' mounts
    #   - any capability broader than the contract
    m = _matrix()
    cases = [
        # category, request path, capability
        ("outside-dedicated-mount", "kv-other/runtime/x", "read"),
        ("sys-admin", "sys/health", "read"),
        ("sys-admin", "sys/policies/acl", "read"),
        ("auth-admin", "auth/approle/role/hsl-signer", "read"),
        ("auth-admin", "auth/token/lookup-self", "read"),
        ("identity-admin", "identity/entity/id/abc", "read"),
        ("identity-admin", "identity/group/id/xyz", "read"),
        ("secret-tree", "secret/data/foo", "read"),
        ("secret-tree", "secret/foo", "read"),
        ("other-consumer-kv", "github-kv/data/x", "read"),
        ("other-consumer-kv", "github-kv/", "list"),
        ("other-consumer-kv", "github-kv/data/x", "delete"),
        ("other-consumer-transit", "github-transit/sign/github-signing", "update"),
        ("other-consumer-transit", "github-transit/verify/github-signing", "update"),
        ("other-consumer-transit", "grafana-transit/sign/grafana-signing", "update"),
        ("cross-consumer-list-delete", "grafana-kv/data/y", "delete"),
        ("stale-transit-prefix", "transit/sign/hsl-signing", "update"),
        ("stale-transit-prefix", "transit/verify/hsl-signing", "update"),
        ("cross-consumer-keys", "github-transit/keys/github-signing", "read"),
    ]
    for category, path, cap in cases:
        assert not m.is_allowed(path, cap), (
            f"DENIED category leaked through hsl-signer policy: "
            f"[{category}] {path} ({cap}) must be denied but policy allows it"
        )


def test_hsl_signer_matrix_has_representative_denials():
    # The static matrix builder must enumerate the representative denied paths
    # (provenance of the E3 isolation claim), not silently return empty.
    m = _matrix()
    assert len(m.denied_paths) >= 10, (
        f"negative-capability matrix under-populated: {len(m.denied_paths)}"
    )
    # Every denied sample must actually be denied by the policy (consistency
    # between the matrix and the matcher).
    for sample in m.denied_paths:
        assert not m.is_allowed(sample["path"], sample["capability"]), (
            f"matrix sample not denied by matcher: "
            f"{sample['category']} {sample['path']} ({sample['capability']})"
        )


def test_hsl_signer_dedicated_mount_only():
    # Regression guard: every granted path must live under the canonical
    # dedicated HSL transit mount `hsl-transit/`. No grant may leak to any
    # other mount prefix (spec §11.4, §13).
    m = _matrix()
    prefix = f"{HSL_MOUNT}/"
    for g in m.grants:
        assert g.path.startswith(prefix), (
            f"grant outside dedicated hsl mount: {g.path}"
        )
        assert HSL_KEY in g.path, f"grant not bound to hsl-signing key: {g.path}"


def test_matrix_is_non_vacuous_detects_over_broad_policy():
    # Hardening: the matrix must NOT be vacuously green. If a future change
    # leaks a wildcard, extra mount, or broader capability into the policy,
    # build_hsl_negative_matrix must surface it as over_broad AND must no
    # longer deny the corresponding cross-consumer path (so the denial proof
    # fails loudly, never silently passes).
    leaked = """
path "hsl-transit/sign/hsl-signing" { capabilities = ["update"] }
path "hsl-transit/verify/hsl-signing" { capabilities = ["update"] }
path "hsl-transit/keys/hsl-signing" { capabilities = ["read"] }
# leaked broad grant — must be flagged
path "github-transit/sign/github-signing" { capabilities = ["update"] }
"""
    m = build_hsl_negative_matrix(leaked, identity=_IDENTITY)
    assert m.over_broad_grants, "matrix failed to flag leaked cross-consumer grant"
    assert m.is_allowed("github-transit/sign/github-signing", "update"), (
        "matrix matcher inconsistent with its over_broad detection"
    )
    # Consequently the static denial proof for that path would now be violated.
    assert any(
        d["path"] == "github-transit/sign/github-signing" and d["capability"] == "update"
        for d in m.denied_paths
    ) is False, "leaked grant should no longer be denied"


def test_matrix_detects_comment_only_policy_as_empty():
    # Hardening: a policy whose only statements are inside comments must parse
    # to zero active grants, so the denial proof cannot be satisfied by
    # comment text (semantic parsing, not naive substring).
    commented = """
# path "sys/*" { capabilities = ["sudo"] }
# path "auth/*" { capabilities = ["update"] }
# Explicitly NO path "sys/*", NO path "auth/*", NO other consumers' mounts.
"""
    m = build_hsl_negative_matrix(commented, identity=_IDENTITY)
    assert m.grants == [], "commented-out policy must yield no active grants"
    assert m.is_allowed("sys/health", "read") is False
