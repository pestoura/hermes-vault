"""Fail-closed lifecycle state-machine tests (spec §16, plan Task G1).

Repo-side only: pure state/transition logic, NO Vault runtime, NO credentials,
NO live checks. Live/runtime evidence (restore drill, audit device, unseal
quorum) is treated as NOT_PROVEN unless explicitly supplied by an operator step.
"""

from src.lifecycle.states import (
    ServiceState,
    allowed,
    promotion_ready,
    request_capability,
)


# --- Plan Task G1 mandated assertions ---------------------------------------


def test_sealed_denies_capability():
    assert request_capability(ServiceState.INITIALIZED_SEALED, principal="hsl-signer") is False


def test_error_blocks_promotion():
    assert allowed(ServiceState.ERROR, to="UNSEALED_READY") is False


def test_audit_down_blocks_promotion():
    assert request_capability(ServiceState.UNSEALED_READY, audit_enabled=False) is False


# --- Fail-closed: the single grant path -------------------------------------


def test_unsealed_ready_with_audit_enables():
    assert request_capability(ServiceState.UNSEALED_READY, audit_enabled=True) is True


# --- Fail-closed hardening: invalid/unrecognized input never enables --------


def test_unrecognized_state_denies_capability():
    # Any unrecognized/invalid state must NOT promote or enable anything.
    assert request_capability("TOTALLY_BOGUS") is False
    assert request_capability(12345) is False
    assert allowed("TOTALLY_BOGUS", to="UNSEALED_READY") is False
    assert allowed(ServiceState.UNSEALED_READY, to="TOTALLY_BOGUS") is False


def test_only_unsealed_ready_with_audit_serves():
    # Every non-serving state denies capability regardless of audit flag.
    for st in (
        ServiceState.UNINITIALIZED,
        ServiceState.INITIALIZED_SEALED,
        ServiceState.ERROR,
        ServiceState.DECOMMISSIONED,
    ):
        assert request_capability(st) is False
        assert request_capability(st, audit_enabled=True) is False


# --- Fail-closed hardening: no auto-promotion -------------------------------


def test_no_auto_promotion_without_explicit_proof():
    # Production-readiness must never be auto-derived from a serving state alone.
    assert promotion_ready(ServiceState.UNSEALED_READY) is False
    assert promotion_ready(ServiceState.UNSEALED_READY, restore_drill_passed=True) is False
    assert (
        promotion_ready(
            ServiceState.UNSEALED_READY,
            restore_drill_passed=True,
            audit_passed=True,
            owner_signoff=True,
        )
        is True
    )


def test_degraded_state_never_promotes():
    # A degraded/terminal state is never promotion-ready, even with full proof.
    assert (
        promotion_ready(
            ServiceState.ERROR,
            restore_drill_passed=True,
            audit_passed=True,
            owner_signoff=True,
        )
        is False
    )
    assert (
        promotion_ready(
            ServiceState.DECOMMISSIONED,
            restore_drill_passed=True,
            audit_passed=True,
            owner_signoff=True,
        )
        is False
    )


# --- Fail-closed hardening: frozen default runtime state --------------------


def test_frozen_default_state_serves_nothing():
    # The initial frozen runtime state (UNINITIALIZED) enables no capability and
    # is not auto-promoted. Live proof is required and is absent repo-side.
    assert request_capability(ServiceState.UNINITIALIZED) is False
    assert request_capability(ServiceState.UNINITIALIZED, audit_enabled=True) is False
    assert promotion_ready(ServiceState.UNINITIALIZED) is False
