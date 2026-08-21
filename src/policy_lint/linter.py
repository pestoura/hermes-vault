"""Static policy linter for Hermes Shared Vault policies.

This module performs pure-text analysis of Vault policy HCL. It performs no
network or Vault access and never handles secret material. Its only job is to
fail any committed policy that grants a wildcard path or the ``sudo`` capability
to a non-admin identity, satisfying spec S11.4, S21.2 and ADR-013.

Behaviour (derived from the task objective, not copied blindly from any plan
regex):

* A ``path "..."`` statement whose quoted path contains ``*`` is a wildcard path
  and is forbidden for normal identities.
* A ``capabilities = [ ..., "sudo", ... ]`` block grants the ``sudo`` capability
  and is forbidden for identities other than ``hermes-vault-admin``.
* The exact-path case ``hsl-transit/sign/hsl-signing`` with ``update`` is
  accepted (returns no issues).
* ``hermes-vault-admin`` is the only exempt identity (JIT admin, ADR-013).
"""

import re

# Match a Vault policy path block and capture the quoted path string.
_PATH_BLOCK = re.compile(r'path\s*"([^"]*)"\s*\{', re.IGNORECASE)

# Match a capabilities assignment and capture everything between the brackets.
_CAPABILITIES = re.compile(r'capabilities\s*=\s*\[(.*?)\]', re.IGNORECASE | re.DOTALL)

# Comment stripping must not touch quoted strings (active paths/capabilities),
# so double-quoted literals are stashed before any comment marker is removed.
_QUOTED = re.compile(r'"[^"]*"')
_BLOCK_COMMENT = re.compile(r'/\*.*?\*/', re.DOTALL)
_LINE_COMMENT = re.compile(r'(?:#|//)[^\n]*')

ADMIN_IDENTITY = "hermes-vault-admin"


def _strip_comments(text: str) -> str:
    """Remove HCL ``#``/``//`` line comments and ``/* ... */`` block comments.

    Quoted strings are preserved verbatim so a path such as ``secret/*`` or a
    capability literal keeps its active meaning. This is deliberately a minimal
    preprocessor, not a full HCL parser.
    """
    store: list[str] = []

    def _stash(match: re.Match) -> str:
        store.append(match.group(0))
        return f"\x00Q{len(store) - 1}\x00"

    protected = _QUOTED.sub(_stash, text)
    protected = _BLOCK_COMMENT.sub("", protected)
    protected = _LINE_COMMENT.sub("", protected)

    def _restore(match: re.Match) -> str:
        return store[int(match.group(1))]

    return re.sub(r"\x00Q(\d+)\x00", _restore, protected)


def lint_policy_text(text: str, identity: str) -> list[str]:
    """Return human-readable policy violations.

    An empty list means the policy is clean for the given identity. Admin
    identities are exempt from the wildcard and sudo bans; every other
    identity is never exempt.
    """
    issues: list[str] = []
    is_admin = identity == ADMIN_IDENTITY

    # Strip comments before analysis so commented-out capabilities/paths are
    # never flagged. Active (uncommented) tokens are unchanged by this pass.
    text = _strip_comments(text)

    for match in _PATH_BLOCK.finditer(text):
        path = match.group(1)
        if "*" in path and not is_admin:
            issues.append(
                f"wildcard path forbidden for identity={identity}: "
                f"path contains '*' which violates least-privilege (spec S11.4)"
            )

    for match in _CAPABILITIES.finditer(text):
        capabilities = match.group(1)
        if '"sudo"' in capabilities and not is_admin:
            issues.append(
                f"sudo capability forbidden for non-admin identity={identity} "
                f"(ADR-013)"
            )

    return issues
