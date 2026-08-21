# tests/isolation/test_ownership_boundary.py
#
# Task I1 — Ownership boundary: hermes-vault owns the canonical Vault service;
# no consumer-owned (HSL) deployment replica is created inside this repo.
#
# Offline/static only. No Vault started, no token/key/secret, no remote contact,
# no HSL mutation. The HSL `deployment/vault-lab-l1` pattern is generalized INTO
# this shared service (deployments/vault/) as a read-only reference; HSL does NOT
# re-own the result (spec §15/§17). This test is the repo-side I1 GREEN evidence.
#
# It also guards the E1/E2/H1 contracts so I1 cannot silently regress them:
#   * E1 (spec §13): hsl-transit/ mount + hsl-signing key, provider-owned.
#   * E2 (spec §11.2-§11.3): hsl-signer AppRole, exact-path, provider-owned.
#   * H1 (INV-8/INV-10): secret-zero live issuance stays HITL / NOT_RUN.
import re
from pathlib import Path

import pytest

_REPO = Path(".")
_DEPLOYMENTS_VAULT = Path("deployments/vault")
# The exact replica paths the brief forbids (ownership boundary).
_HSL_REPLICA_DIRS = [
    Path("deployment/vault-lab-l1"),
    Path("deployments/vault-lab-l1"),
]
_RUNBOOK = Path("docs/runbooks/hsl-generalization.md")
_README = Path("README.md")

# Provider-owned enable artifacts that carry the shared-ownership contract
# (preserve E1/E2: hsl-transit/hsl-signing, hsl-signer AppRole exact-path).
_E1_SCRIPT = Path("deployments/vault/scripts/enable-hsl-transit.sh")
_E2_SCRIPT = Path("deployments/vault/scripts/enable-hsl-signer.sh")
_H1_RUNBOOK = Path("docs/runbooks/secret-zero.md")

# Canonical service artifacts that must exist for deployments/vault/ to "own" it.
_VAULT_REQUIRED = [
    Path("deployments/vault/Dockerfile"),
    Path("deployments/vault/docker-compose.yml"),
    Path("deployments/vault/config/vault.hcl"),
    Path("deployments/vault/scripts/bootstrap-checklist.sh"),
]


def _repo_paths(exclude=(".git", ".venv", ".pytest_cache", "__pycache__")):
    for p in Path(".").rglob("*"):
        if any(seg in exclude for seg in p.parts):
            continue
        yield p


# ---------------------------------------------------------------------------
# 1) Canonical service ownership — deployments/vault/ owns the service.
# ---------------------------------------------------------------------------
def test_deployments_vault_owns_canonical_service():
    # The shared Vault service deployment lives here and is owned by hermes-vault.
    assert _DEPLOYMENTS_VAULT.is_dir(), "canonical deployment dir missing: deployments/vault/"
    missing = [str(f) for f in _VAULT_REQUIRED if not f.is_file()]
    assert not missing, f"canonical service artifact(s) missing: {missing}"


# ---------------------------------------------------------------------------
# 2) No HSL vault-lab-l1 replica inside this repo (ownership boundary).
# ---------------------------------------------------------------------------
def test_no_hsl_vault_lab_l1_replica_dirs():
    # The two exact replica paths the brief forbids must not exist.
    present = [str(d) for d in _HSL_REPLICA_DIRS if d.exists()]
    assert not present, f"HSL vault-lab-l1 replica present: {present}"


def test_no_vault_lab_l1_artifact_anywhere():
    # Stronger proof: no file or directory named vault-lab-l1 anywhere in the
    # tracked tree (excluding tooling dirs). Catches deployment/ and
    # deployments/ variants, rename attempts, and stray references-as-paths.
    bad = [str(p) for p in _repo_paths() if "vault-lab-l1" in p.name.lower()]
    assert not bad, f"vault-lab-l1 artifact present in hermes-vault tree: {bad}"


# ---------------------------------------------------------------------------
# 3) I1 artifacts exist and record hermes-vault ownership (no HSL re-own).
# ---------------------------------------------------------------------------
def test_hsl_generalization_runbook_exists():
    assert _RUNBOOK.is_file(), f"missing I1 runbook: {_RUNBOOK}"


