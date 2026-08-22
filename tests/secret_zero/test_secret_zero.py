# tests/secret_zero/test_secret_zero.py
#
# Task H1 — Secret-zero bootstrap procedure + delivery-constraint tests.
#
# IMPORTANT (RED->GREEN design note):
# The canonical plan's literal test greps for the bare "SecretID" *string* across
# templates/ policies/ deployments/. That literal form is WRONG for this repo: it
# collides with INV-10, which *requires* the word "SecretID" to appear as
# HITL-boundary prose in deployments/vault/scripts/bootstrap-checklist.sh
# ("AppRole SecretID issuance / wrapping" — operator-only, NOT_RUN). The committed
# global-invariant suite (tests/lifecycle/test_global_invariants.py, INV-8/INV-10)
# states this explicitly: the word as HITL prose is fine; only an *assigned value*
# (SecretID=<value>) is forbidden.
#
# So the literal substring test REDs on a correct, required file. The GREEN form
# below scans for the *value-shape* boundary only (mirroring the canonical
# scripts/ci/run-gates.sh secret-scan pattern), which is the real contract, and
# adds the wrapped/single-use/short-TTL delivery assertion. This preserves the
# INV-8/INV-10 boundaries exactly: live AppRole SecretID issuance/wrapping/CIDR
# binding remains operator-only NOT_RUN.
import pathlib
import re

import pytest

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]

# Mirrors scripts/ci/run-gates.sh secret-scan boundary for SecretID: a real
# *value* assignment only (e.g. SecretID=s.XXXX or SecretID: abc...), never the
# bare HITL-prose word. 16+ token chars per the canonical gate.
_SECRETID_VALUE_RE = re.compile(r"SecretID\s*[:=]\s*[A-Za-z0-9._-]{16,}")

# Roots the secret-zero contract governs (plan H1: never in .env/state/GitHub/logs).
_SCAN_ROOTS = [
    _REPO_ROOT / "templates",
    _REPO_ROOT / "policies",
    _REPO_ROOT / "deployments",
]


def _walk_text_files(root: pathlib.Path):
    if not root.exists():
        return
    for p in sorted(root.rglob("*")):
        if p.is_file() and p.suffix not in {".pyc", ".png", ".jpg", ".jpeg", ".gif", ".pdf"}:
            yield p


def test_secret_zero_no_real_secretid_value_in_contract_roots():
    # RED (literal substring) failed on INV-10 HITL prose in
    # deployments/vault/scripts/bootstrap-checklist.sh. GREEN asserts only the
    # *value* shape is forbidden — exactly what the canonical secret scan enforces.
    hits = []
    for root in _SCAN_ROOTS:
        for f in _walk_text_files(root):
            try:
                text = f.read_text(encoding="utf-8", errors="strict")
            except (UnicodeDecodeError, OSError):
                continue
            for m in _SECRETID_VALUE_RE.finditer(text):
                hits.append(f"{f.relative_to(_REPO_ROOT)}: {m.group(0)!r}")
    assert not hits, (
        "INV-8/INV-10 violation: a real SecretID value shape was found in a "
        "secret-zero contract root (templates/ policies/ deployments/):\n"
        + "\n".join(hits)
    )


def test_wrapped_single_use_short_ttl_contract():
    from src.capability_contract.schema import CapabilityRequest, CapabilityType

    # Secret-zero delivery is wrapped_secret, single-use, ttl<=300.
    req = CapabilityRequest(
        principal="hsl-signer",
        action="auth.approle",
        resource_scope="hsl-signer",
        risk_class="high",
        requested_ttl=120,
        capability_type=CapabilityType.wrapped_secret,
    )
    # Delivery type is the wrapped-secret contract (no raw SecretID value travels).
    assert req.capability_type is CapabilityType.wrapped_secret
    # Short-TTL bound for the bootstrap credential.
    assert req.requested_ttl <= 300
    # Single-use / no-secret-payload: the contract envelope MUST reject any secret
    # material (INV-1 + INV-8). A hypothetical secret-bearing field is denied.
    with pytest.raises(Exception):
        CapabilityRequest(
            principal="x",
            action="y",
            resource_scope="z",
            risk_class="low",
            requested_ttl=60,
            _secret_value="SYNTH-PLACEHOLDER-NOT-REAL",
        )


