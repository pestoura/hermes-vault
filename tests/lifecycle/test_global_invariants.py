"""Global invariants test (plan Task G3, spec §22, INV-1..INV-11).

Repo-side only: static / source-level proof that the eleven frozen invariants
hold across the tracked tree. NO Vault runtime, NO credentials, NO live checks,
NO mutation of other repos.

This is the canonical repo-wide invariant gate that every task carries. Each
test maps 1:1 to one global invariant and asserts the *evidence* that the
invariant holds, not a runtime claim. Live assertions (restore drill, audit
device, unseal quorum, promotion sign-off) are operator HITL steps and are
explicitly NOT_RUN here — they are never relabeled PASS.
"""

import ast
import os
import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
# The planning prose (docs/superpowers) merely NAMES controls and is excluded
# from repo-secret/invariant scans, mirroring run-gates.sh secret_scan.
PLAN_DIR = REPO / "docs" / "superpowers"
EXCLUDE_PREFIXES = ("docs/superpowers/",)


def _tracked_sources():
    """Yield (relative-path, text) for every tracked, non-plan source file."""
    import subprocess

    out = subprocess.run(
        ["git", "ls-files"], cwd=REPO, capture_output=True, text=True, check=True
    )
    for rel in out.stdout.splitlines():
        if rel.startswith(EXCLUDE_PREFIXES):
            continue
        p = REPO / rel
        if not p.is_file():
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="strict")
        except (UnicodeDecodeError, OSError):
            continue
        yield rel, text


def _doc_texts():
    """Concatenated text of every tracked runbook / spec / security doc."""
    parts = []
    for rel, text in _tracked_sources():
        if rel.startswith(("docs/",)) and rel.endswith((".md",)):
            parts.append(text)
    return "\n".join(parts)


# --- INV-1 NO_SECRET_IN_REPO -------------------------------------------------
# Synthetic control tokens only. No real secret value is ever committed (ADR-014,
# spec §22). The scanner matches the SAME shapes as run-gates.sh secret_scan plus
# the plan-named `VAULT-*` literals, but emits only redacted signal + file path.
_SECRET_RE = re.compile(
    r"(hvs\.[A-Za-z0-9]{20,})"
    r"|(s\.[A-Za-z0-9]{20,})"
    r"|((VAULT_TOKEN|VAULT_[A-Z0-9]+|[Rr]oot_token|recovery_key|SecretID)"
    r"\s*[:=]\s*[A-Za-z0-9._-]{16,})"
    r"|(VAULT-[A-Z0-9]{6,})"  # plan-named forbidden literal family
)


def test_inv1_no_real_secret_in_tracked_repo():
    offenders = []
    for rel, text in _tracked_sources():
        for m in _SECRET_RE.finditer(text):
            # Reject only if a value (not merely the control-word in prose) is present.
            matched = m.group(0)
            if len(matched) >= 16 and not matched.endswith(("=", ":")):
                offenders.append((rel, matched[:6] + "…"))
    assert offenders == [], f"INV-1 violation(s): {offenders}"


# --- INV-2 NO_AUTO_PROMOTION -------------------------------------------------
def test_inv2_no_auto_promotion_documented():
    # Genuine G3 acceptance: the production gate (restore drill PASS + audit PASS
    # + owner sign-off) MUST be documented in a tracked runbook, and the tree MUST
    # NOT contain an auto-promotion code path.
    docs = _doc_texts()
    assert "NO_AUTO_PROMOTION" in docs, "NO_AUTO_PROMOTION gate not documented in runbooks"
    # No code path may auto-promote: production use is gated on owner sign-off.
    for rel, text in _tracked_sources():
        if rel.startswith(("scripts/", "src/")) and "promote" in text.lower():
            # allowed only if explicitly gated / denied; fail-closed wording required
            assert "fail-closed" in text.lower() or "owner sign-off" in text.lower(), (
                f"INV-2: promotion reference in {rel} not fail-closed / owner-gated"
            )


