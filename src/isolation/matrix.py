"""Reusable negative-capability matrix builder (spec §11, §12 — Task E4).

Task E4 generalizes the E3 hsl-signer negative matrix so the SAME spec §11.4
denials are generated for ANY future consumer (github, grafana, ...) WITHOUT
namespaces. The builder is fed a :class:`ConsumerContract` and emits a static
list of :class:`NegativeCase` objects covering every spec §11.4 denial
category, parametrized purely from the contract.

The matcher reuses E3 semantics exactly: ``parse_policy_grants`` (the shared
policy linter's comment-stripping + exact-path extraction) and
``PolicyMatrix.is_allowed`` (Vault path semantics: trailing ``*`` is a prefix
wildcard, otherwise exact match; capability must be present). No Vault runtime,
no token, no secrets — pure static text analysis.
"""

from dataclasses import dataclass, field
from typing import Iterable

from src.isolation.negative_matrix import (
    Grant,
    PolicyMatrix,
    parse_policy_grants,
)


@dataclass(frozen=True)
class NegativeCase:
    """One expected-denied request derived from a consumer contract."""

    category: str
    path: str
    capability: str


@dataclass
class ConsumerContract:
    """Provider-neutral per-consumer isolation contract (spec §11, §14).

    Mirrors the E3 ``CONTRACT_GRANTS``/``HSL_MOUNT``/``HSL_KEY`` shape but
    generalizes it so the matrix builder is parametrized, not hard-coded.
    """

    identity: str
    dedicated_mounts: tuple[str, ...]
    key: str
    grants: dict[str, tuple[str, ...]]
    other_consumers: tuple[str, ...] = field(default_factory=tuple)


def _dedicated_prefixes(contract: ConsumerContract) -> list[str]:
    return [f"{m}/" for m in contract.dedicated_mounts]


def build_negative_cases(contract: ConsumerContract) -> list[NegativeCase]:
    """Build the spec §11.4 negative-capability matrix for ``contract``.

    Returns the list of :class:`NegativeCase` that the consumer MUST be denied.
    Coverage mirrors E3 ``SPEC_DENIALS`` but is synthesized from the contract
    so it is reusable for every consumer without namespaces.
    """
    identity = contract.identity
    key = contract.key
    cases: list[NegativeCase] = []

    # 1) any path outside its dedicated mount(s).
    cases.append(NegativeCase("outside-dedicated-mount", "kv-other/runtime/x", "read"))
    cases.append(NegativeCase("outside-dedicated-mount", f"kv-{identity}/data/x", "read"))

    # 2) sys/* administrative paths.
    cases.append(NegativeCase("sys-admin", "sys/health", "read"))
    cases.append(NegativeCase("sys-admin", "sys/policies/acl", "read"))
    cases.append(NegativeCase("sys-admin", "sys/seal", "update"))

    # 3) auth/* administrative paths (incl. the consumer's own AppRole role).
    cases.append(NegativeCase("auth-admin", f"auth/approle/role/{identity}", "read"))
    cases.append(NegativeCase("auth-admin", "auth/token/lookup-self", "read"))
    cases.append(NegativeCase("auth-admin", "auth/approle/login", "update"))

    # 4) identity/* administrative paths.
    cases.append(NegativeCase("identity-admin", "identity/entity/id/abc", "read"))
    cases.append(NegativeCase("identity-admin", "identity/group/id/xyz", "read"))

    # 5) shared secret/* tree (no consumer may touch it).
    cases.append(NegativeCase("secret-tree", "secret/data/foo", "read"))
    cases.append(NegativeCase("secret-tree", "secret/foo", "read"))

    # 6-8) every other consumer's mounts/transit keys (cross-consumer isolation).
    for oc in contract.other_consumers:
        cases.append(NegativeCase("other-consumer-kv", f"{oc}-kv/data/x", "read"))
        cases.append(NegativeCase("other-consumer-kv", f"{oc}-kv/", "list"))
        cases.append(NegativeCase("other-consumer-kv", f"{oc}-kv/data/x", "delete"))
        cases.append(NegativeCase("other-consumer-kv", f"{oc}-kv/data/y", "delete"))
        cases.append(
            NegativeCase("other-consumer-transit", f"{oc}-transit/sign/{oc}-signing", "update")
        )
        cases.append(
            NegativeCase(
                "other-consumer-transit", f"{oc}-transit/verify/{oc}-signing", "update"
            )
        )
        cases.append(
            NegativeCase("other-consumer-keys", f"{oc}-transit/keys/{oc}-signing", "read")
        )

    # 9) stale ``transit/`` prefix (plan draft) — must NOT match the canonical
    #    dedicated ``<mount>/`` prefix.
    cases.append(NegativeCase("stale-transit-prefix", f"transit/sign/{key}", "update"))
    cases.append(NegativeCase("stale-transit-prefix", f"transit/verify/{key}", "update"))

    return cases


def evaluate_cases(
    cases: Iterable[NegativeCase], policy_text: str
) -> list[NegativeCase]:
    """Return the subset of ``cases`` the parsed ``policy_text`` ALLOWS.

    Empty result == the policy denies every generated case (the desired
    isolation proof). Reuses E3 ``PolicyMatrix.is_allowed`` semantics; matching
    depends only on the parsed grants, not the identity label.
    """
    cases = list(cases)
    if not cases:
        return []
    matrix = PolicyMatrix(identity="eval", grants=parse_policy_grants(policy_text))
    violations: list[NegativeCase] = []
    for c in cases:
        if matrix.is_allowed(c.path, c.capability):
            violations.append(c)
    return violations
