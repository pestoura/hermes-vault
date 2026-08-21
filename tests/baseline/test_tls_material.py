# tests/baseline/test_tls_material.py
#
# Task B3 — TLS cert provisioning (HITL private material).
#
# Validates, WITHOUT generating / reading / copying / inspecting any real TLS
# private key or certificate secret material:
#   * no *.key / *.pem / CA / server-cert secret material is committed to the repo;
#   * the operator provisioning script exists, is POSIX-bash, references the
#     git-ignored certs/ paths, is operator-only/HITL, and refuses to overwrite
#     any pre-existing TLS material;
#   * SECURITY.md documents that TLS private material is operator-custodied out
#     of the repo.
import re
from pathlib import Path

_VAULT_DIR = Path("deployments/vault")
_SCRIPT = _VAULT_DIR / "scripts" / "provision-tls.sh"
_GITIGNORE = _VAULT_DIR / ".gitignore"
_SECURITY_MD = Path("SECURITY.md")

_CERT_PATHS = (
    "certs/vault-server.key",
    "certs/vault-server.pem",
    "certs/ca.pem",
)


# --- from the approved task brief (Step 1) -----------------------------------
def test_tls_private_key_not_in_repo():
    bad = list(_VAULT_DIR.rglob("*.key"))
    assert bad == [], f"private key committed: {bad}"


def test_provision_script_writes_gitignored_certs():
    assert "certs/" in _GITIGNORE.read_text()


# --- B3 artifact existence / RED drivers -------------------------------------
def test_provision_tls_script_exists():
    assert _SCRIPT.is_file(), f"missing operator TLS provisioning script: {_SCRIPT}"


def test_provision_tls_script_references_certs_and_openssl():
    src = _SCRIPT.read_text()
    for p in _CERT_PATHS:
        assert p in src, f"script must provision {p}"
    assert re.search(r"\bopenssl\b", src), "script must use openssl to generate certs"


def test_provision_tls_script_is_operator_hitl_only():
    src = _SCRIPT.read_text()
    # HITL refusal: must NOT run unattended / must require operator acknowledgement.
    assert (
        "VAULT_TLS_OPERATOR_ACK" in src
        or "operator-only" in src.lower()
        or "hitl" in src.lower()
    ), "script must encode an operator-only (HITL) acknowledgement guard"
    # Must never start Vault or perform init/unseal (those are operator steps too).
    assert "vault operator init" not in src
    assert "operator unseal" not in src
    assert "vault server" not in src


def test_provision_tls_script_fails_closed_on_existing_material():
    """Static safety gate: unattended tests must never execute key generation.

    The operator script must visibly check all persistent TLS outputs before the
    first OpenSSL key-generation command and refuse rather than overwrite them.
    """
    src = _SCRIPT.read_text()
    first_genrsa = src.index("openssl genrsa")
    preflight = src[:first_genrsa]
    for var in ("CA_KEY", "CA_CERT", "SERVER_KEY", "SERVER_CERT"):
        assert re.search(rf'-e\s+"\${{{var}}}"', preflight), (
            f"script must test existing ${var} before key generation"
        )
    assert "refus" in preflight.lower() or "already exist" in preflight.lower()
    assert "VAULT_TLS_FORCE" not in src, "MVP must not provide an overwrite bypass"


def test_security_md_documents_tls_private_material_out_of_repo():
    txt = _SECURITY_MD.read_text()
    assert "deployments/vault/certs/" in txt
    assert re.search(r"operator|operador", txt, re.IGNORECASE)
    assert re.search(r"git-?ignored|gitignore", txt, re.IGNORECASE)


def test_no_secret_material_in_deployment_sources():
    patterns = (
        re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"),
        re.compile(r"-----BEGIN CERTIFICATE-----"),
        re.compile(r"-----BEGIN CERTIFICATE REQUEST-----"),
    )
    hits = []
    for f in _VAULT_DIR.rglob("*"):
        if not f.is_file():
            continue
        if f.suffix in (".key", ".pem") or "certs/" in str(f):
            # generated secret material is git-ignored and must not exist in repo
            hits.append(f"unexpected secret file in repo: {f}")
            continue
        try:
            text = f.read_text()
        except (UnicodeDecodeError, IsADirectoryError):
            continue
        for pat in patterns:
            if pat.search(text):
                hits.append(f"secret-material pattern {pat.pattern} in {f}")
    assert hits == [], "secret material found in deployment sources:\n" + "\n".join(hits)
