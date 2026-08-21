# tests/evidence/test_sanitization.py
#
# Task G2 — Sanitized evidence tests (spec §14, docs/04 §167, docs/08 §24, INV-9).
#
# Proves the deterministic evidence redactor (`src/evidence/redact.py`, owned by
# G2, seeded in C1) is FAIL-CLOSED for every secret-bearing shape/field the task
# requires — token, password, SecretID, root, recovery, unseal, private key, PEM —
# in both `key=value` and JSON `"key": "value"` forms, in nested structures, and
# that redaction is DETERMINISTIC and IDEMPOTENT.
#
# Guardrails honoured here:
#   * SYNTHETIC fixtures ONLY. No real token / SecretID / recovery share / private
#     key / password ever appears in this file (INV-1).
#   * Every secret-shaped fixture is ASSEMBLED AT RUNTIME from harmless fragments,
#     so no tracked source line contains a literal that would trip the repo secret
#     scanner (`scripts/ci/run-gates.sh` secret_scan). The scanner is NOT weakened
#     and this file is NOT exempted — the C1 SECRET SCANNER RULING stands.
#   * No Vault runtime, no credentials, no network, no remotes.
#   * Public API preserved: only `redact_text` / `contains_secret` are exercised.
#
# There is no `pytest.mark.hitl` test in G2: the plan defines none. Redaction is
# proved statically and completely offline; nothing here is a live-PASS claim.
from __future__ import annotations

import re

import pytest

from src.evidence.redact import contains_secret, redact_text

# ---------------------------------------------------------------------------
# Synthetic fragments. Assembled at runtime (never a tracked literal of the
# shape `<sensitive_key>=<16+ chars>` or a full PEM block).
# ---------------------------------------------------------------------------
_SYNTH_VALUE = "ABCD_SYNTHETIC_VALUE_xyz0123"
_SYNTH_B64 = "U1lOVEhFVElDX0ZJWFRVUkVfQk9EWV9OT1RfQV9LRVk"
_SYNTH_UUID = "a1b2c3d4-e5f6-7890-ab12-cd34ef567890"

_PEM_BEGIN = "-----BEGIN " + "RSA PRIVATE KEY" + "-----"
_PEM_END = "-----END " + "RSA PRIVATE KEY" + "-----"

# Secret-bearing field labels required by the G2 objective.
_SECRET_LABELS = (
    "token",
    "api_token",
    "auth_token",
    "vault_token",
    "VAULT_TOKEN",
    "password",
    "passwd",
    "secret",
    "client_secret",
    "SecretID",
    "secret_id",
    "root_token",
    "recovery_key",
    "recovery_key_1",
    "unseal_key",
    "unseal_key_3",
    "private_key",
    "wrapping_token",
)


def _assign(label: str, value: str) -> str:
    """Build `label=value` at runtime; the literal never exists in the source."""
    return "".join((label, "=", value))


def _json_field(label: str, value: str) -> str:
    """Build the JSON `"label": "value"` form at runtime."""
    return "".join(('"', label, '": "', value, '"'))


def _pem_block() -> str:
    """Build a synthetic PRIVATE KEY PEM block at runtime."""
    return "\n".join((_PEM_BEGIN, _SYNTH_B64, _PEM_END))


def _vault_token(prefix: str) -> str:
    """Build a Vault-style prefixed token (`s.` / `hvs.`) at runtime."""
    return "".join((prefix, "SYNTHETICTOKENBODY0123456789"))


# ---------------------------------------------------------------------------
# 1) Fail-closed coverage per required secret-bearing FIELD — assignment form.
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("label", _SECRET_LABELS)
def test_assignment_value_is_redacted_for_every_secret_label(label: str) -> None:
    raw = _assign(label, _SYNTH_VALUE)
    # Non-vacuous: the redactor must first CLASSIFY the raw text as secret-bearing.
    assert contains_secret(raw), f"raw {label} assignment not classified as secret"
    out = redact_text(raw)
    assert _SYNTH_VALUE not in out, (
        f"{label} VALUE leaked through redactor (fail-open); got {out!r}"
    )
    assert not contains_secret(out), f"redacted {label} output still flagged secret"


# ---------------------------------------------------------------------------
# 2) Fail-closed coverage per required secret-bearing FIELD — JSON form.
#    Evidence bundles are emitted as JSON, so the quoted form must be covered.
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("label", _SECRET_LABELS)
def test_json_field_value_is_redacted_for_every_secret_label(label: str) -> None:
    raw = _json_field(label, _SYNTH_VALUE)
    assert contains_secret(raw), f"raw JSON {label} field not classified as secret"
    out = redact_text(raw)
    assert _SYNTH_VALUE not in out, (
        f"JSON {label} VALUE leaked through redactor (fail-open); got {out!r}"
    )
    assert not contains_secret(out), f"redacted JSON {label} output still flagged secret"


