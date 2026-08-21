from pathlib import Path
import re

from src.policy_lint.linter import lint_policy_text

ADR = Path("docs/13-security-decisions.md")
ADMIN = Path("policies/admin/vault-admin-recovery.hcl")
ACCEPT = Path("policies/recovery/restore-acceptance-test.hcl")
BOOTSTRAP = Path("deployments/vault/scripts/bootstrap-jit-admin.sh")
PROMOTE = Path("deployments/vault/scripts/promote-recovery-admin.sh")
GITIGNORE = Path(".gitignore")


def _text(path: Path) -> str:
    return path.read_text()


def _paths(text: str) -> list[str]:
    return re.findall(r'^\s*path\s+"([^"]+)"\s*\{', text, re.M)


def _block(text: str, path: str) -> str:
    return text.split(f'path "{path}"', 1)[1].split("}", 1)[0]


def test_adr023_records_owner_approved_network_none_restore_model():
    text = _text(ADR)
    assert "ADR-023" in text
    section = text.split("## ADR-023", 1)[1]
    low = section.lower()
    for marker in ("network=none", "zero ports", "snapshot-force", "shamir", "hitl"):
        assert marker in low

def test_recovery_admin_policy_is_exact_and_never_restores_production():
    assert ADMIN.is_file()
    text = _text(ADMIN)
    expected = {
        "sys/storage/raft/snapshot",
        "sys/mounts/restore-acceptance-kv",
        "sys/mounts/restore-acceptance-transit",
        "sys/policies/acl/restore-acceptance-test",
        "auth/cert/certs/restore-acceptance",
        "restore-acceptance-kv/data/primary",
        "restore-acceptance-kv/data/forbidden",
        "restore-acceptance-transit/keys/restore-acceptance",
        "auth/token/revoke-self",
    }
    assert set(_paths(text)) == expected
    assert "snapshot-force" not in text
    assert 'path "*"' not in text
    snap = _block(text, "sys/storage/raft/snapshot")
    assert '"read"' in snap
    for forbidden in ('"create"', '"update"', '"delete"', '"sudo"'):
        assert forbidden not in snap
    assert lint_policy_text(text, identity="hermes-vault-admin") == []


def test_acceptance_policy_is_read_only_positive_with_explicit_cross_path_deny():
    assert ACCEPT.is_file()
    text = _text(ACCEPT)
    assert set(_paths(text)) == {
        "restore-acceptance-kv/data/primary",
        "restore-acceptance-kv/data/forbidden",
        "restore-acceptance-transit/keys/restore-acceptance",
        "auth/token/revoke-self",
    }
    assert 'capabilities = ["deny"]' in _block(
        text, "restore-acceptance-kv/data/forbidden"
    )
    assert '"read"' in _block(text, "restore-acceptance-kv/data/primary")
    assert '"read"' in _block(
        text, "restore-acceptance-transit/keys/restore-acceptance"
    )
    assert lint_policy_text(text, identity="restore-acceptance-test") == []


def test_bootstrap_supports_recovery_class_without_changing_issuer_scope():
    src = _text(BOOTSTRAP)
    assert "vault policy write vault-admin-recovery" in src
    role = src.split("auth/token/roles/hermes-vault-admin", 1)[1]
    allowed = next(line.strip() for line in role.splitlines() if "allowed_policies=" in line)
    assert "vault-admin-recovery" in allowed
    assert "vault-admin-issuer" not in allowed
    assert "snapshot-force" not in src


def test_existing_runtime_promotion_is_hitl_and_reapplies_exact_role_contract():
    assert PROMOTE.is_file()
    src = _text(PROMOTE)
    assert "VAULT_RECOVERY_PROMOTION_OPERATOR_ACK" in src
    assert "VAULT_TOKEN" in src
    assert "vault policy write vault-admin-recovery" in src
    assert "auth/token/roles/hermes-vault-admin" in src
    for marker in (
        "orphan=true",
        "renewable=false",
        "token_no_default_policy=true",
        "token_explicit_max_ttl=10m",
        "disallowed_policies=default,root",
        "vault-admin-recovery",
    ):
        assert marker in src

    for forbidden in (
        "vault operator init",
        "vault operator unseal",
        "snapshot restore",
        "snapshot-force",
        "client-key",
        "PRIVATE KEY",
    ):
        assert forbidden not in src


def test_project_local_worktree_directory_is_ignored():
    text = _text(GITIGNORE)
    assert any(line.strip() == ".worktrees/" for line in text.splitlines())
