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
    low = text.lower()
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