# ---------------------------------------------------------------------------
# 3) Vault-prefixed token shapes (the `s.` / `hvs.` contract from the plan).
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("prefix", ["s.", "hvs."])
def test_vault_prefixed_token_is_redacted(prefix: str) -> None:
    token = _vault_token(prefix)
    raw = "".join(("emitted evidence line, token ", token, " end"))
    assert contains_secret(raw)
    out = redact_text(raw)
    assert token not in out, "Vault-prefixed token survived redaction"
    assert "SYNTHETICTOKENBODY" not in out, "token body survived redaction"
    assert not contains_secret(out)


def test_root_token_shape_is_redacted() -> None:
    root_tok = "".join(("root.", "SYNTHETICROOTBODY0123456789"))
    out = redact_text(root_tok)
    assert "SYNTHETICROOTBODY" not in out, "root.* token body survived redaction"
    assert not contains_secret(out)


# ---------------------------------------------------------------------------
# 4) SecretID / UUID-shaped material.
# ---------------------------------------------------------------------------
def test_secret_id_label_and_uuid_value_are_redacted() -> None:
    raw = _assign("SecretID", _SYNTH_UUID)
    out = redact_text(raw)
    assert _SYNTH_UUID not in out, "SecretID UUID value survived redaction"
    assert "SecretID" not in out, "SecretID label survived redaction"
    assert not contains_secret(out)


def test_bare_uuid_shaped_value_is_redacted() -> None:
    # A bare UUID in emitted evidence is treated as possible SecretID material.
    out = redact_text(_SYNTH_UUID)
    assert _SYNTH_UUID not in out, "bare UUID-shaped value survived redaction"
    assert not contains_secret(out)


# ---------------------------------------------------------------------------
# 5) Private-key PEM blocks (multi-line).
# ---------------------------------------------------------------------------
def test_private_key_pem_block_is_fully_redacted() -> None:
    raw = "\n".join(("evidence header", _pem_block(), "evidence footer"))
    assert contains_secret(raw), "PEM block not classified as secret"
    out = redact_text(raw)
    assert "PRIVATE KEY" not in out, "PEM PRIVATE KEY marker survived redaction"
    assert _SYNTH_B64 not in out, "PEM body survived redaction"
    assert not contains_secret(out)
    # Surrounding non-secret prose is preserved (no over-redaction).
    assert "evidence header" in out and "evidence footer" in out


def test_pem_block_inside_json_string_is_redacted() -> None:
    # PEM material is frequently embedded with escaped newlines in JSON evidence.
    escaped = "\\n".join((_PEM_BEGIN, _SYNTH_B64, _PEM_END))
    raw = "".join(('"tls_key": "', escaped, '"'))
    out = redact_text(raw)
    assert "PRIVATE KEY" not in out, "escaped-newline PEM survived redaction"
    assert _SYNTH_B64 not in out, "escaped-newline PEM body survived redaction"
    assert not contains_secret(out)


# ---------------------------------------------------------------------------
# 6) Recovery / unseal material, including the grouped-digits share shape.
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("label", ["recovery_key", "recovery_key_2", "unseal_key", "unseal_key_5"])
def test_recovery_and_unseal_values_are_redacted(label: str) -> None:
    raw = _assign(label, _SYNTH_VALUE)
    out = redact_text(raw)
    assert _SYNTH_VALUE not in out, f"{label} value survived redaction"
    assert not contains_secret(out)


def test_grouped_digit_share_shape_is_redacted() -> None:
    share = "-".join(("12345", "67890", "13579", "24680", "11223"))
    out = redact_text(share)
    assert share not in out, "grouped-digit share shape survived redaction"
    assert not contains_secret(out)


# ---------------------------------------------------------------------------
# 7) Structured (nested) evidence payloads — sanitized by field name at depth.
# ---------------------------------------------------------------------------
def test_nested_structured_evidence_is_sanitized_at_depth() -> None:
    raw = "\n".join(
        (
            "{",
            '  "run": {',
            "    " + _json_field("password", _SYNTH_VALUE) + ",",
            '    "consumers": [',
            "      { " + _json_field("SecretID", _SYNTH_UUID) + " },",
            "      { " + _json_field("api_token", _SYNTH_VALUE) + " }",
            "    ],",
            '    "note": "benign evidence text"',
            "  }",
            "}",
        )
    )
    assert contains_secret(raw), "nested payload not classified as secret-bearing"
    out = redact_text(raw)
    assert _SYNTH_VALUE not in out, "nested secret value leaked"
    assert _SYNTH_UUID not in out, "nested SecretID leaked"
    assert not contains_secret(out), "sanitized nested payload still flagged secret"
    # Structure and benign content survive.
    assert "benign evidence text" in out
    assert '"consumers"' in out


