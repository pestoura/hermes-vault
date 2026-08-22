from pathlib import Path
import re

from src.policy_lint.linter import lint_policy_text

POLICY = Path("policies/admin/vault-admin-hsl-bootstrap.hcl")
BOOTSTRAP = Path("deployments/vault/scripts/bootstrap-jit-admin.sh")
RECOVERY_PROMOTION = Path("deployments/vault/scripts/promote-recovery-admin.sh")


def _text(path: Path) -> str:
    return path.read_text()


def _active_paths(text: str) -> list[str]:
    return re.findall(r'^\s*path\s+"([^"]+)"\s*\{', text, re.M)


def test_hsl_bootstrap_jit_policy_is_exact_and_self_revoke_only_beyond_hsl_scope():
    assert POLICY.is_file(), "missing dedicated HSL bootstrap JIT policy"
    text = _text(POLICY)
    assert _active_paths(text) == [
        "sys/mounts",
        "sys/mounts/hsl-transit",
        "hsl-transit/keys/hsl-signing",
        "auth/token/revoke-self",
    ]
    assert 'path "sys/mounts/*"' not in text
    assert 'path "hsl-transit/*"' not in text
    assert 'path "auth/approle' not in text
    assert '"delete"' not in text
    assert '"sudo"' not in text
    assert lint_policy_text(text, identity="vault-admin-hsl-bootstrap") == []


def test_hsl_bootstrap_jit_policy_can_create_mount_and_exact_signing_key():
    text = _text(POLICY)
    mount = text.split('path "sys/mounts/hsl-transit"', 1)[1].split('}', 1)[0]
    key = text.split('path "hsl-transit/keys/hsl-signing"', 1)[1].split('}', 1)[0]
    for capability in ('"create"', '"read"', '"update"'):
        assert capability in mount
        assert capability in key
    revoke = text.split('path "auth/token/revoke-self"', 1)[1].split('}', 1)[0]
    assert '"update"' in revoke


def test_jit_bootstrap_installs_and_authorizes_hsl_bootstrap_class():
    src = _text(BOOTSTRAP)
    assert "vault-admin-hsl-bootstrap.hcl" in src
    assert "vault policy write vault-admin-hsl-bootstrap -" in src
    role_block = src.split("auth/token/roles/hermes-vault-admin", 1)[1]
    allowed_line = next(line for line in role_block.splitlines() if "allowed_policies=" in line)
    assert "vault-admin-hsl-bootstrap" in allowed_line


def test_recovery_promotion_preserves_hsl_bootstrap_class_in_admin_role():
    src = _text(RECOVERY_PROMOTION)
    role_block = src.split("auth/token/roles/hermes-vault-admin", 1)[1]
    allowed_line = next(line for line in role_block.splitlines() if "allowed_policies=" in line)
    assert "vault-admin-hsl-bootstrap" in allowed_line


HSL_PROMOTION = Path("deployments/vault/scripts/promote-hsl-bootstrap-admin.sh")


def test_existing_runtime_hsl_bootstrap_promotion_is_jit_only_and_bounded():
    assert HSL_PROMOTION.is_file(), "missing post-root HSL bootstrap JIT promoter"
    src = _text(HSL_PROMOTION)
    assert "VAULT_HSL_BOOTSTRAP_PROMOTION_OPERATOR_ACK" in src
    assert "vault-admin-policy" in src and "vault-admin-token" in src
    assert "vault policy write vault-admin-hsl-bootstrap -" in src
    assert "auth/token/roles/hermes-vault-admin" in src
    assert "vault-admin-hsl-bootstrap" in src
    for marker in (
        "orphan=true",
        "renewable=false",
        "token_no_default_policy=true",
        "token_explicit_max_ttl=10m",
        "disallowed_policies=default,root",
    ):
        assert marker in src
    for forbidden in (
        "vault operator init",
        "vault operator unseal",
        "root_token",
        "PRIVATE KEY",
        "secret-id",
    ):
        assert forbidden not in src


HSL_TRANSIT = Path("deployments/vault/scripts/enable-hsl-transit.sh")
HSL_SIGNER = Path("deployments/vault/scripts/enable-hsl-signer.sh")


def test_hsl_operator_scripts_use_pinned_container_vault_cli():
    for path in (HSL_TRANSIT, HSL_SIGNER):
        src = _text(path)
        assert "docker compose" in src, path
        assert "exec -T -e VAULT_TOKEN vault vault" in src, path
        assert "command -v vault" not in src, path
        assert "COMPOSE_FILE" in src and "DEPLOY_DIR" in src, path


STATUS_DOC = Path("docs/16-current-runtime-status.md")
HSL_RUNBOOK = Path("docs/runbooks/hsl-first-consumer-bootstrap.md")


def test_hsl_bootstrap_jit_runtime_status_and_operator_sequence_are_explicit():
    status = _text(STATUS_DOC)
    assert "HSL_BOOTSTRAP_JIT_LIVE_PROMOTION=NOT_RUN" in status
    assert HSL_RUNBOOK.is_file()
    runbook = _text(HSL_RUNBOOK)
    for marker in (
        "vault-admin-hsl-bootstrap",
        "promote-hsl-bootstrap-admin.sh",
        "enable-hsl-transit.sh",
        "enable-hsl-signer.sh",
        "FIRST_CONSUMER_BOOTSTRAP=NOT_RUN",
        "SecretID",
        "HITL",
    ):
        assert marker in runbook


def test_hsl_runtime_promoter_never_combines_admin_classes_and_self_revokes():
    src = _text(HSL_PROMOTION)
    assert '"policy")' in src
    assert '"role")' in src
    assert 'required={"vault-admin-policy","vault-admin-token"}' not in src
    assert 'EXPECTED_POLICY="vault-admin-policy"' in src
    assert 'EXPECTED_POLICY="vault-admin-token"' in src
    assert "vault token revoke -self" in src
