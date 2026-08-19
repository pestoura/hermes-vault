"""Fail-closed lifecycle state machine (spec §16, plan Task G1).

Repo-side logic only. There is NO Vault runtime, NO credentials, and NO live
evidence here. Per spec §16.3, every guard fails CLOSED: an unrecognized or
degraded state enables and promotes NOTHING. Promotion is operator sign-off
only — never auto-derived.

Source of truth: docs/specs/2026-08-18-hermes-shared-vault-service-design.md §16.
"""

from enum import StrEnum


class ServiceState(StrEnum):
    """Service lifecycle states (spec §16.1).

    Any unrecognized value resolves to ERROR so invalid input can never
    promote or enable anything (fail-closed, spec §16.3).
    """

    UNINITIALIZED = "UNINITIALIZED"
    INITIALIZED_SEALED = "INITIALIZED_SEALED"
    UNSEALED_READY = "UNSEALED_READY"
    ERROR = "ERROR"
    DECOMMISSIONED = "DECOMMISSIONED"

    @classmethod
    def _missing_(cls, value):
        # Fail-closed: an unrecognized string/value is treated as degraded.
        return cls.ERROR


# Known member names/values, for strict target validation in `allowed`.
_VALID_MEMBERS = frozenset(m.value for m in ServiceState)

# Allowed forward transitions per spec §16.1 entry conditions.
_ALLOWED: dict[ServiceState, frozenset[ServiceState]] = {
    ServiceState.UNINITIALIZED: frozenset({ServiceState.INITIALIZED_SEALED}),
    ServiceState.INITIALIZED_SEALED: frozenset({ServiceState.UNSEALED_READY, ServiceState.ERROR}),
    ServiceState.UNSEALED_READY: frozenset({ServiceState.ERROR, ServiceState.DECOMMISSIONED}),
    ServiceState.ERROR: frozenset({ServiceState.UNINITIALIZED, ServiceState.INITIALIZED_SEALED}),
    ServiceState.DECOMMISSIONED: frozenset(),
}


def allowed(state, to) -> bool:
    """True iff the transition state -> to is an explicitly permitted edge.

    Invalid/unrecognized states or targets are fail-closed to False. An
    unrecognized target must NOT silently degrade into a valid state (e.g. the
    ERROR edge): only a known member value/name is accepted.
    """
    state = ServiceState(state)
    if isinstance(to, ServiceState):
        target = to
    elif to in _VALID_MEMBERS:
        target = ServiceState(to)
    else:
        return False
    return target in _ALLOWED[state]


def request_capability(state, principal=None, audit_enabled=None) -> bool:
    """Fail-closed capability gate (spec §16.3).

    A capability may be served ONLY from UNSEALED_READY with audit enabled.
    Sealed, uninitialized, degraded, and decommissioned states deny — and so
    does any state with the audit device unavailable (spec §16.3: audit down
    blocks promotion/real-secret use). Any unrecognized state resolves to ERROR
    and is denied.
    """
    state = ServiceState(state)
    if state != ServiceState.UNSEALED_READY:
        return False
    if audit_enabled is not None and not audit_enabled:
        return False
    return True


def promotion_ready(state, restore_drill_passed=False, audit_passed=False, owner_signoff=False) -> bool:
    """Production-readiness gate. NEVER auto-promotes (spec §16.3, ADR-012).

    Requires the service to be UNSEALED_READY AND all three independent proofs:
    restore drill PASS + audit PASS + owner sign-off. Degraded/terminal states
    are never promotion-ready regardless of proof.
    """
    state = ServiceState(state)
    if state != ServiceState.UNSEALED_READY:
        return False
    return bool(restore_drill_passed and audit_passed and owner_signoff)
