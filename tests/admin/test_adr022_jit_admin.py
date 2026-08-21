from pathlib import Path
import re

from src.policy_lint.linter import lint_policy_text

ADR = Path("docs/13-security-decisions.md")
POLICY_DIR = Path("policies/admin")
ISSUER = POLICY_DIR / "vault-admin-issuer.hcl"
ADMIN_POLICIES = {
    "vault-admin-policy": POLICY_DIR / "vault-admin-policy.hcl",
    "vault-admin-auth": POLICY_DIR / "vault-admin-auth.hcl",
    "vault-admin-token": POLICY_DIR / "vault-admin-token.hcl",
    "vault-admin-secrets-engine": POLICY_DIR / "vault-admin-secrets-engine.hcl",
    "vault-admin-audit": POLICY_DIR / "vault-admin-audit.hcl",
}


def _text(path: Path) -> str:
    return path.read_text()


def _active_paths(text: str) -> list[str]:
    return re.findall(r'^\s*path\s+"([^"]+)"\s*\{', text, re.M)


def test_adr022_records_audit_first_cert_issuer_jit_admin_and_root_revoke_order():
    text = _text(ADR)
    assert "ADR-022" in text
    section = text.split("## ADR-022", 1)[1]
    section = section.split("\n## ADR-", 1)[0] if "\n## ADR-" in section else section
    low = section.lower()
    for marker in ("audit", "cert", "vault-admin-issuer", "hermes-vault-admin", "root"):
        assert marker in low
    assert low.index("audit") < low.index("vault-admin-issuer") < low.rindex("root")
    assert "10 min" in low or "10m" in low
    assert "non-renew" in low or "não renov" in low
    assert "orphan" in low


def test_certificate_identity_is_issuer_only_with_exact_token_role_path():
    assert ISSUER.is_file()
    text = _text(ISSUER)
    assert _active_paths(text) == ["auth/token/create/hermes-vault-admin"]
    assert 'capabilities = ["update"]' in text
    assert "sudo" not in text.lower()
    assert "*" not in _active_paths(text)[0]
    assert lint_policy_text(text, identity="vault-admin-issuer") == []


def test_classed_admin_policies_exist_without_global_root_policy_or_global_wildcard():
    for identity, path in ADMIN_POLICIES.items():
        assert path.is_file(), f"missing {path}"
        text = _text(path)
        assert _active_paths(text), f"no path blocks in {path}"
        assert 'path "*"' not in text
        assert not re.search(r'capabilities\s*=\s*\[[^\]]*"root"', text, re.I | re.S)
        assert "root" not in {p.strip("/") for p in _active_paths(text)}
        assert lint_policy_text(text, identity="hermes-vault-admin") == []


def test_admin_classes_are_scoped_by_control_plane_domain():
    assert any(p.startswith("sys/policies/acl") for p in _active_paths(_text(ADMIN_POLICIES["vault-admin-policy"])))
    assert any(p.startswith("sys/auth") for p in _active_paths(_text(ADMIN_POLICIES["vault-admin-auth"])))
    assert any(p.startswith("auth/token") for p in _active_paths(_text(ADMIN_POLICIES["vault-admin-token"])))
    assert any(p.startswith("sys/mounts") for p in _active_paths(_text(ADMIN_POLICIES["vault-admin-secrets-engine"])))
    assert any(p.startswith("sys/audit") for p in _active_paths(_text(ADMIN_POLICIES["vault-admin-audit"])))

SCRIPT = Path("deployments/vault/scripts/bootstrap-jit-admin.sh")
CHECKLIST = Path("deployments/vault/scripts/bootstrap-checklist.sh")


def test_jit_bootstrap_script_is_hitl_audit_gated_and_public_cert_only():
    assert SCRIPT.is_file()
    src = _text(SCRIPT)
    assert "VAULT_JIT_ADMIN_OPERATOR_ACK" in src
    assert "VAULT_ADMIN_CERT_PEM" in src
    assert "vault audit list" in src
    assert "AUDIT_REQUIRED" in src
    assert "vault auth list" in src and "vault auth enable cert" in src
    assert "openssl x509" in src
    assert "CA:TRUE" in src
    assert "TLS Web Client Authentication" in src
    for forbidden in ("vault operator init", "vault operator unseal", "vault token revoke", "vault login", "client-key"):
        assert forbidden not in src
    assert "PRIVATE KEY" not in src


def test_jit_bootstrap_applies_all_policy_classes_and_issuer_cert_role():
    src = _text(SCRIPT)
    for policy in ("vault-admin-issuer", *ADMIN_POLICIES.keys()):
        assert f"vault policy write {policy}" in src
    assert "auth/cert/certs/vault-admin-issuer" in src
    assert "certificate=-" in src
    assert 'cat "${VAULT_ADMIN_CERT_PEM}" | vault write' in src
    assert "token_policies=vault-admin-issuer" in src
    assert "token_no_default_policy=true" in src
    assert "token_explicit_max_ttl=5m" in src


def test_jit_token_role_is_exactly_bounded_to_classed_admin_policies():
    src = _text(SCRIPT)
    assert "auth/token/roles/hermes-vault-admin" in src
    assert "orphan=true" in src
    assert "renewable=false" in src
    assert "token_no_default_policy=true" in src
    assert "token_explicit_max_ttl=10m" in src
    assert "disallowed_policies=default,root" in src
    expected = ",".join(ADMIN_POLICIES.keys())
    assert f"allowed_policies={expected}" in src
    role_block = src.split('auth/token/roles/hermes-vault-admin', 1)[1]
    assert "allowed_policies=root" not in role_block


def test_bootstrap_checklist_moves_audit_before_jit_admin_and_root_revoke():
    text = _text(CHECKLIST)
    low = text.lower()
    assert "enable audit" in low
    assert "jit" in low and "cert" in low
    assert "revoke initial root" in low
    assert low.index("enable audit") < low.index("jit") < low.index("revoke initial root")


ENABLE_AUDIT = Path("deployments/vault/scripts/enable-audit.sh")

def test_operator_scripts_use_container_pinned_vault_cli_not_missing_host_cli():
    for path in (SCRIPT, ENABLE_AUDIT):
        src = _text(path)
        assert "docker compose" in src
        assert "exec -T -e VAULT_TOKEN vault vault" in src
        assert "command -v vault" not in src

def test_jit_bootstrap_streams_host_policy_files_to_container_cli():
    src = _text(SCRIPT)
    for policy in ("vault-admin-issuer", *ADMIN_POLICIES.keys()):
        assert f"vault policy write {policy} -" in src
        assert f"{policy}.hcl" in src
