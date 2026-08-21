# src/evidence/redact.py
#
# Task G2 (OWNER) — Deterministic evidence redactor (spec §14, docs/04 §167,
# docs/08 §24, INV-9). Redacts tokens / passwords / SecretIDs / keys / recovery
# and unseal material / private-key PEM blocks from any emitted artifact (audit
# logs, evidence bundles, CI output) so no secret value leaves the boundary in
# clear text.
#
# Ownership: this module was SEEDED in Task C1 ("Task C1 / G2-seed") and the plan
# File Map assigns `src/evidence/redact.py` to Task G2. G2 therefore takes
# ownership of this file IN PLACE — extending and hardening the C1 seed rather
# than duplicating it. The C1 acceptance tests
# (`tests/audit/test_audit_redaction.py`) remain consumers of this module and are
# not weakened; the public API `redact_text` / `contains_secret` is preserved.
#
# Design contract (asserted by tests/evidence/test_sanitization.py):
#   * FAIL-CLOSED per FIELD NAME, not merely per token prefix. Any sensitive
#     label (token / password / secret / SecretID / root / recovery / unseal /
#     private key ...) has its VALUE removed in both the `key=value` and the JSON
#     `"key": "value"` forms, at any nesting depth (the redactor is text-level, so
#     depth is inherent).
#   * FAIL-CLOSED on input type: a non-`str` input raises TypeError rather than
#     being passed through unsanitized.
#   * DETERMINISTIC: pure regex substitution, no randomness, no clock, no I/O.
#   * IDEMPOTENT: every replacement marker is INERT (it contains none of the
#     trigger substrings), so re-running on already-redacted output is a no-op and
#     `contains_secret()` returns False for redacted text.
#   * NO OVER-REDACTION: benign operational evidence (storage_type=raft,
#     seal_type=shamir, http_status=200, ...) passes through untouched.
#
# No Vault runtime, no credentials, no network: this is a pure static text layer.
from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# Sensitive field labels. A label's VALUE is redacted whenever the label appears
# in an assignment (`label=value`, `label: value`) or as a JSON key
# (`"label": "value"`). Longest-first alternation so a compound label
# (`client_secret`, `api_token`) is never partially consumed by a shorter one.
#
# Word boundaries make this safe: `\btoken\b` does NOT match inside `api_token`
# (underscore is a word character), which is exactly why each compound label is
# listed explicitly instead of relying on substring matching.
# ---------------------------------------------------------------------------
_SENSITIVE_LABELS: tuple[str, ...] = (
    # Vault / auth tokens
    "root_token",
    "wrapping_token",
    "wrapped_token",
    "vault_token",
    "client_token",
    "auth_token",
    "api_token",
    "access_token",
    "refresh_token",
    "bearer_token",
    "token",
    # Passwords / generic secrets
    "password",
    "passwd",
    "client_secret",
    "secret_key",
    "secret_value",
    "secret",
    # AppRole material
    "secret_id",
    "secretid",
    "role_secret",
    # Seal / recovery material
    "recovery_key",
    "unseal_key",
    "recovery_token",
    "shamir_share",
    # Key material
    "private_key",
    "signing_key",
    "encryption_key",
    "tls_key",
    "api_key",
    # Environment-style
    "VAULT_TOKEN",
)


def _label_alternation() -> str:
    """Build a longest-first, numeric-suffix-aware label alternation.

    `recovery_key` also matches `recovery_key_1`, `unseal_key_3`, etc. — the
    indexed forms Vault emits for Shamir shares.
    """
    labels = sorted(set(_SENSITIVE_LABELS), key=len, reverse=True)
    return "|".join(re.escape(label) + r"(?:_\d+)?" for label in labels)


_LABELS = _label_alternation()

# A value is either a quoted string (JSON / shell style) or a bare run of
# non-whitespace. Quoted alternatives come first so the closing quote — and only
# the closing quote — terminates the match, keeping surrounding structure
# (commas, braces) intact.
_VALUE = r'(?:"[^"\n]*"|\'[^\'\n]*\'|\S+)'