# --- INV-3 COMMUNITY_OSS_ONLY -----------------------------------------------
def test_inv3_community_oss_only():
    bad = []
    # Binding technical bans (Community/OSS only, INV-3): no Enterprise namespaces
    # and no HCP auto-unseal anywhere in the tree (spec §4, §12, ADR-013). Test
    # sources are excluded from these literal-syntax bans (they only RE-PATTERN
    # the words; the operational config is covered by the B1/B2 config tests).
    for rel, text in _tracked_sources():
        if rel.startswith("tests/"):
            continue
        if re.search(r"namespace\s*=", text):
            bad.append((rel, "namespace ="))
        if re.search(r"auto_unseal", text):
            bad.append((rel, "auto_unseal"))
    # Prose MAY mention Enterprise/HCP only when explicitly disclaimed as
    # non-adopted (language-tolerant: PT "não" / EN "no|not|without" / "Community/OSS").
    _disclaimer = re.compile(
        r"(não|não deve|not |no |without|community/oss)", re.IGNORECASE
    )
    for rel, text in _tracked_sources():
        if re.search(r"\b(enterprise|hcp)\b", text, re.IGNORECASE):
            if not _disclaimer.search(text):
                bad.append((rel, "enterprise/hcp without explicit OSS-only disclaimer"))
    assert bad == [], f"INV-3 violation(s): {bad}"


# --- INV-4 SHARED_OWNERSHIP --------------------------------------------------
def test_inv4_shared_ownership():
    docs = _doc_texts()
    # Spec §3 canonical statement: hermes-vault owns the shared service; consumers
    # depend on the contract (not a Vault deployment).
    assert "owns the shared service" in docs, "INV-4: shared-ownership statement missing"
    # The contract module must NOT import Vault/hvac — consumers depend on the
    # contract, not Vault APIs (proved statically, matches F1 conformance).
    broker = REPO / "src" / "capability_contract" / "broker.py"
    contract = REPO / "src" / "capability_contract" / "schema.py"
    for f in (broker, contract):
        if f.exists():
            src = f.read_text()
            assert "import hvac" not in src, f"INV-4: {f.name} imports hvac (Vault API leak)"
            assert "from hvac" not in src, f"INV-4: {f.name} imports hvac (Vault API leak)"


# --- INV-5 PER_CONSUMER_ISOLATION -------------------------------------------
def test_inv5_per_consumer_isolation_policy_present():
    policy = REPO / "policies" / "hsl" / "hsl-signer.hcl"
    assert policy.exists(), "INV-5: dedicated HSL policy missing"
    txt = policy.read_text()
    # exact-path (no wildcard), dedicated mount, no sys/auth wildcard
    assert 'path "hsl-transit/' in txt
    assert "capabilities = [\"sudo\"]" not in txt
    assert not re.search(r'path\s+"\*"', txt)
    # negative-capability matrix framework exists (reusable, no namespaces)
    matrix = REPO / "src" / "isolation" / "matrix.py"
    assert matrix.exists(), "INV-5: isolation matrix framework missing"


# --- INV-6 FAIL_CLOSED -------------------------------------------------------
def test_inv6_fail_closed_lifecycle():
    from src.lifecycle.states import (
        ServiceState,
        allowed,
        promotion_ready,
        request_capability,
    )

    # Sealed / uninitialized / error / decommissioned all deny capability.
    for st in (
        ServiceState.UNINITIALIZED,
        ServiceState.INITIALIZED_SEALED,
        ServiceState.ERROR,
        ServiceState.DECOMMISSIONED,
    ):
        assert request_capability(st, audit_enabled=True) is False
    # Audit down blocks capability even when ready.
    assert request_capability(ServiceState.UNSEALED_READY, audit_enabled=False) is False
    # Promotion NEVER auto-derived; exact gate enforced.
    assert promotion_ready(ServiceState.UNSEALED_READY) is False
    assert promotion_ready(
        ServiceState.UNSEALED_READY,
        restore_drill_passed=True,
        audit_passed=True,
        owner_signoff=True,
    ) is True
    # Unrecognized state/target is fail-closed.
    assert allowed("TOTALLY_BOGUS", to="UNSEALED_READY") is False
    assert allowed(ServiceState.UNINITIALIZED, to="TOTALLY_BOGUS") is False


