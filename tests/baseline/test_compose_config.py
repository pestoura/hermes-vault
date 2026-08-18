# B1 RED: compose/config assertions (no Vault runtime required).
# Source of truth: .superpowers/sdd/hermes-shared-vault-service/task-B1-brief.md
from pathlib import Path

import yaml, re

PINNED = "hashicorp/vault:1.21.4@sha256:4e33b126a59c0c333b76fb4e894722462659a6bec7c48c9ee8cea56fccfd2569"

def test_image_pinned_by_hsl_digest():
    comp = yaml.safe_load(Path("deployments/vault/docker-compose.yml").read_text())
    img = comp["services"]["vault"]["image"]
    assert img == PINNED, img
    assert re.fullmatch(r"sha256:[0-9a-f]{64}", img.split("@")[1])

def test_raft_storage_and_tls_enabled():
    hcl = Path("deployments/vault/config/vault.hcl").read_text()
    assert 'storage "raft"' in hcl and "node_id" in hcl
    assert "tls_disable = false" in hcl or "tls_cert_file" in hcl

def test_hardening_flags():
    comp = yaml.safe_load(Path("deployments/vault/docker-compose.yml").read_text())
    c = comp["services"]["vault"]
    assert c.get("read_only") is True
    assert "ALL" in c.get("cap_drop", [])
    assert "no-new-privileges" in str(c.get("security_opt", []))