# Order matters: multi-line PEM blocks first, then labelled assignments (which
# consume `label=value` as a unit), then bare labels, then value-shape patterns.
# Every replacement marker is inert with respect to ALL patterns below, which is
# what makes redaction idempotent.
_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # --- Private-key / certificate PEM blocks (multi-line, or with escaped \n
    #     as embedded in JSON evidence bundles). ---
    (
        re.compile(
            r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----",
            re.S,
        ),
        "[REDACTED-PRIVKEY]",
    ),
    (
        re.compile(r"-----BEGIN CERTIFICATE-----.*?-----END CERTIFICATE-----", re.S),
        "[REDACTED-CERT]",
    ),
    # --- Sensitive label + value, JSON form: "label": "value" ---
    # Handled explicitly (before the generic assignment rule) so the key's quotes
    # are consumed too and no dangling `"label":` fragment is left behind.
    (
        re.compile(
            r'"(?:' + _LABELS + r')"\s*:\s*' + _VALUE,
            re.I,
        ),
        "[REDACTED-SEC]",
    ),
    # --- Sensitive label + value, assignment form: label=value / label: value ---
    # Must run BEFORE the bare-label rule, otherwise the label rule would strip
    # the key name and leave the secret VALUE in clear text (the exact C1 defect
    # fixed in 8943e75).
    (
        re.compile(
            r"\b(?:" + _LABELS + r")\b\s*[:=]\s*" + _VALUE,
            re.I,
        ),
        "[REDACTED-SEC]",
    ),
    # --- Bare sensitive labels (no value attached). Kept narrow: only labels
    #     whose mere presence in emitted evidence is itself disclosive. ---
    (
        re.compile(
            r"\b(?:root_token|recovery_key(?:_\d+)?|unseal_key(?:_\d+)?|SecretID|secret_id)\b",
            re.I,
        ),
        "[REDACTED-LBL]",
    ),
    # --- Value-shape patterns (catch secrets with no label at all). ---
    # Vault token prefixes per Vault docs: s.* , hvs.* , root.*
    (re.compile(r"\b(?:s\.[A-Za-z0-9_-]{8,})\b"), "[REDACTED-TOKEN]"),
    (re.compile(r"\b(?:hvs\.[A-Za-z0-9_-]{8,})\b"), "[REDACTED-TOKEN]"),
    # root.* tokens (any length — real root tokens are long, redact defensively).
    (re.compile(r"\b(?:root\.[A-Za-z0-9_-]+)\b"), "[REDACTED-ROOT]"),
    # AppRole SecretID / RID (UUID-shaped).
    (
        re.compile(
            r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
            r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b"
        ),
        "[REDACTED-SID]",
    ),
    # Grouped-digit recovery / unseal share shape (e.g. 12345-67890-13579-...).
    (re.compile(r"\b(?:\d+-){4,}\d+\b"), "[REDACTED-RECOVERY]"),
]


def redact_text(text: str) -> str:
    """Return ``text`` with all known secret shapes replaced by stable markers.

    Deterministic and idempotent: re-running on already-redacted output leaves
    the markers intact (they contain no secret material to match).

    Fail-closed on type: a non-``str`` input raises ``TypeError`` rather than
    being returned unsanitized. Callers emitting structured evidence must
    serialize it (e.g. ``json.dumps``) and redact the serialized form.
    """
    if not isinstance(text, str):
        raise TypeError(
            "redact_text() requires str; refusing to pass a "
            f"{type(text).__name__} through unsanitized (fail-closed)"
        )
    if not text:
        return text
    out = text
    for pattern, replacement in _PATTERNS:
        out = pattern.sub(replacement, out)
    return out


def contains_secret(text: str) -> bool:
    """Return True if ``text`` still contains a redactable secret shape.

    Fail-closed on type: a non-``str`` input raises ``TypeError`` (see
    :func:`redact_text`) instead of silently reporting "no secret".
    """
    return redact_text(text) != text
