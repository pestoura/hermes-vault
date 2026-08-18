# tests/baseline/test_no_automated_secret_ops.py
#
# Task B4 — Init / unseal / root bootstrap runbook + HITL stops.
#
# Validates, WITHOUT executing Vault or touching any secret material:
#   * docs/runbooks/vault-bootstrap.md documents the human init/unseal/root
#     procedure with explicit HITL gates and out-of-band custody;
#   * the runbook contains NO leaked real secret value;
#   * deployments/vault/scripts/bootstrap-checklist.sh is a read-only checklist
#     printer that encodes explicit HITL stop points and performs NO automated
#     secret operation (no init/unseal/root/SecretID/TLS-key execution, never
#     starts Vault, never reads/writes tokens/shares/keys).
import re
from pathlib import Path

_RUNBOOK = Path("docs/runbooks/vault-bootstrap.md")
_CHECKLIST = Path("deployments/vault/scripts/bootstrap-checklist.sh")

# HITL boundary verbs that must be PRESENT in the runbook as recorded
# operator-only procedures (documented, never auto-executed).
_HITL_MARKERS = ["HITL", "init", "unseal", "root", "out-of-band custody"]


def _script_executable_body(src: str) -> str:
    """Return only the parts of a bash script that could actually execute:
    drop comment lines, and drop the body of any quoted heredoc (inert text)."""
    out_lines = []
    in_heredoc = False
    for raw in src.splitlines():
        line = raw.rstrip("\n")
        stripped = line.strip()
        if in_heredoc:
            if stripped == "EOF":
                in_heredoc = False
            continue
        if stripped.startswith("#"):
            continue
        if stripped.startswith("cat") and "<<'EOF'" in stripped:
            in_heredoc = True
            continue
        out_lines.append(line)
    return "\n".join(out_lines)


# --- from the approved task brief (Step 1) -----------------------------------
def test_runbook_has_hitl_markers():
    txt = _RUNBOOK.read_text()
    for m in _HITL_MARKERS:
        assert m.lower() in txt.lower(), m


def test_no_secret_in_runbook():
    txt = _RUNBOOK.read_text()
    assert not re.search(r"(root_token|recovery_key|s\.\w{20,})", txt), "real secret leaked"


# --- B4 artifact existence / RED drivers -------------------------------------
def test_runbook_exists():
    assert _RUNBOOK.is_file(), f"missing HITL bootstrap runbook: {_RUNBOOK}"


def test_checklist_script_exists():
    assert _CHECKLIST.is_file(), f"missing read-only bootstrap checklist: {_CHECKLIST}"


def test_checklist_is_read_only_printer():
    src = _CHECKLIST.read_text()
    # A read-only checklist printer must only emit guidance, never act.
    # Refuse to run if it starts Vault (a real, executable command).
    body = _script_executable_body(src)
    assert "vault server" not in body, "checklist must not start Vault"
    # It must declare itself read-only / printer-only.
    assert re.search(r"read-?only|checklist", src, re.IGNORECASE), \
        "checklist must self-identify as read-only checklist printer"


def test_checklist_has_explicit_hitl_stop_points():
    src = _CHECKLIST.read_text()
    # Explicit operator-only / HITL stop markers must be encoded so an attacker
    # or an unattended task cannot mistake the printer for an executor.
    hits = [
        m for m in ("HITL", "operator-only", "out-of-band")
        if m.lower() in src.lower()
    ]
    assert hits, "checklist must encode explicit HITL stop points"
    # It must reference the documented human steps it is guarding.
    for step in ("init", "unseal", "root"):
        assert step.lower() in src.lower(), f"checklist must reference {step}"


def test_checklist_performs_no_secret_operations():
    src = _CHECKLIST.read_text()
    body = _script_executable_body(src)
    # Forbidden automated secret operations (execution, not documentation):
    forbidden = (
        re.compile(r"vault operator init"),
        re.compile(r"operator unseal"),
        re.compile(r"vault operator unseal"),
        re.compile(r"approle"),          # SecretID issuance
        re.compile(r"secret-id"),        # SecretID issuance
        re.compile(r"openssl"),          # TLS key generation
        re.compile(r"secret[/ ]write"),  # secret writes
        re.compile(r"token create"),     # root/derived token issuance
    )
    for pat in forbidden:
        assert not pat.search(body), f"checklist must not contain automated secret op: {pat.pattern}"
    # No real secret shapes may appear anywhere in the script source.
    secret_shapes = (
        re.compile(r"(root_token|recovery_key|s\.\w{20,})"),
        re.compile(r"(VAULT_TOKEN|SecretID)\s*[:=]"),
    )
    for pat in secret_shapes:
        assert not pat.search(src), f"checklist must not contain secret material: {pat.pattern}"
