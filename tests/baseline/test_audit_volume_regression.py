from pathlib import Path

import yaml


COMPOSE = Path("deployments/vault/docker-compose.yml")


def test_read_only_vault_has_persistent_writable_audit_mount():
    comp = yaml.safe_load(COMPOSE.read_text())
    vault = comp["services"]["vault"]

    assert vault.get("read_only") is True
    mounts = vault.get("volumes", [])
    assert "vault-audit:/vault/logs" in mounts, mounts
    assert "vault-audit" in comp.get("volumes", {}), comp.get("volumes", {})
