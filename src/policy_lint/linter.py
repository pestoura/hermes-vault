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
* The exact-path case ``transit/sign/hsl-transit/hsl-signing`` with ``update`` is
  accepted (returns no issues).
* ``hermes-vault-admin`` is the only exempt identity (JIT admin, ADR-013).
"""

import re

# Match a Vault policy path block and capture the quoted path string.
_PATH_BLOCK = re.compile(r'path\s*"([^"]*)"\s*\{', re.IGNORECASE)

# Match a capabilities assignment and capture everything between the brackets.
_CAPABILITIES = re.compile(r'capabilities\s*=\s*\[(.*?)\]', re.IGNORECASE | re.DOTALL)

ADMIN_IDENTITY = "hermes-vault-admin"


def lint_policy_text(text: str, identity: str) -> list[str]:
    """Return human-readable policy violations.

    An empty list means the policy is clean for the given identity. Admin
    identities are exempt from the wildcard and sudo bans; every other
    identity is never exempt.
    """
    issues: list[str] = []
    is_admin = identity == ADMIN_IDENTITY

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
