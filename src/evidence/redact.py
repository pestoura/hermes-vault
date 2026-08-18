# src/evidence/redact.py
#
# Task C1 / G2-seed — Deterministic evidence redactor (spec §14, docs/04 §167,
# docs/08 §24, INV-9). Redacts tokens / SecretIDs / keys / recovery material /
# private-key PEM blocks from any emitted artifact (audit logs, evidence bundles,
# CI output) so no secret value leaves the boundary in clear text.
#
# This is the static, repo-side redaction layer referenced by C1 acceptance. It
# is deterministic (no randomness) so redaction is testable and idempotent.
from __future__ import annotations

import re

# Order matters: PEM blocks first (they span multiple lines), then single-line
# secret shapes. Each match is replaced by an opaque marker that contains NONE of
# the trigger substrings (so redaction is idempotent: re-running on already-
# redacted output leaves the markers intact and contains_secret() returns False).
_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # Private-key / certificate PEM blocks (multi-line).
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.S),
     "[REDACTED-PRIVKEY]"),
    (re.compile(r"-----BEGIN CERTIFICATE-----.*?-----END CERTIFICATE-----", re.S),
     "[REDACTED-CERT]"),
    # Complete assignments FIRST: redact the label AND its non-whitespace value
    # for sensitive keys so the secret VALUE (not just the key name) is removed.
    # This must run before the bare-label rule below, otherwise the label rule
    # strips the key name and leaves the value in clear text.
    (re.compile(
        r"\b(root_token|recovery_key(?:_\d+)?|unseal_key(?:_\d+)?|SecretID|VAULT_TOKEN|VAULT_[A-Z0-9_]+)\b"
        r"\s*[:=]\s*\S+",
        re.I,
    ), "[REDACTED-SEC]"),
    # Bare secret labels (also catch the JSON `"label":` form where a quote sits
    # between the label and the value, defeating the assignment-style patterns).
    # Runs only after complete assignments above have consumed any `label=value`.
    (re.compile(r"\b(root_token|recovery_key|recovery_key_\d+|unseal_key|unseal_key_\d+)\b", re.I),
     "[REDACTED-LBL]"),
    # Vault tokens: s.* , hvs.* , root.* (token prefixes per Vault docs).
    (re.compile(r"\b(s\.[A-Za-z0-9_-]{8,})\b"), "[REDACTED-TOKEN]"),
    (re.compile(r"\b(hvs\.[A-Za-z0-9_-]{8,})\b"), "[REDACTED-TOKEN]"),
    # root.* tokens (any length — real root tokens are long, but redact defensively).
    (re.compile(r"\b(root\.[A-Za-z0-9_-]+)\b"), "[REDACTED-ROOT]"),
    # AppRole SecretID (UUID-shaped) and the literal SecretID label.
    (re.compile(r"\b([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})\b"),
     "[REDACTED-SID]"),
    (re.compile(r"SecretID", re.I), "[REDACTED-SID]"),
    # Recovery / unseal key lines (digits-groups shape).
    (re.compile(r"\b(recovery_key|recovery_key_\d+|unseal_key|unseal_key_\d+)\b\s*[:=]\s*\S+", re.I),
     "[REDACTED-RECOVERY]"),
    (re.compile(r"\b(\d+-){4,}\d+\b"), "[REDACTED-RECOVERY]"),
    # Generic high-entropy assignments that look like secret values.
    (re.compile(r"\b(VAULT_TOKEN|VAULT_[A-Z0-9_]+|root_token|recovery_key|SecretID)\b\s*[:=]\s*[A-Za-z0-9._\-+/]{12,}",
     re.I),
     "[REDACTED-SEC]"),
]


def redact_text(text: str) -> str:
    """Return ``text`` with all known secret shapes replaced by stable markers.

    Deterministic and idempotent: re-running on already-redacted output leaves
    the markers intact (they contain no secret material to match).
    """
    if not text:
        return text
    out = text
    for pattern, replacement in _PATTERNS:
        out = pattern.sub(replacement, out)
    return out


def contains_secret(text: str) -> bool:
    """Return True if ``text`` still contains a redactable secret shape."""
    return redact_text(text) != text
