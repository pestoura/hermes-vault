from pathlib import Path

import re
import yaml

ROOT = Path(__file__).resolve().parents[2]
COMPOSE = ROOT / "deployments/vault/docker-compose.yml"
SCRIPTS = ROOT / "deployments/vault/scripts"
SYSTEMD = ROOT / "deployments/vault/systemd"
BACKUP_POLICY = ROOT / "policies/backup/vault-backup-snapshot.hcl"


def _compose():
    return yaml.safe_load(COMPOSE.read_text(encoding="utf-8"))


def test_compose_runtime_restarts_unless_explicitly_stopped():
    vault = _compose()["services"]["vault"]
    assert vault.get("restart") == "unless-stopped"


def test_readiness_script_is_secret_free_and_fail_closed():
    text = (SCRIPTS / "operational-readiness.sh").read_text(encoding="utf-8")
    for marker in (
        "VAULT_24X7_READY",
        "VAULT_24X7_SEALED_NEEDS_QUORUM",
        "RestartPolicy",
        "hermes-security-plane",
        "hermes-vault-admin",
        "/v1/sys/health",
    ):
        assert marker in text
    for forbidden in ("VAULT_TOKEN=", "SecretID=", "VAULT_SKIP_VERIFY"):
        assert forbidden not in text


def test_readiness_user_timer_runs_at_boot_and_every_five_minutes():
    service = (SYSTEMD / "hermes-vault-readiness.service").read_text(encoding="utf-8")
    timer = (SYSTEMD / "hermes-vault-readiness.timer").read_text(encoding="utf-8")
    assert "ExecStart=%h/hermes-vault/deployments/vault/scripts/operational-readiness.sh" in service
    assert "OnBootSec=1min" in timer
    assert "OnUnitActiveSec=5min" in timer
    assert "Persistent=true" in timer


def test_backup_policy_is_exact_snapshot_read_plus_self_revoke():
    text = BACKUP_POLICY.read_text(encoding="utf-8")
    paths = re.findall(r'^path\s+"([^"]+)"', text, re.M)
    assert paths == ["sys/storage/raft/snapshot", "auth/token/revoke-self"]
    assert 'capabilities = ["read"]' in text
    assert 'capabilities = ["update"]' in text
    for forbidden in ("snapshot-force", "secret/*", "sys/mounts/*", "auth/*"):
        assert forbidden not in text


def test_backup_approle_is_bounded_and_never_issues_secret_id():
    text = (SCRIPTS / "enable-backup-snapshot.sh").read_text(encoding="utf-8")
    for marker in (
        "VAULT_BACKUP_OPERATOR_ACK",
        "vault-backup-snapshot",
        "auth/approle/role/vault-backup",
        "token_ttl=5m",
        "token_max_ttl=5m",
        "token_num_uses=2",
        "secret_id_num_uses=40",
        "secret_id_ttl=840h",
        "role-id",
    ):
        assert marker in text
    assert "/secret-id" not in text
    assert "secret_id" not in text.lower().split("role-id")[-1]


def test_snapshot_service_uses_user_scoped_encrypted_credentials_via_runtime_loader():
    service = (SYSTEMD / "hermes-vault-snapshot.service").read_text(encoding="utf-8")
    timer = (SYSTEMD / "hermes-vault-snapshot.timer").read_text(encoding="utf-8")
    loader = (SCRIPTS / "run-scheduled-snapshot.sh").read_text(encoding="utf-8")
    assert "LoadCredentialEncrypted=" not in service
    assert "EnvironmentFile=%h/.config/hermes-vault/backup.env" in service
    assert "ExecStart=%h/hermes-vault/deployments/vault/scripts/run-scheduled-snapshot.sh" in service
    assert "systemd-creds --user --name=backup-secret-id decrypt" in loader
    assert "systemd-creds --user --name=snapshot-passphrase decrypt" in loader
    assert "XDG_RUNTIME_DIR" in loader and "mktemp -d" in loader
    assert "chmod 700" in loader and "trap cleanup EXIT" in loader
    assert "CREDENTIALS_DIRECTORY" in loader
    assert "OnCalendar=*-*-* 02:30:00" in timer
    assert "Persistent=true" in timer


def test_scheduled_snapshot_uses_short_lived_login_and_self_revoke():
    text = (SCRIPTS / "scheduled-snapshot.py").read_text(encoding="utf-8")
    for marker in (
        "CREDENTIALS_DIRECTORY",
        "backup-secret-id",
        "snapshot-passphrase",
        "/v1/auth/approle/login",
        "/v1/sys/storage/raft/snapshot",
        "/v1/auth/token/revoke-self",
        "VAULT_SNAPSHOT_RETENTION",
        "AES-256-CBC",
        "PBKDF2",
    ):
        assert marker in text
    assert "VAULT_SKIP_VERIFY" not in text
    assert "print(client_token" not in text
    assert "print(secret_id" not in text


def test_scheduled_snapshot_has_no_embedded_secret_literals():
    text = (SCRIPTS / "scheduled-snapshot.py").read_text(encoding="utf-8")
    for pattern in (r"(?<![A-Za-z0-9_])hvs\.[A-Za-z0-9]", r"(?<![A-Za-z0-9_])s\.[A-Za-z0-9_-]{12,}", r"-----BEGIN .*PRIVATE KEY-----"):
        assert re.search(pattern, text) is None
