# tests/isolation/test_matrix_framework.py
#
# Task E4 — Reusable consumer-isolation negative-capability framework (spec §11, §12).
#
# Proves the SAME spec §11.4 negative matrix is reusable for every future
# consumer (github, grafana, ...) WITHOUT namespaces. The builder is fed the
# canonical HSL contract fixture and the generated denial cases must be denied
# generically by the committed `policies/hsl/hsl-signer.hcl` policy. No Vault
# runtime, no token, no secrets — pure static semantic matching (reuses E3
# path/capability matcher). This is the repo-side E4 GREEN evidence.
from pathlib import Path

import pytest

from src.isolation.matrix import (
    ConsumerContract,
    NegativeCase,
    build_negative_cases,
    evaluate_cases,
)

_POLICY = Path("policies/hsl/hsl-signer.hcl")
_IDENTITY = "hsl-signer"

# Canonical HSL contract (spec §13, E1/E2): dedicated HSL Transit mount + key.
# Mirrors src/isolation/negative_matrix.CONTRACT_GRANTS so E4 reuses the exact
# same E3 grant semantics.
HSL_CONTRACT = ConsumerContract(
    identity=_IDENTITY,
    dedicated_mounts=("hsl-transit",),
    key="hsl-signing",
    grants={
        "hsl-transit/sign/hsl-signing": ("update",),
        "hsl-transit/verify/hsl-signing": ("update",),
        "hsl-transit/keys/hsl-signing": ("read",),
    },
    other_consumers=("github", "grafana"),
)

# spec §11.4 denial categories the reusable matrix must cover for any consumer.
EXPECTED_CATEGORIES = {
    "outside-dedicated-mount",
    "sys-admin",
    "auth-admin",
    "identity-admin",
    "secret-tree",
    "other-consumer-kv",
    "other-consumer-transit",
    "other-consumer-keys",
    "stale-transit-prefix",
}


@pytest.fixture
def hsl_cases():
    return build_negative_cases(HSL_CONTRACT)


@pytest.fixture
def hsl_policy_text():
    return _POLICY.read_text()


def test_builder_covers_all_spec_11_4_categories(hsl_cases):
    # The reusable matrix must enumerate EVERY spec §11.4 denial category for
    # the HSL contract, not a silent subset.
    seen = {c.category for c in hsl_cases}
    missing = EXPECTED_CATEGORIES - seen
    assert not missing, f"missing spec §11.4 denial categories: {sorted(missing)}"
    # No category outside the contract's known set (no scope creep).
    extra = seen - EXPECTED_CATEGORIES
    assert not extra, f"unexpected denial categories: {sorted(extra)}"


def test_builder_is_non_vacuous(hsl_cases):
    # The matrix must be populated; an empty builder would make the denial
    # proof vacuously green.
    assert len(hsl_cases) >= 15, f"negative matrix under-populated: {len(hsl_cases)}"


def test_hsl_contract_denies_every_generated_case(hsl_cases, hsl_policy_text):
    # Core E4 claim: feeding the HSL contract into the reusable builder yields
    # the SAME denials generically, and the real hsl-signer policy denies all
    # of them. evaluate_cases returns the failures; empty == all denied.
    violations = evaluate_cases(hsl_cases, hsl_policy_text)
    assert violations == [], (
        "reusable negative matrix leaked through hsl-signer policy:\n"
        + "\n".join(f"  [{c.category}] {c.path} ({c.capability})" for c in violations)
    )


def test_same_denials_as_e3_matrix(hsl_cases):
    # The reusable builder must reproduce the per-category denials asserted by
    # E3 (tests/isolation/test_hsl_negative_capability.py), expressed
    # generically from the contract. Spot-check the representative paths.
    path_set = {(c.path, c.capability) for c in hsl_cases}
    expected_representative = {
        ("sys/health", "read"),
        ("auth/approle/role/hsl-signer", "read"),
        ("auth/token/lookup-self", "read"),
        ("identity/entity/id/abc", "read"),
        ("secret/data/foo", "read"),
        ("github-transit/sign/github-signing", "update"),
        ("github-transit/verify/github-signing", "update"),
        ("grafana-kv/data/y", "delete"),
        ("github-transit/keys/github-signing", "read"),
        ("transit/sign/hsl-signing", "update"),
        ("transit/verify/hsl-signing", "update"),
        ("github-kv/data/x", "read"),
        ("github-kv/", "list"),
    }
    missing = expected_representative - path_set
    assert not missing, f"reusable matrix missing E3 representative denials: {sorted(missing)}"


def test_builder_is_parametrized_not_hardcoded():
    # Reusability guard: a different consumer contract must synthesize that
    # consumer's own denied paths, proving the builder is NOT hard-coded to HSL.
    github = ConsumerContract(
        identity="github-signer",
        dedicated_mounts=("github-transit",),
        key="github-signing",
        grants={
            "github-transit/sign/github-signing": ("update",),
            "github-transit/verify/github-signing": ("update",),
        },
        other_consumers=("hsl", "grafana"),
    )
    cases = build_negative_cases(github)
    paths = {c.path for c in cases}
    # github-specific auth role path must be present (was hsl-signer before).
    assert "auth/approle/role/github-signer" in paths
    # cross-consumer names must reflect github's other_consumers (hsl, grafana).
    assert "hsl-transit/sign/hsl-signing" in paths
    assert "grafana-kv/data/x" in paths
    # and must NOT still reference hsl-signer as the subject role.
    assert "auth/approle/role/hsl-signer" not in paths
