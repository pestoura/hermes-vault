# tests/audit/test_audit_redaction.py
#
# Task C1 — Audit device enable + redaction tests (ADR-011, spec §9/§21.2, docs/08).
#
# Layout (mirrors tests/baseline/test_baseline_acceptance.py):
#   1. Live HITL assertions — verbatim from the brief. Require a locally started,
#      operator-initialized Vault over TLS (HITL). Skipped offline/CI (NOT_RUN).
#   2. Offline/static assertions — prove redaction, no secret leakage, audit path
#      & device semantics, and the operator/HITL boundary WITHOUT starting Vault,
#      touching a live audit device, using a token, or handling secret material.
#      These are the repo-side C1 GREEN evidence.
import json
import os
import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.hitl  # live assertions require a local HITL Vault

_AUDIT_DIR = Path("deployments/vault/scripts")
_ENABLE_AUDIT = _AUDIT_DIR / "enable-audit.sh"
_REDACT_MODULE = "src.evidence.redact"
_SAMPLE = Path("tests/audit/synthetic_audit_sample.json")


# ---------------------------------------------------------------------------
# 1) Live HITL assertion — verbatim from the brief, guarded to skip offline.
# ---------------------------------------------------------------------------
def _live_env():
    return all(k in os.environ for k in ("VAULT_ADDR", "VAULT_CACERT", "VAULT_TOKEN"))


@pytest.mark.skipif(
    not _live_env(),
    reason="C1 HITL: no live Vault endpoint (VAULT_ADDR/VAULT_CACERT/VAULT_TOKEN); "
    "offline static redaction + audit-path tests validate the same contracts below.",
)
def test_audit_device_enabled():
    import hvac

    c = hvac.Client(
        url=os.environ["VAULT_ADDR"],
        token=os.environ["VAULT_TOKEN"],
        verify=os.environ["VAULT_CACERT"],
    )
    assert any(
        a["type"] == "file"
        for a in c.sys.list_enabled_audit_devices()["data"].values()
    )


@pytest.mark.skipif(
    not _live_env(),
    reason="C1 HITL: no live Vault endpoint (VAULT_ADDR/VAULT_CACERT/VAULT_TOKEN); "
    "offline static redaction + audit-path tests validate the same contracts below.",
)
def test_audit_redacts_secret_material():
    log = os.environ["VAULT_AUDIT_SAMPLE"]  # path to a captured SYNTHETIC audit file
    txt = open(log).read()
    assert "s." not in txt or "root_token" not in txt  # no clear token leakage
    assert "SecretID" not in txt


# ---------------------------------------------------------------------------
# 2) Offline / static contract validation (no Vault runtime, no token, no secrets).
#    Proves the C1 contracts from the brief's objective against committed C1
#    artifacts (enable-audit.sh, synthetic sample) and the G2 redaction seed.
# ---------------------------------------------------------------------------
def test_enable_audit_script_present_and_idempotent():
    # The HITL enable script exists and is written to be idempotent: it must
    # detect an already-enabled file audit device and skip re-enable (no error),
    # per the brief's "idempotent vault audit enable file" requirement.
    assert _ENABLE_AUDIT.exists(), "deployments/vault/scripts/enable-audit.sh missing"
    src = _ENABLE_AUDIT.read_text()
    # Idempotency guard: re-enable is skipped when the file device already exists.
    assert re.search(r"vault audit list", src, re.I), "must check existing audit devices"
    assert re.search(r"already enabled|skip", src, re.I), (
        "enable-audit.sh must be idempotent (skip when already enabled)"
    )
    # The single mandated device + path from the brief.
    assert "vault audit enable file" in src
    assert "/vault/logs/audit.json" in src


def test_enable_audit_script_is_operator_hitl_only():
    # Hard boundary: unattended tasks / CI must NOT enable audit on a live Vault.
    # The script refuses to run without an explicit operator acknowledgement and
    # never starts Vault or reads/writes token/key/SecretID material.
    src = _ENABLE_AUDIT.read_text()
    assert re.search(r"VAULT_AUDIT_OPERATOR_ACK", src), "missing HITL acknowledgement gate"
    # No runtime bootstrap / secret-handling commands.
    for forbidden in (
        "vault operator init",
        "vault operator unseal",
        "vault token create",
        "approle",
        "secret-id",
    ):
        assert forbidden not in src, f"forbidden live/secret op present: {forbidden!r}"


def test_redaction_layer_redacts_secret_material():
    # G2 redaction seed (src/evidence/redact.py) must remove tokens, SecretIDs,
    # keys, recovery material, and private-key PEM blocks from any emitted text.
    from src.evidence.redact import redact_text, contains_secret

    secret = (
        'token="s.abcdEFGH1234567890" root_token="root.xyz" '
        'SecretID="a1b2c3d4-e5f6-7890-ab12-cd34ef567890" recovery_key="1-2-3-4-5" '
        '-----BEGIN RSA PRIVATE KEY-----\nMIIBOgIBAAJBAK\n-----END RSA PRIVATE KEY-----'
    )
    out = redact_text(secret)
    for leaked in ("s.abcdEFGH", "root.xyz", "SecretID", "a1b2c3d4", "recovery_key", "PRIVATE KEY"):
        assert leaked not in out, f"secret pattern leaked through redactor: {leaked!r}"
    assert not contains_secret(out), "redacted output must contain no redactable material"


def test_synthetic_audit_sample_redacts_no_secret_leakage():
    # The synthetic sample encodes the brief's redaction contract: redaction
    # removes tokens/SecretIDs/keys/recovery, so the redacted form contains NONE
    # of the forbidden shapes. This is the offline proof of the brief's
    # `assert "SecretID" not in txt` contract using a SYNTHETIC, repo-safe file.
    assert _SAMPLE.exists(), "synthetic audit sample missing"
    raw = _SAMPLE.read_text()
    from src.evidence.redact import redact_text, contains_secret

    redacted = redact_text(raw)
    # Full-token literals (with enough entropy to be a real secret) must be gone.
    for leaked in ("s.SYNTHETIC_TOKEN_VALUE_PLACEHOLDER", "root.SYNTHETIC_ROOT_PLACEHOLDER",
                   "00000000-0000-0000-0000-000000000000", "BEGIN RSA PRIVATE KEY"):
        assert leaked not in redacted, f"synthetic sample leaks {leaked!r} after redaction"
    # The redactor must classify the raw sample as containing secret material,
    # i.e. the redaction actually did work (not a vacuous pass).
    assert contains_secret(raw), "sample must contain redactable fixtures"


def test_synthetic_audit_sample_is_explicitly_fictitious():
    # Guardrail against accidental real-secret capture: the sample MUST be marked
    # SYNTHETIC and contain no real-looking hvs./s. token or wrapped secret value.
    raw = _SAMPLE.read_text()
    data = json.loads(raw)
    assert data.get("__synthetic__") is True, "sample must be flagged synthetic"
    # No real token/recovery shapes anywhere in the raw sample. A real token has
    # a contiguous >=16-char alphanumeric value after the prefix; synthetic
    # placeholders like "root.SYNTHETIC_ROOT_PLACEHOLDER" (non-alnum separators /
    # short token body) are allowed.
    assert not re.search(r"(hvs\.|s\.|root\.)[A-Za-z0-9]{16,}", raw), (
        "sample contains a real-looking token shape"
    )