def test_runbook_records_hermes_vault_ownership_and_no_replica():
    text = _RUNBOOK.read_text()
    low = text.lower()
    # Ownership stays with hermes-vault.
    assert "hermes-vault" in low, "runbook must name hermes-vault as owner"
    assert ("owns" in low or "ownership" in low), "runbook must state ownership"
    # Read-only reference to the HSL lab pattern.
    assert "vault-lab-l1" in low, "runbook must reference the HSL lab pattern"
    # Explicit no-replica rule.
    assert "deployment/vault-lab-l1" in text, "runbook must name the forbidden replica path"
    assert ("not created" in low or "no " in low and "replica" in low), \
        "runbook must state no replica is created in this repo"
    # Mapping covers the lifted patterns -> shared artifacts.
    for artifact in ("deployments/vault", "hsl-transit", "hsl-signer", "secret-zero"):
        assert artifact in text, f"runbook mapping missing artifact: {artifact}"


def test_readme_records_hsl_supersession_and_hermes_vault_ownership():
    text = _README.read_text()
    low = text.lower()
    assert "superseded" in low, "README must state HSL deployment is superseded for target arch"
    assert "hermes-vault" in low, "README must name hermes-vault"
    assert "owns" in low, "README must state hermes-vault owns the service"


# ---------------------------------------------------------------------------
# 4) E1/E2/H1 contracts preserved (I1 must not regress them).
# ---------------------------------------------------------------------------
def test_e1_e2_scripts_remain_provider_owned_and_no_replica():
    # E1/E2 scripts may mention `vault-lab-l1` only as a READ-ONLY prose
    # reference (allowed by the E1 contract — the brief itself references it).
    # The hard boundary: they must NEVER create/clone an HSL-owned replica
    # (mkdir/cp/rsync/target path into a vault-lab-l1 dir).
    _creation_cmds = ("mkdir", "cp -r", "cp ", "rsync", "ln -s", "ln -", "git clone")
    for script in (_E1_SCRIPT, _E2_SCRIPT):
        assert script.is_file(), f"provider-owned enable script missing: {script}"
        src = script.read_text()
        low = src.lower()
        # Shared-ownership / provider-owned contract preserved (E1/E2).
        assert ("shared ownership" in low or "provider-owned" in low
                or "hermes-vault owns" in low), \
            f"{script} must record the shared-ownership / provider-owned contract"
        # No replica-creation command targeting vault-lab-l1.
        for cmd in _creation_cmds:
            for line in src.splitlines():
                if cmd in line.lower() and "vault-lab-l1" in line.lower():
                    raise AssertionError(
                        f"{script} must not create an HSL vault-lab-l1 replica: {line!r}"
                    )


def test_e1_e2_scripts_remain_hitl_and_data_free():
    # HITL refusal + no live/secret ops (preserves E1/E2 HITL boundary).
    for script in (_E1_SCRIPT, None):
        pass
    for script in (_E1_SCRIPT, _E2_SCRIPT):
        src = script.read_text()
        assert "HITL REFUSES" in src, f"{script} must refuse unattended execution"
        assert re.search(r"exit 1", src), f"{script} must fail-closed without operator ACK"
        for forbidden in ("vault operator init", "vault operator unseal",
                          "vault server", "vault token create", "secret-id"):
            assert forbidden not in src, f"{script} contains forbidden live/secret op: {forbidden!r}"


def test_h1_secret_zero_runbook_remains_hitl_not_run():
    # H1 contract: live SecretID issuance/wrapping stays HITL / NOT_RUN.
    assert _H1_RUNBOOK.is_file(), f"missing H1 runbook: {_H1_RUNBOOK}"
    text = _H1_RUNBOOK.read_text()
    low = text.lower()
    assert "not_run" in low or "not run" in low, "secret-zero runbook must record live step as NOT_RUN"
    assert "hitl" in low or "operator" in low, "secret-zero runbook must be operator/HITL only"