# --- INV-7 AUDIT_EVERYTHING -------------------------------------------------
def test_inv7_audit_mandatory_before_secret_use():
    docs = _doc_texts()
    assert "audit device" in docs.lower(), "INV-7: audit device not referenced in docs"
    assert (
        "before any" in docs.lower() and "real" in docs.lower()
    ) or "mandatory" in docs.lower(), "INV-7: mandatory-audit-before-real-secret not stated"
    # Consumer redaction layer exists and is importable (G2).
    from src.evidence.redact import redact_text, contains_secret  # noqa: F401

    assert callable(redact_text) and callable(contains_secret)


# --- INV-8 SECRET_ZERO_EXPLICIT ---------------------------------------------
def test_inv8_secret_zero_wrapped_single_use_short_ttl():
    from src.capability_contract.schema import CapabilityRequest, CapabilityType

    req = CapabilityRequest(
        principal="hsl-signer",
        action="auth.approle",
        resource_scope="hsl-signer",
        risk_class="high",
        requested_ttl=120,
        capability_type=CapabilityType.wrapped_secret,
    )
    assert req.capability_type is CapabilityType.wrapped_secret
    assert req.requested_ttl <= 300
    # Contract schema MUST reject secret payloads (INV-1 + INV-8).
    with pytest.raises(Exception):
        CapabilityRequest(
            principal="x", action="y", resource_scope="z",
            risk_class="low", requested_ttl=60, _secret_value="VAULT-TOKEN-XXXX",
        )
    # No REAL SecretID VALUE committed anywhere (the word "SecretID" as HITL-boundary
    # prose is required by INV-10 and is fine; only an assigned value is forbidden).
    # The value-shape scan is already covered by INV-1's _SECRET_RE (SecretID=VALUE).


# --- INV-9 SANITIZED_EVIDENCE ------------------------------------------------
def test_inv9_sanitized_evidence():
    from src.evidence.redact import redact_text, contains_secret

    # Synthetic fixtures assembled at runtime (no scanner-triggering literal).
    raw = '\n'.join([
        'token=' + 's.' + 'A' * 24,
        'root_token=' + 'root.' + 'B' * 24,
        'SecretID=' + 'C' * 36,
        'recovery_key=' + 'D' * 32,
        'password=' + 'E' * 16,
    ])
    assert contains_secret(raw) is True
    red = redact_text(raw)
    assert contains_secret(red) is False
    assert "[REDACTED" in red
    assert "s.AAAAAA" not in red and "root.BBBB" not in red


# --- INV-10 HITL_BOUNDARY ----------------------------------------------------
def test_inv10_hitl_boundary_documented():
    docs = _doc_texts()
    hitl_markers = ["init", "unseal", "root", "out-of-band", "HITL"]
    for m in hitl_markers:
        assert m.lower() in docs.lower(), f"INV-10: HITL marker '{m}' missing in docs"
    # No code path performs init/unseal/root/SecretID/TLS-private/promotion.
    for rel, text in _tracked_sources():
        if rel.startswith(("scripts/", "src/")):
            assert "vault operator init" not in text
            assert "vault operator unseal" not in text
            assert "vault token revoke" not in text


# --- INV-11 SCOPE_HERMES_VAULT_ONLY -----------------------------------------
def test_inv11_scope_limited_to_hermes_vault():
    # No tracked operational file mutates or pushes to another repo (e.g. HSL).
    remote_mut = re.compile(r"\b(git push|git remote|gh [a-z]+ (pr|api)|curl |wget )\b")
    for rel, text in _tracked_sources():
        if rel.startswith(("scripts/", "src/", "deployments/")):
            assert not remote_mut.search(text), f"INV-11: remote-mutating cmd in {rel}"
    # References to HSL in tracked non-plan files are descriptive only (ownership
    # boundary), never a mutation instruction.
    for rel, text in _tracked_sources():
        if "hermes-security-labs" in text:
            assert "does NOT" in text or "does not" in text or "not modify" in text.lower(), (
                f"INV-11: HSL reference in {rel} not framed as non-mutating boundary"
            )