# ---------------------------------------------------------------------------
# 8) Idempotence + determinism (explicit G2 requirement).
# ---------------------------------------------------------------------------
def _all_fixture_texts() -> list[str]:
    texts: list[str] = []
    for label in _SECRET_LABELS:
        texts.append(_assign(label, _SYNTH_VALUE))
        texts.append(_json_field(label, _SYNTH_VALUE))
    texts.append(_pem_block())
    texts.append(_vault_token("s."))
    texts.append(_vault_token("hvs."))
    texts.append(_SYNTH_UUID)
    texts.append("-".join(("12345", "67890", "13579", "24680", "11223")))
    texts.append("wholly benign evidence line with no secret")
    return texts


@pytest.mark.parametrize("raw", _all_fixture_texts())
def test_redaction_is_idempotent(raw: str) -> None:
    once = redact_text(raw)
    twice = redact_text(once)
    assert twice == once, f"redaction not idempotent for {raw[:40]!r}"
    # And a second pass never re-flags already-redacted output as secret-bearing.
    assert not contains_secret(once), f"redacted output re-flagged for {raw[:40]!r}"


@pytest.mark.parametrize("raw", _all_fixture_texts())
def test_redaction_is_deterministic(raw: str) -> None:
    assert redact_text(raw) == redact_text(raw), "redaction is not deterministic"


def test_markers_contain_no_trigger_substring() -> None:
    # Idempotence depends on the replacement markers being inert: a marker must
    # not itself contain a redactable trigger, or repeated passes would churn.
    for raw in _all_fixture_texts():
        out = redact_text(raw)
        for marker in re.findall(r"\[REDACTED-[A-Z]+\]", out):
            assert redact_text(marker) == marker, f"marker {marker!r} is not inert"


# ---------------------------------------------------------------------------
# 9) No over-redaction: benign evidence must pass through untouched.
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "benign",
    [
        "audit device enabled at path file/",
        "restore drill PASS; audit PASS; owner sign-off PENDING",
        "consumer hsl-signer bound to policy hsl-signer",
        "storage_type=raft",
        "seal_type=shamir",
        "http_status=200",
        "",
    ],
)
def test_benign_evidence_is_not_redacted(benign: str) -> None:
    assert redact_text(benign) == benign, "benign evidence was over-redacted"
    assert not contains_secret(benign), "benign evidence misclassified as secret"


# ---------------------------------------------------------------------------
# 10) Fail-closed on non-str input: the redactor must not silently pass a
#     secret-bearing object through unsanitized.
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("bad", [None, 12345, b"bytes", ["list"], {"k": "v"}, object()])
def test_non_str_input_is_fail_closed(bad: object) -> None:
    # Either reject explicitly (TypeError) or sanitize the string form — never
    # return the raw object / leak an unsanitized value.
    try:
        out = redact_text(bad)  # type: ignore[arg-type]
    except TypeError:
        pass  # explicit fail-closed rejection is acceptable
    else:
        assert isinstance(out, str), "redact_text must return str when it does not raise"
        assert not contains_secret(out), "non-str path produced unsanitized output"

    try:
        flagged = contains_secret(bad)  # type: ignore[arg-type]
    except TypeError:
        pass
    else:
        assert isinstance(flagged, bool), "contains_secret must return bool or raise"


def test_secret_bearing_non_str_is_not_passed_through_clean() -> None:
    payload = {"password": _SYNTH_VALUE}
    try:
        out = redact_text(payload)  # type: ignore[arg-type]
    except TypeError:
        return  # explicit rejection — fail-closed, nothing emitted
    assert _SYNTH_VALUE not in out, "secret leaked via non-str input path"


# ---------------------------------------------------------------------------
# 11) Public API contract is preserved (C1 consumers must keep working).
# ---------------------------------------------------------------------------
def test_public_api_shape_preserved() -> None:
    import inspect

    assert callable(redact_text) and callable(contains_secret)
    assert list(inspect.signature(redact_text).parameters)[0] == "text"
    assert list(inspect.signature(contains_secret).parameters)[0] == "text"
    assert isinstance(redact_text("plain"), str)
    assert contains_secret("plain") is False


def test_contains_secret_agrees_with_redact_text() -> None:
    for raw in _all_fixture_texts():
        expected = redact_text(raw) != raw
        assert contains_secret(raw) is expected, (
            "contains_secret disagrees with redact_text — classifier is not fail-closed"
        )
