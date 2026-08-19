"""Static negative-capability matrix for per-consumer isolation (spec §11.4).

This module performs pure-text analysis of a Vault policy HCL. It performs no
network or Vault access and never handles secret material. Its job is to prove
that a consumer AppRole policy can reach ONLY its contract paths and is
therefore denied every administrative / cross-consumer / over-broad path
enumerated in spec §11.4 (the HSL negative-capability matrix, Task E3).

Semantic parsing reuses the shared policy linter's ``_strip_comments``
preprocessor, so commented-out capabilities/paths are ignored and active quoted
paths keep their meaning. We deliberately do NOT rely on naive raw-substring
checks against the raw policy text: matching is path-aware and capability-aware.
"""

import re
from dataclasses import dataclass, field

from src.policy_lint.linter import _strip_comments

# Canonical HSL contract (spec §13, E1/E2): dedicated HSL Transit mount + key.
HSL_MOUNT = "hsl-transit"
HSL_KEY = "hsl-signing"

# Exact path -> capabilities granted by the hsl-signer policy (spec §11.3).
# This is the single source of truth for "what hsl-signer MAY do".
CONTRACT_GRANTS: dict[str, list[str]] = {
    "hsl-transit/sign/hsl-signing": ["update"],
    "hsl-transit/verify/hsl-signing": ["update"],
    "hsl-transit/keys/hsl-signing": ["read"],
}

# Path-block + capabilities extraction (same semantics as the E2 linter).
_PATH_BLOCK = re.compile(r'path\s*"([^"]*)"\s*\{', re.IGNORECASE)
_CAPABILITIES = re.compile(r'capabilities\s*=\s*\[(.*?)\]', re.IGNORECASE | re.DOTALL)

# Representative denied paths covering every spec §11.4 denial category. Used
# for provenance of the E3 isolation claim and validated against the parsed
# grants by ``build_hsl_negative_matrix``.
SPEC_DENIALS: list[dict] = [
    # any path outside its dedicated mount(s)
    {"category": "outside-dedicated-mount", "path": "kv-other/runtime/x", "capability": "read"},
    {"category": "outside-dedicated-mount", "path": "kv-hsl/data/x", "capability": "read"},
    # sys/* administrative paths
    {"category": "sys-admin", "path": "sys/health", "capability": "read"},
    {"category": "sys-admin", "path": "sys/policies/acl", "capability": "read"},
    {"category": "sys-admin", "path": "sys/seal", "capability": "update"},
    # auth/* administrative paths
    {"category": "auth-admin", "path": "auth/approle/role/hsl-signer", "capability": "read"},
    {"category": "auth-admin", "path": "auth/token/lookup-self", "capability": "read"},
    {"category": "auth-admin", "path": "auth/approle/login", "capability": "update"},
    # identity/* administrative paths
    {"category": "identity-admin", "path": "identity/entity/id/abc", "capability": "read"},
    {"category": "identity-admin", "path": "identity/group/id/xyz", "capability": "read"},
    # shared secret/* tree (no consumer may touch it)
    {"category": "secret-tree", "path": "secret/data/foo", "capability": "read"},
    {"category": "secret-tree", "path": "secret/foo", "capability": "read"},
    # list/delete/read on other consumers' KV mounts
    {"category": "other-consumer-kv", "path": "github-kv/data/x", "capability": "read"},
    {"category": "other-consumer-kv", "path": "github-kv/", "capability": "list"},
    {"category": "other-consumer-kv", "path": "github-kv/data/x", "capability": "delete"},
    {"category": "other-consumer-kv", "path": "grafana-kv/data/y", "capability": "delete"},
    # transit/sign|verify for other consumers' keys
    {"category": "other-consumer-transit", "path": "github-transit/sign/github-signing", "capability": "update"},
    {"category": "other-consumer-transit", "path": "github-transit/verify/github-signing", "capability": "update"},
    {"category": "other-consumer-transit", "path": "grafana-transit/sign/grafana-signing", "capability": "update"},
    # other consumers' transit keys metadata
    {"category": "other-consumer-keys", "path": "github-transit/keys/github-signing", "capability": "read"},
    # stale transit/ prefix (plan draft) — must not match the canonical mount
    {"category": "stale-transit-prefix", "path": "transit/sign/hsl-signing", "capability": "update"},
    {"category": "stale-transit-prefix", "path": "transit/verify/hsl-signing", "capability": "update"},
]


@dataclass
class Grant:
    """A single parsed ``path { capabilities = [...] }`` block."""

    path: str
    capabilities: list[str]


@dataclass
class PolicyMatrix:
    """Parsed policy + the negative-capability result for one identity."""

    identity: str
    grants: list[Grant] = field(default_factory=list)
    over_broad_grants: list[Grant] = field(default_factory=list)
    denied_paths: list[dict] = field(default_factory=list)

    def is_allowed(self, path: str, capability: str) -> bool:
        """Return True iff the parsed policy grants ``capability`` on ``path``.

        Uses Vault path semantics: a trailing ``*`` is a prefix wildcard;
        otherwise the path must match exactly. Capability must be present in
        the matched block.
        """
        for g in self.grants:
            if _path_matches(g.path, path) and capability in g.capabilities:
                return True
        return False


def _path_matches(grant_path: str, request_path: str) -> bool:
    if grant_path.endswith("*"):
        return request_path.startswith(grant_path[:-1])
    return grant_path == request_path


def _parse_capabilities(raw: str) -> list[str]:
    caps: list[str] = []
    for tok in raw.split(","):
        tok = tok.strip().strip('"').strip()
        if tok:
            caps.append(tok)
    return caps


def parse_policy_grants(text: str) -> list[Grant]:
    """Extract ``(path, capabilities)`` grants, ignoring HCL comments.

    Each ``path "..." { ... }`` block is paired with the next ``capabilities =
    [...]`` block found after it (HCL ordering). Comment stripping happens
    first via the shared linter, so commented-out blocks are excluded.
    """
    clean = _strip_comments(text)
    grants: list[Grant] = []
    for m in _PATH_BLOCK.finditer(clean):
        path = m.group(1)
        cap_m = _CAPABILITIES.search(clean, m.end())
        caps = _parse_capabilities(cap_m.group(1)) if cap_m else []
        grants.append(Grant(path=path, capabilities=caps))
    return grants


def build_hsl_negative_matrix(text: str, identity: str = "hsl-signer") -> PolicyMatrix:
    """Build the HSL negative-capability matrix from a policy HCL string.

    Returns a :class:`PolicyMatrix` whose ``grants`` are the parsed contract
    grants, ``over_broad_grants`` are any grants not in ``CONTRACT_GRANTS``
    (spec §11.4 "any capability broader than the contract"), and
    ``denied_paths`` are the ``SPEC_DENIALS`` samples proven denied by the
    parsed policy.
    """
    grants = parse_policy_grants(text)
    contract = {(p, tuple(sorted(c))) for p, c in CONTRACT_GRANTS.items()}
    over_broad = [
        g
        for g in grants
        if (g.path, tuple(sorted(g.capabilities))) not in contract  # noqa: E501
    ]
    matrix = PolicyMatrix(
        identity=identity,
        grants=grants,
        over_broad_grants=over_broad,
        denied_paths=[],
    )
    matrix.denied_paths = [
        s for s in SPEC_DENIALS if not matrix.is_allowed(s["path"], s["capability"])
    ]
    return matrix