def test_secret_zero_runbook_uses_secret_id_generation_parameters():
    rb = _REPO_ROOT / "docs" / "runbooks" / "secret-zero.md"
    text = rb.read_text(encoding="utf-8")
    command = text.split("vault write -f -wrap-ttl=60s", 1)[1].split("```", 1)[0]

    # Vault AppRole SecretID generation accepts ttl/num_uses for per-issuance
    # overrides. secret_id_ttl/secret_id_num_uses are role property names and
    # must not be used as request fields on the /secret-id generation endpoint.
    assert "ttl=120" in command
    assert "num_uses=1" in command
    assert "secret_id_ttl=" not in command
    assert "secret_id_num_uses=" not in command

    # Bind both the SecretID login and the resulting token to the consumer CIDR.
    assert "cidr_list=" in command
    assert "token_bound_cidrs=" in command


def test_secret_zero_runbook_exists_and_is_hitl_not_run():
    # The operator runbook must exist and must NOT claim a live PASS: the actual
    # wrapped SecretID issuance remains operator-only NOT_RUN.
    rb = _REPO_ROOT / "docs" / "runbooks" / "secret-zero.md"
    assert rb.exists(), "H1 requires docs/runbooks/secret-zero.md"
    text = rb.read_text(encoding="utf-8")
    assert "NOT_RUN" in text, "secret-zero.md must record the live issuance as NOT_RUN"
    # The HITL boundary must be explicit (INV-10).
    lowered = text.lower()
    for marker in ("hitl", "operator-only", "out-of-band", "cidr"):
        assert marker in lowered, f"secret-zero.md missing HITL/contract marker: {marker}"


# --- Hardening ---
def test_secret_zero_value_shape_regex_distinguishes_prose_from_value():
    # Regression guard: the value-shape boundary MUST NOT match INV-10 HITL
    # prose (the word "SecretID" as operator-boundary text) but MUST match a
    # real assigned value. Prevents the regex from drifting back to the broken
    # bare-substring form, or to a form that lets real values slip through.
    hitl_prose = "AppRole SecretID issuance / wrapping (operator-only, NOT_RUN)"
    assert _SECRETID_VALUE_RE.search(hitl_prose) is None, (
        "value-shape regex must NOT match INV-10 HITL prose"
    )
    # Build the real-value strings at RUNTIME (concatenation) so the trigger
    # literals never appear verbatim in this source file — otherwise the
    # canonical secret scan (scripts/ci/run-gates.sh --scan-only) would flag the
    # test source itself as a leak. The regex-under-test still runs on the real
    # value shape.
    real_value = "SecretID=" + "s." + "A" * 24
    assert _SECRETID_VALUE_RE.search(real_value) is not None, (
        "value-shape regex must match a real SecretID value assignment"
    )
    real_value_colon = "SecretID:" + " " + "B" * 24
    assert _SECRETID_VALUE_RE.search(real_value_colon) is not None, (
        "value-shape regex must match a 'SecretID: <value>' assignment"
    )


def test_secret_zero_runbook_passes_canonical_secret_scan():
    # Hardening: the runbook MUST use only clearly-synthetic values so it passes
    # the canonical gate (scripts/ci/run-gates.sh --scan-only). We apply the same
    # SecretID value-shape rule the gate uses, to the runbook text.
    rb = _REPO_ROOT / "docs" / "runbooks" / "secret-zero.md"
    text = rb.read_text(encoding="utf-8")
    assert _SECRETID_VALUE_RE.search(text) is None, (
        "secret-zero.md must not contain any real SecretID value shape; "
        "synthetic placeholders only"
    )
    # And the canonical hvs./s. token patterns must also be absent (synthetic
    # placeholders like WRAPPED-TOKEN-EXAMPLE-NOT-REAL must not match).
    canonical = re.compile(
        r"(hvs\.[A-Za-z0-9]{20,})|(s\.[A-Za-z0-9]{20,})|"
        r"((VAULT_TOKEN|VAULT_[A-Z0-9]+|[Rr]oot_token|recovery_key|SecretID)"
        r"\s*[:=]\s*[A-Za-z0-9._-]{16,})"
    )
    assert canonical.search(text) is None, (
        "secret-zero.md must pass the canonical secret scan (synthetic only)"
    )
