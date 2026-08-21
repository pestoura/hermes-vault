# B1 architecture-compliance assertions (static only, no Vault runtime).
# Mirrors spec §4, §5, §6, §7, §8 and ADR-002/006/009/013/019.
from pathlib import Path

import re, yaml

PINNED = "hashicorp/vault:1.21.4@sha256:4e33b126a59c0c333b76fb4e894722462659a6bec7c48c9ee8cea56fccfd2569"

COMPOSE = Path("deployments/vault/docker-compose.yml")
HCL = Path("deployments/vault/config/vault.hcl")

def _compose():
    return yaml.safe_load(COMPOSE.read_text())

def _hcl():
    return HCL.read_text()

def test_single_node_topology():
    comp = _compose()
    assert list(comp["services"].keys()) == ["vault"], comp["services"].keys()

def test_oss_image_not_enterprise():
    comp = _compose()
    vault = comp["services"]["vault"]
    img = vault["image"]
    assert img == PINNED
    assert img.startswith("hashicorp/vault:"), "must be Community/OSS, not vault-enterprise"
    assert "build" not in vault, "runtime must use only the pinned official image, not a local build path"

def test_command_is_server():
    comp = _compose()
    assert comp["services"]["vault"].get("command") == "server"

def test_config_mounted_readonly():
    comp = _compose()
    vols = comp["services"]["vault"].get("volumes", [])
    assert any("vault.hcl:ro" in v for v in vols), vols

def test_certs_volume_readonly():
    comp = _compose()
    vols = comp["services"]["vault"].get("volumes", [])
    assert any("/vault/certs:ro" in v for v in vols), vols

def test_ports_loopback_only():
    comp = _compose()
    ports = comp["services"]["vault"].get("ports", [])
    for p in ports:
        assert p.strip().startswith("127.0.0.1:"), f"non-loopback exposure: {p}"

def test_named_data_volume_uses_official_vault_writable_path():
    comp = _compose()
    vols = comp["services"]["vault"].get("volumes", [])
    assert any(v == "vault-data:/vault/file" for v in vols), vols
    assert "vault-data" in comp.get("volumes", {}), comp.get("volumes")

def test_entrypoint_bootstrap_preserves_cap_drop_all():
    comp = _compose()
    vault = comp["services"]["vault"]
    assert vault.get("cap_drop") == ["ALL"]
    env = vault.get("environment", {})
    assert str(env.get("SKIP_SETCAP")) == "1", env
    assert str(env.get("SKIP_CHOWN")) == "1", env
    assert "cap_add" not in vault, "runtime must not add capabilities to bypass entrypoint setup"

def test_healthcheck_uses_strict_tls_with_mounted_ca():
    comp = _compose()
    vault = comp["services"]["vault"]
    env = vault.get("environment", {})
    assert env.get("VAULT_ADDR") == "https://127.0.0.1:8200", env
    assert env.get("VAULT_CACERT") == "/vault/certs/ca.pem", env
    assert "VAULT_SKIP_VERIFY" not in env, "healthcheck must not bypass TLS verification"
    health = vault.get("healthcheck", {}).get("test", [])
    assert health == ["CMD", "vault", "status"], health

def test_no_autounseal_and_no_enterprise_namespaces():
    hcl = _hcl()
    # No auto-unseal `seal "..." {` stanza (Shamir manual, HITL later). The bare
    # word "seal" may appear in comments (# Shamir manual seal) and must not trip.
    assert not re.search(r'^\s*seal\s+"', hcl, re.M), "auto-unseal seal stanza present"
    # No Enterprise namespace usage.
    assert "namespace" not in hcl, "Enterprise namespace present"

def test_ui_disabled():
    hcl = _hcl()
    assert "ui = false" in hcl

def test_raft_single_node_nodeid():
    hcl = _hcl()
    assert 'storage "raft"' in hcl
    assert "node_id" in hcl
    assert 'path    = "/vault/file"' in hcl or 'path = "/vault/file"' in hcl

def test_tls_required_not_disabled():
    hcl = _hcl()
    assert re.search(r'tls_disable\s*=\s*false', hcl), "TLS must be enabled (tls_disable=false)"
    assert "tls_cert_file" in hcl and "tls_key_file" in hcl
    assert "0.0.0.0:8200" in hcl
